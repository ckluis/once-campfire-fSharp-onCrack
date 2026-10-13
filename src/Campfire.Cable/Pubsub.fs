// Port of rust/crates/cable/src/pubsub.rs
//
// In-process replacement for the Redis subscription adapter: a ring buffer per group of subscribers
// (what `tokio::sync::broadcast` is in Rust), created on first subscribe and dropped with the last
// subscriber of a broadcasting.
//
// Payloads are already-encoded JSON, as they are on the Redis wire. Subscribers that would wrap a
// payload identically (the same channel identifier) share one group, and each broadcast builds their
// `{"identifier":...,"message":...}` frame once for all of them.
//
// onCrack (unit R4.5): a group keeps an append-only log in chunks (`LogGroup`), shared by its subscribers, each of which
// keeps its own place in it; what no subscriber can still read is freed. The log is bounded by a byte budget
// (`CAMPFIRE_CABLE_LAG_BYTES`), not by a frame count: a subscriber behind by that much is told it lagged and its connection
// is closed with `reconnect: true` (the browser treats it as a dropped network and refreshes the room), so a client that is
// slow to read is held as long as the memory bound allows, as Action Cable holds it, and never silently skips messages.
// `CAMPFIRE_CABLE_LOG=ring` keeps the fixed ring of rounds 1-4 (`RingGroup`), cutting a subscriber 256 frames behind.
//
// Where tokio wakes a receiver's task per broadcast, a subscriber here wakes its connection's `Wake`:
// one object per connection, however many streams it reads, which the connection awaits and then reads
// every ready stream from, without a queue of its own.
namespace Campfire.Cable

open System
open System.Collections.Concurrent
open System.Numerics
open System.Text
open System.Threading
open System.Threading.Tasks
open System.Threading.Tasks.Sources
open Campfire.Cable.Socket

/// An auto-reset event with one waiter, awaited without allocating: `Set` makes the next (or
/// current) `WaitAsync` complete, any number of `Set`s before it count once.
[<Sealed>]
type Wake() =
    // 0: nothing set and nobody waiting; 1: set; 2: the waiter is parked.
    let mutable state = 0
    let mutable core = ManualResetValueTaskSourceCore<bool>(RunContinuationsAsynchronously = true)
    let mutable retired = 0
    let mutable writeWaitSince = 0L

    member _.Set() : unit =
        let mutable spinning = true
        while spinning do
            match Volatile.Read(&state) with
            | 1 -> spinning <- false
            | 0 -> if Interlocked.CompareExchange(&state, 1, 0) = 0 then spinning <- false
            | _ ->
                if Interlocked.CompareExchange(&state, 0, 2) = 2 then
                    core.SetResult true
                    spinning <- false

    /// Completes after a `Set`, consuming it. Only one call may be outstanding.
    member this.WaitAsync() : ValueTask<bool> =
        if Interlocked.CompareExchange(&state, 0, 1) = 1 then
            ValueTask<bool>(true)
        else
            core.Reset()
            if Interlocked.CompareExchange(&state, 2, 0) = 0 then
                new ValueTask<bool>(this :> IValueTaskSource<bool>, core.Version)
            else
                // Set between the check and parking.
                Volatile.Write(&state, 0)
                ValueTask<bool>(true)

    /// `WakeBatch`'s mark: the token of the last scope that held this wake back.
    member val internal HeldIn = 0L with get, set

    /// How long a cut subscriber's connection is given to say goodbye (its disconnect frame, then the close) before its socket is
    /// aborted. A client that is reading finishes inside it; one that is not is cut when it ends.
    static member val CutGrace = TimeSpan.FromSeconds 1.0 with get, set

    /// Unit R4.5: how the connection is cut (`Connection.run` sets it), for a subscriber over its log's byte budget.
    member val internal Abort: (unit -> unit) | null = null with get, set

    /// The connection has ended: a late cut leaves its socket alone.
    member _.Retire() : unit = Volatile.Write(&retired, 1)

    /// Unit R5.1: the connection's trace (`CAMPFIRE_CABLE_TRACE`); null without the switch.
    member val internal Trace: ConnTrace | null = null with get, set

    /// Round 4 verifier: when (`Stopwatch` ticks) the connection began waiting on a socket write that has not completed, or 0. A
    /// connection that has waited long on one write is limited by its own reader, not by the fan-out (`Hub.Congested` leaves it out).
    member _.WriteWaitSince
        with get () = Volatile.Read(&writeWaitSince)
        and set (since: int64) = Volatile.Write(&writeWaitSince, since)

    /// Wakes the connection, which finds its subscriber lagged and says goodbye; its socket is aborted after `CutGrace` if it
    /// has not finished (a client that has stopped reading cannot take the goodbye). Called from a thread pool item.
    member this.Cut() : unit =
        (match this.Trace with
         | null -> ()
         | trace -> trace.Event("cut", 0L, 0L))
        this.Set()
        match this.Abort with
        | null -> ()
        | abort -> Task.Delay(Wake.CutGrace).ContinueWith(fun (_: Task) -> if Volatile.Read(&retired) = 0 then abort ()) |> ignore

    interface IValueTaskSource<bool> with
        member _.GetResult(token: int16) = core.GetResult token
        member _.GetStatus(token: int16) = core.GetStatus token

        member _.OnCompleted(continuation, state, token, flags) =
            core.OnCompleted(continuation, state, token, flags)

/// onCrack (unit R2.1): wakes held back while one thread publishes several broadcasts, then set once each. A post makes two
/// (its append to the room, then the unread ping to every member), and `BroadcastOrder` publishes every post waiting in line
/// one after another; with the wakes held until the last of them is in its ring, a connection reads them all in one turn and
/// sends them in one write, instead of waking on the first and sending again for each later one. Frames are in their rings
/// before anyone is woken either way, so what a connection reads, and in which order, is the same; only fewer, later wakes.
[<Sealed; AbstractClass>]
type WakeBatch private () =
    [<ThreadStatic; DefaultValue>]
    static val mutable private depth: int

    [<ThreadStatic; DefaultValue>]
    static val mutable private held: System.Collections.Generic.List<Wake> | null

    /// The outermost scope's token: unique across threads, so a wake's one mark field says which scope holds it.
    [<ThreadStatic; DefaultValue>]
    static val mutable private token: int64

    static let mutable tokens = 0L

    /// Holds this thread's wakes until the matching `End`. Scopes nest; the outermost `End` sets them.
    static member Begin() : unit =
        if WakeBatch.depth = 0 then
            WakeBatch.token <- Interlocked.Increment(&tokens)
            if isNull WakeBatch.held then WakeBatch.held <- System.Collections.Generic.List<Wake>()
        WakeBatch.depth <- WakeBatch.depth + 1

    static member End() : unit =
        WakeBatch.depth <- WakeBatch.depth - 1
        if WakeBatch.depth = 0 then WakeBatch.SetHeld true

    /// Ends the scope like `End`, but at the outermost end hands what it held to `into` (marked with `token`, each wake once)
    /// instead of setting it: the caller sets them later (`BroadcastOrder` holds a busy line's wakes until it is idle).
    static member EndInto(into: System.Collections.Generic.List<Wake>, token: int64) : unit =
        WakeBatch.depth <- WakeBatch.depth - 1
        if WakeBatch.depth = 0 then
            match WakeBatch.held with
            | null -> ()
            | held ->
                for i in 0 .. held.Count - 1 do
                    let wake = held[i]
                    if wake.HeldIn <> token then
                        wake.HeldIn <- token
                        into.Add wake
                held.Clear()

    /// A token no scope has: for a holder of wakes outside `WakeBatch`'s scopes (`EndInto`).
    static member NewToken() : int64 = Interlocked.Increment(&tokens)

    /// Sets what is held now, staying in the scope: a scope that publishes without end (a drainer that keeps finding work)
    /// calls it every few broadcasts, so nobody waits on the scope's end.
    static member Flush() : unit =
        if WakeBatch.depth > 0 then
            WakeBatch.SetHeld false
            WakeBatch.token <- Interlocked.Increment(&tokens)

    /// Sets and clears what is held; `release` (the scope is over) drops a list that grew large.
    static member private SetHeld(release: bool) : unit =
        match WakeBatch.held with
        | null -> ()
        | held ->
            for i in 0 .. held.Count - 1 do
                held[i].Set()
            held.Clear()
            if release && held.Capacity > 65536 then WakeBatch.held <- null

    /// The thread's scope, for a loop over many wakes: its token and list, or null outside a scope (one look for them all).
    static member internal Current: struct (int64 * System.Collections.Generic.List<Wake> | null) =
        if WakeBatch.depth = 0 then struct (0L, null) else struct (WakeBatch.token, WakeBatch.held)

    /// Runs `publish` with the wakes it makes held until it returns.
    static member Run(publish: unit -> unit) : unit =
        WakeBatch.Begin()
        try
            publish ()
        finally
            WakeBatch.End()

/// What reading a subscriber found.
type RecvStatus =
    | Got = 0
    | Empty = 1
    /// The subscriber missed messages; its connection must be closed.
    | Lagged = 2

/// A run of consecutive frames of a group's log (unit R4.5). Frames are written once, under the group's lock, and never
/// change; a reader follows `Next` from one chunk to the next. A chunk is freed by the GC once the group's head and every
/// subscriber have moved past it.
[<Sealed>]
type internal Chunk(size: int, id: int64, start: int64) =
    let frames: Frame[] = Array.zeroCreate size
    let seqs: int64[] = Array.zeroCreate size
    let mutable filled = 0
    let mutable next: Chunk | null = null

    /// The log's chunks are numbered in order, so a chunk's id says which of two is behind.
    member _.Id = id

    /// Bytes of frames the log held before this chunk.
    member _.Start = start

    member _.Size = size
    member _.Frames = frames

    /// Each frame's number in the hub's publish order (`LogStats.NextSequence`), written with the frame.
    member _.Sequences = seqs

    /// How many slots hold a frame (published with `Volatile.Write` after the frame is in its slot).
    member _.Filled
        with get () = Volatile.Read(&filled)
        and set (value: int) = Volatile.Write(&filled, value)

    member _.Next
        with get () = Volatile.Read(&next)
        and set (value: Chunk | null) = Volatile.Write(&next, value)

    /// A chunk no log has: the position of a ring subscriber, which has none.
    static member val None = Chunk(0, -1L, 0L)

/// The bytes the logs of one hub hold now and at most, and how many subscribers they cut.
[<Sealed>]
type internal LogStats() =
    let mutable retained = 0L
    let mutable peak = 0L
    let mutable cuts = 0L
    let mutable sequence = 0L

    /// The next number in the hub's publish order: a frame published later has a higher one, across every group.
    member _.NextSequence() : int64 = Interlocked.Increment(&sequence)

    member _.Retained = Interlocked.Read(&retained)
    member _.Peak = Interlocked.Read(&peak)
    member _.Cuts = Interlocked.Read(&cuts)

    member _.Add(delta: int64) : unit =
        let now = Interlocked.Add(&retained, delta)
        if delta > 0L then
            let mutable seen = Volatile.Read(&peak)
            while now > seen do
                let was = Interlocked.CompareExchange(&peak, now, seen)
                seen <- if was = seen then now + 1L else was

    member _.NoteCuts(count: int) : unit = Interlocked.Add(&cuts, int64 count) |> ignore

/// The subscribers of one broadcasting that receive identical frames: the payload wrapped for the
/// same encoded channel identifier, or the raw payload when `Identifier` is null.
[<AbstractClass>]
type internal GroupBase(identifier: string | null) =
    static let closingBrace: byte[] = [| byte '}' |]

    let prefix: byte[] | null =
        match identifier with
        | null -> null
        | identifier -> Encoding.UTF8.GetBytes(Protocol.messagePrefix identifier)

    member _.Identifier = identifier

    /// Unit R5.1: the group's number in a trace (`CAMPFIRE_CABLE_TRACE`).
    member val Id = CableTrace.NextGroupId() with get

    /// The frame a payload makes for this group's subscribers.
    member _.Frame(payload: ReadOnlySpan<byte>) : Frame =
        match prefix with
        | null -> Frame.OfBytes payload
        | prefix -> Frame.Concat(ReadOnlySpan<byte> prefix, payload, ReadOnlySpan<byte> closingBrace)

    abstract Count: int

    /// Appends the frame and wakes every subscriber. Returns how many there are.
    abstract Publish: Frame -> int

    /// A subscriber that will see what is published from now on.
    abstract Add: Wake * Hub * string -> Subscriber

    abstract Remove: Subscriber -> unit

    /// The group has been dropped from its hub: it no longer counts toward the hub's retained bytes.
    abstract Retire: unit -> unit
    default _.Retire() = ()

    /// Unit R4.5: how many subscribers are more than `frames` behind the newest frame and whose connections have not waited `waitTicks`
    /// or longer on one socket write (high 32 bits), and how many subscribers there are (low 32 bits). A ring has no such measure (0).
    abstract Tally: frames: int * waitTicks: int64 -> int64
    default _.Tally(_: int, _: int64) = 0L

    /// Reads `subscriber`'s next frame: the frame, or whether there is none yet or it missed some.
    abstract TryRead: Subscriber * byref<Frame> -> RecvStatus

    /// The publish-order number of `subscriber`'s next frame, without taking it (logs only: a ring has none).
    abstract TryPeek: Subscriber * byref<int64> -> RecvStatus

    /// Wakes `receivers[0 .. count - 1]`, or holds their wakes for the thread's `WakeBatch` scope.
    static member internal WakeAll(receivers: Subscriber[], count: int) : unit =
        match WakeBatch.Current with
        | struct (_, null) ->
            for i in 0 .. count - 1 do
                receivers[i].Wake.Set()
        | struct (token, held) ->
            for i in 0 .. count - 1 do
                let wake = receivers[i].Wake
                if wake.HeldIn <> token then
                    wake.HeldIn <- token
                    held.Add wake

/// onCrack (unit R4.5): a group's frames in an append-only log of chunks shared by its subscribers. A subscriber is a cursor
/// (chunk, index); one that has caught up costs nothing, one that is far behind costs the log from its place, shared with every
/// other subscriber behind there. The group holds the log from the oldest chunk any subscriber is still in (`head`). When that
/// is more than `budget` bytes the subscribers in the oldest chunk are cut, oldest first, until it is not; so the memory a slow
/// client can pin is bounded per group, and a client that is merely slow, and within the bound, loses nothing.
///
/// Readers take no lock: a publish writes the frame into its slot, then raises the chunk's `Filled` (a release); a reader that
/// sees the count sees the frame. A chunk is linked from the one before it before its first frame is written, so a reader
/// that has read all of a full chunk finds the next one or finds none yet (nothing published).
and [<Sealed>] internal LogGroup(identifier: string | null, chunkSize: int, budget: int64, stats: LogStats, onCut: Action<int, int64> | null) =
    inherit GroupBase(identifier)
    let gate = obj ()
    let mutable head = Chunk(chunkSize, 0L, 0L)
    let mutable tail = head
    let mutable written = 0L
    let mutable receivers: Subscriber[] = Array.zeroCreate 4
    let mutable count = 0
    let mutable retired = false
    // Unit R5.2: slots of the head chunk below `freedIndex` are emptied (every subscriber is past them), `freedBytes` of frames.
    let mutable freedIndex = 0
    let mutable freedBytes = 0L
    let mutable tally = 0L
    let mutable tallyAt = 0L
    let verdictTicks = Diagnostics.Stopwatch.Frequency / 100L

    /// Moves `head` to the oldest chunk a subscriber is in (or the tail, with none), freeing what is behind it. Under `gate`.
    let trim () : unit =
        let mutable oldest = tail
        for i in 0 .. count - 1 do
            let chunk = receivers[i].Chunk
            if chunk.Id < oldest.Id then oldest <- chunk
        if oldest.Id > head.Id then
            if not retired then stats.Add(-(oldest.Start - head.Start - freedBytes))
            head <- oldest
            freedIndex <- 0
            freedBytes <- 0L

    /// The first slot of `chunk`, counted over the whole log (`Subscriber.Slot`).
    let baseOf (chunk: Chunk) : int64 = chunk.Id * int64 chunkSize

    /// Where slot `slot` is in the log, in bytes written before it (`written` for the next frame to come), looked for from `chunk` on (the
    /// slot is in it or after it): the chunk's start plus the frames ahead of the slot (a head chunk's emptied slots are counted in
    /// `freedBytes`). Under `gate`.
    let position (chunk: Chunk) (slot: int64) : int64 =
        let mutable chunk = chunk
        let mutable result = -1L
        while result < 0L do
            let index = slot - baseOf chunk
            if index < int64 chunk.Filled then
                let mutable at = chunk.Start
                let mutable from = 0
                if obj.ReferenceEquals(chunk, head) then
                    at <- at + freedBytes
                    from <- freedIndex
                for k in from .. int index - 1 do
                    at <- at + int64 chunk.Frames[k].Bytes.Length
                result <- at
            else
                match chunk.Next with
                | null -> result <- written
                | next -> chunk <- next
        result

    /// Bytes `subscriber` has yet to read. Under `gate`. Round 5 verifier: the subscriber's place is one number (`Slot`), written once a frame
    /// is read; the chunk, read first, only says where to start looking. Round 5's pair (chunk, index) was written in two steps when a reader
    /// crossed into a new chunk, and a look between them took the reader to be a whole chunk further behind than it was.
    let unread (subscriber: Subscriber) : int64 =
        let chunk = subscriber.Chunk
        written - position chunk subscriber.SlotSeen

    /// Cuts the subscribers in the oldest chunk, adding their wakes to `cut` (made when needed). Under `gate`; `trim` after.
    let cutHead (cut: Collections.Generic.List<Wake> | null) : Collections.Generic.List<Wake> | null =
        let mutable cut = cut
        let mutable i = count - 1
        while i >= 0 do
            let subscriber = receivers[i]
            if obj.ReferenceEquals(subscriber.Chunk, head) then
                (match subscriber.Wake.Trace with
                 | null -> ()
                 | trace -> trace.Event("overrun", int64 subscriber.Group.Id, head.Id))
                subscriber.MarkOverrun()
                receivers[i] <- receivers[count - 1]
                receivers[count - 1] <- Unchecked.defaultof<_>
                Volatile.Write(&count, count - 1)
                match cut with
                | null -> cut <- Collections.Generic.List<Wake>()
                | _ -> ()
                (nonNull cut).Add subscriber.Wake
            i <- i - 1
        cut

    /// Cuts the subscribers in the oldest chunk until the log is within its budget (or only the tail's chunk is left, which is
    /// at most `chunkSize` frames). Returns the cut subscribers' wakes, for a thread pool item to close. Under `gate`.
    let enforce () : Collections.Generic.List<Wake> | null =
        let mutable cut: Collections.Generic.List<Wake> | null = null
        trim ()
        while written - head.Start > budget && not (obj.ReferenceEquals(head, tail)) do
            cut <- cutHead cut
            trim ()
        cut

    override _.Count = Volatile.Read(&count)

    override this.Publish(frame: Frame) : int =
        let struct (cut, shared) =
            lock gate (fun () ->
                let mutable chunk = tail
                let mutable fresh = false
                if chunk.Filled = chunk.Size then
                    let next = Chunk(chunkSize, chunk.Id + 1L, written)
                    chunk.Next <- next
                    tail <- next
                    chunk <- next
                    fresh <- true
                let length = int64 frame.Bytes.Length
                chunk.Frames[chunk.Filled] <- frame
                let sequence = stats.NextSequence()
                chunk.Sequences[chunk.Filled] <- sequence
                frame.Seq <- sequence
                CableVerify.Stamp frame
                if CableTrace.Enabled then
                    CableTrace.Published(this.Id, chunk.Id * int64 chunkSize + int64 chunk.Filled, sequence, frame.Bytes)
                written <- written + length
                chunk.Filled <- chunk.Filled + 1
                if not retired then stats.Add length
                // Finding the oldest subscriber is a pass over them all: once per chunk, or when over the budget.
                let cut =
                    if fresh || (written - head.Start > budget && not (obj.ReferenceEquals(head, tail))) then enforce () else null
                GroupBase.WakeAll(receivers, count)
                struct (cut, count))
        match cut with
        | null -> ()
        | wakes -> LogGroup.CutLater(wakes, stats, onCut, budget)
        shared

    /// Counts `wakes` as cut and closes their connections from a thread pool item.
    static member internal CutLater(wakes: Collections.Generic.List<Wake>, stats: LogStats, onCut: Action<int, int64> | null, budget: int64) : unit =
        stats.NoteCuts wakes.Count
        ThreadPool.UnsafeQueueUserWorkItem(
            WaitCallback(fun _ ->
                for wake in wakes do
                    wake.Cut()
                match onCut with
                | null -> ()
                | onCut -> onCut.Invoke(wakes.Count, budget)),
            null
        )
        |> ignore

    override this.Add(wake: Wake, hub: Hub, broadcasting: string) : Subscriber =
        lock gate (fun () ->
            let subscriber = new Subscriber(this, hub, broadcasting, wake, 0L, tail, tail.Filled)
            (match wake.Trace with
             | null -> ()
             | trace -> trace.Subscribed(this.Id, broadcasting, tail.Id * int64 chunkSize + int64 tail.Filled))
            if count = receivers.Length then Array.Resize(&receivers, count * 2)
            receivers[count] <- subscriber
            Volatile.Write(&count, count + 1)
            subscriber)

    override this.Remove(subscriber: Subscriber) : unit =
        lock gate (fun () ->
            let at = Array.IndexOf(receivers, subscriber, 0, count)
            if at >= 0 then
                (match subscriber.Wake.Trace with
                 | null -> ()
                 | trace -> trace.Event("unsubscribed", int64 this.Id, 0L))
                receivers[at] <- receivers[count - 1]
                receivers[count - 1] <- Unchecked.defaultof<_>
                Volatile.Write(&count, count - 1)
                // The oldest subscriber leaving frees the log behind the next one.
                if obj.ReferenceEquals(subscriber.Chunk, head) && not (obj.ReferenceEquals(head, tail)) then trim ())

    /// A tally is worked out at most every 10 ms, however many ask: a pass over the subscribers under the group's lock.
    override _.Tally(frames: int, waitTicks: int64) : int64 =
        let now = Diagnostics.Stopwatch.GetTimestamp()
        if now - Volatile.Read(&tallyAt) < verdictTicks then
            Volatile.Read(&tally)
        else
            lock gate (fun () ->
                let mutable behind = 0L
                let mutable counted = 0L
                let newest = tail.Id * int64 chunkSize + int64 tail.Filled
                for i in 0 .. count - 1 do
                    let subscriber = receivers[i]
                    let since = subscriber.Wake.WriteWaitSince
                    counted <- counted + 1L
                    if (since = 0L || now - since < waitTicks)
                       && newest - subscriber.SlotSeen > int64 frames then
                        behind <- behind + 1L
                let packed = (behind <<< 32) ||| counted
                Volatile.Write(&tally, packed)
                Volatile.Write(&tallyAt, now)
                packed)

    override _.Retire() : unit =
        lock gate (fun () ->
            if not retired then
                retired <- true
                stats.Add(-(written - head.Start - freedBytes)))

    /// Frees what no subscriber can read: the heartbeat calls it, so a log that nobody publishes to any more does not hold what
    /// its subscribers have since read. Unit R5.2: that includes the frames of the head chunk that every subscriber is past.
    member this.Trim() : unit = this.Compact()

    /// Unit R5.2: moves `head` to the oldest chunk a subscriber is in, then empties the slots of that chunk that every subscriber has
    /// read (a log with no subscribers holds nothing), so the bytes retained are the bytes some subscriber has yet to read, not the
    /// chunk they are in. Readers take no lock, and this never takes anything from one: it empties slots below the lowest slot
    /// any subscriber is seen at, and a slot only grows (a stale reading is lower, which empties less). A subscriber taken out of the group
    /// whose reader has not yet seen the cut can find its next slot empty, and `TryRead` reads that as the cut.
    member _.Compact() : unit =
        lock gate (fun () ->
            trim ()
            let mutable upTo = head.Filled
            let first = baseOf head
            for i in 0 .. count - 1 do
                // Round 5 verifier: a slot, read with acquire, is one the reader has finished reading the frame before (`TryRead` writes it with
                // release); a subscriber past the head chunk has a slot past its end.
                let index = receivers[i].SlotSeen - first
                if index < int64 upTo then upTo <- int index
            if upTo > freedIndex then
                let mutable freed = 0L
                for i in freedIndex .. upTo - 1 do
                    freed <- freed + int64 head.Frames[i].Bytes.Length
                    head.Frames[i] <- Unchecked.defaultof<Frame>
                freedIndex <- upTo
                freedBytes <- freedBytes + freed
                if not retired then stats.Add(-freed))

    /// Bytes this log holds now: what some subscriber has yet to read, from the oldest chunk's emptied part on.
    member _.Retained = lock gate (fun () -> written - head.Start - freedBytes)

    /// Unit R5.2: adds `(unread bytes, this log, subscriber)` for every subscriber that has something to read (the hub's total sheds
    /// the furthest behind first).
    member this.Collect(into: Collections.Generic.List<struct (int64 * LogGroup * Subscriber)>) : unit =
        lock gate (fun () ->
            for i in 0 .. count - 1 do
                let subscriber = receivers[i]
                let behind = unread subscriber
                if behind > 0L then into.Add(struct (behind, this, subscriber)))

    /// Unit R5.2: cuts `subscriber` (as `cutHead` does), and frees what that leaves nobody to read. Its wake, or null if it has left.
    member this.CutOne(subscriber: Subscriber) : Wake | null =
        lock gate (fun () ->
            let at = Array.IndexOf(receivers, subscriber, 0, count)
            if at < 0 then
                null
            else
                (match subscriber.Wake.Trace with
                 | null -> ()
                 | trace -> trace.Event("overrun", int64 subscriber.Group.Id, head.Id))
                subscriber.MarkOverrun()
                receivers[at] <- receivers[count - 1]
                receivers[count - 1] <- Unchecked.defaultof<_>
                Volatile.Write(&count, count - 1)
                this.Compact()
                subscriber.Wake)

    /// Finds `subscriber`'s next slot, following the link out of a chunk it has read to the end.
    static member private Locate(subscriber: Subscriber, chunk: byref<Chunk>, index: byref<int>) : bool =
        chunk <- subscriber.Chunk
        index <- int (subscriber.Slot - chunk.Id * int64 chunk.Size)
        if index = chunk.Size then
            // All of this chunk is read; the next may not exist yet.
            match chunk.Next with
            | null -> ()
            | next ->
                chunk <- next
                index <- 0
                // Round 5 verifier: the slot is already the next chunk's first (the slot after a chunk's last), so moving is one write.
                subscriber.MoveTo next
                (match subscriber.Wake.Trace with
                 | null -> ()
                 | trace -> trace.Cross(subscriber.Group.Id, next.Id))
        index < chunk.Filled

    override _.TryRead(subscriber: Subscriber, frame: byref<Frame>) : RecvStatus =
        if subscriber.Overrun then
            RecvStatus.Lagged
        else
            let mutable chunk = subscriber.Chunk
            let mutable index = 0
            if LogGroup.Locate(subscriber, &chunk, &index) then
                let read = chunk.Frames[index]
                if isNull (box read) then
                    // Round 5 verifier: emptied by `Compact`, which empties only slots every subscriber of the group has passed, so this one is
                    // no longer in the group: cut (`CutOne`, `cutHead`) after its reader looked at the flag above. It reads as the cut it is.
                    RecvStatus.Lagged
                else
                    frame <- read
                    // A release: the frame is read before another thread can see the slot as passed (`Compact`) and empty it.
                    subscriber.Advance()
                    RecvStatus.Got
            else
                RecvStatus.Empty

    override _.TryPeek(subscriber: Subscriber, sequence: byref<int64>) : RecvStatus =
        if subscriber.Overrun then
            RecvStatus.Lagged
        else
            let mutable chunk = subscriber.Chunk
            let mutable index = 0
            if LogGroup.Locate(subscriber, &chunk, &index) then
                sequence <- chunk.Sequences[index]
                RecvStatus.Got
            else
                RecvStatus.Empty

/// The group of rounds 1-4 (`CAMPFIRE_CABLE_LOG=ring`): a fixed ring of `capacity` frames shared by its subscribers; one more
/// than `capacity` frames behind is lagged and loses the frames it missed.
and [<Sealed>] internal RingGroup(identifier: string | null, capacity: int) =
    inherit GroupBase(identifier)
    // `capacity + 1` slots, so that the slot a publish is writing never holds a frame a reader
    // still within `capacity` of the tail can want.
    let slots: Frame[] = Array.zeroCreate (capacity + 1)
    let mutable tail = 0L
    let mutable receivers: Subscriber[] = Array.zeroCreate 4
    let mutable count = 0

    override _.Count = Volatile.Read(&count)

    override this.Publish(frame: Frame) : int =
        lock slots (fun () ->
            CableVerify.Stamp frame
            if CableTrace.Enabled then
                let sequence = CableTrace.RingSeq()
                frame.Seq <- sequence
                CableTrace.Published(this.Id, tail, sequence, frame.Bytes)
            Volatile.Write(&slots[int (tail % int64 slots.Length)], frame)
            Volatile.Write(&tail, tail + 1L)
            GroupBase.WakeAll(receivers, count)
            count)

    override this.Add(wake: Wake, hub: Hub, broadcasting: string) : Subscriber =
        lock slots (fun () ->
            let subscriber = new Subscriber(this, hub, broadcasting, wake, tail, Chunk.None, 0)
            (match wake.Trace with
             | null -> ()
             | trace -> trace.Subscribed(this.Id, broadcasting, tail))
            if count = receivers.Length then Array.Resize(&receivers, count * 2)
            receivers[count] <- subscriber
            Volatile.Write(&count, count + 1)
            subscriber)

    override _.Remove(subscriber: Subscriber) : unit =
        lock slots (fun () ->
            let at = Array.IndexOf(receivers, subscriber, 0, count)
            if at >= 0 then
                receivers[at] <- receivers[count - 1]
                receivers[count - 1] <- Unchecked.defaultof<_>
                Volatile.Write(&count, count - 1))

    override _.TryPeek(_: Subscriber, _: byref<int64>) : RecvStatus = RecvStatus.Empty

    /// Reads from the subscriber's position: the frame there, or whether there is none yet or the ring has moved past it.
    override _.TryRead(subscriber: Subscriber, frame: byref<Frame>) : RecvStatus =
        let position = subscriber.Position
        let t = Volatile.Read(&tail)
        if position = t then
            RecvStatus.Empty
        elif t - position > int64 capacity then
            subscriber.Position <- t - int64 capacity
            RecvStatus.Lagged
        else
            let found = Volatile.Read(&slots[int (position % int64 slots.Length)])
            // A publish may have wrapped around to this slot while it was being read.
            let t = Volatile.Read(&tail)
            if t - position > int64 capacity then
                subscriber.Position <- t - int64 capacity
                RecvStatus.Lagged
            else
                frame <- found
                subscriber.Position <- position + 1L
                RecvStatus.Got

/// One subscription's place in a group's log (or ring).
and [<Sealed>] Subscriber internal (group: GroupBase, hub: Hub, broadcasting: string, wake: Wake, start: int64, chunk0: Chunk, index0: int) =
    let mutable chunk = chunk0
    // Round 5 verifier: the next slot over the whole log (chunk id x chunk size + index), so that one write moves the reader on.
    let mutable slot = if chunk0.Id < 0L then 0L else chunk0.Id * int64 chunk0.Size + int64 index0
    let mutable stopped = 0
    let mutable overrun = 0

    member _.Broadcasting: string = broadcasting
    member internal _.Wake: Wake = wake
    member internal _.Group: GroupBase = group
    member internal _.Hub: Hub = hub

    /// The ring's place (ring groups).
    member val internal Position = start with get, set

    /// The log's place: the chunk, which the group's `trim` reads from its own thread, and the next slot, counted over the whole log (a
    /// chunk's slots are its id x the chunk size and on). The chunk moves only once the slot is the next chunk's first, so a slot read after
    /// the chunk is in that chunk or past it.
    member internal _.Chunk: Chunk = Volatile.Read(&chunk)

    /// The next slot, as the reader's own thread sees it.
    member internal _.Slot = slot

    /// The next slot, as another thread sees it (`Compact`, `Collect`, `Tally`): a place at or behind where the reader is, every slot before it read.
    member internal _.SlotSeen = Volatile.Read(&slot)

    /// The reader has read the frame in its slot (a release: the read is done before any thread can see the slot as passed).
    member internal _.Advance() : unit = Volatile.Write(&slot, slot + 1L)
    member internal _.MoveTo(next: Chunk) : unit = Volatile.Write(&chunk, next)

    /// The group cut this subscriber for being more than its budget behind; it is out of the group and reads nothing more.
    member internal _.Overrun = Volatile.Read(&overrun) <> 0
    member internal _.MarkOverrun() : unit = Volatile.Write(&overrun, 1)

    /// Whether it has been disposed: it reads nothing more.
    member _.Stopped = Volatile.Read(&stopped) <> 0

    /// The next frame, if there is one. Read by one thread at a time.
    member this.TryRecv(frame: byref<Frame>) : RecvStatus =
        if this.Stopped then RecvStatus.Empty else group.TryRead(this, &frame)

    /// Unit R4.5: the publish-order number of the next frame (higher is later, across the hub's groups), without taking it.
    member this.TryPeek(sequence: byref<int64>) : RecvStatus =
        if this.Stopped then RecvStatus.Empty else group.TryPeek(this, &sequence)

    interface IDisposable with
        member this.Dispose() =
            if Interlocked.Exchange(&stopped, 1) = 0 then hub.Release this

/// The broadcast hub: `Hub.Broadcast` publishes to every subscriber of a broadcasting.
///
/// `capacity` is the chunk size of a group's log (frames), or the ring's size with `ring`. `lagBytes` is a log's budget
/// (`CAMPFIRE_CABLE_LAG_BYTES`): a subscriber more than that far behind is cut. `onCut` is told how many were cut in one go.
and [<Sealed>] Hub(capacity: int, lagBytes: int64, ring: bool, onCut: Action<int, int64> | null) =
    // tokio rounds a channel's capacity up to a power of two.
    let capacity = if ring then int (BitOperations.RoundUpToPowerOf2(uint32 (max capacity 1))) else max capacity 1
    let streams = ConcurrentDictionary<string, GroupBase[]>(StringComparer.Ordinal)
    let gate = obj ()
    let stats = LogStats()
    let mutable totalBudget: int64 = 1024L * 1024L * 1024L
    let mutable shedding = 0
    let mutable shedAt: int64 = 0L

    new(capacity: int) = Hub(capacity, Hub.DefaultLagBytes, false, null)
    new(capacity: int, lagBytes: int64, ring: bool) = Hub(capacity, lagBytes, ring, null)

    /// A group's log may hold this much behind its oldest subscriber (`CAMPFIRE_CABLE_LAG_BYTES`): about 26,000 Campfire messages, whose
    /// frames are about 10 KB (64 MB was 6,500 of them, which a few slow clients of a saturated room passed).
    static member DefaultLagBytes = 256L * 1024L * 1024L

    /// onCrack: whether `broadcasting` has a subscriber now, so that a broadcast nobody would receive needn't be
    /// encoded. One that subscribes after this answer misses the broadcast, as it would one sent a moment earlier.
    member _.HasSubscribers(broadcasting: string) : bool = streams.ContainsKey broadcasting

    /// Publishes to every current subscriber of `broadcasting`; `payload` is encoded JSON as UTF-8.
    /// Returns how many received it.
    member this.Broadcast(broadcasting: string, payload: ReadOnlySpan<byte>) : int =
        match streams.TryGetValue broadcasting with
        | true, groups ->
            let mutable receivers = 0
            for group in groups do
                receivers <- receivers + group.Publish(group.Frame payload)
            if stats.Retained > Volatile.Read(&totalBudget) then this.ShedLater()
            receivers
        | _ -> 0

    /// Round 4 verifier: the most all of the hub's logs hold together (`CAMPFIRE_CABLE_HUB_BYTES`). Each group's own budget bounds one
    /// room's backlog, but not how many there are: every room, private stream and channel identifier (a client writes its own; each
    /// is a group with its own copy of the frames) can hold its budget. Over this, the furthest-behind subscribers anywhere are cut.
    member _.TotalBudget
        with get () = Volatile.Read(&totalBudget)
        and set (bytes: int64) = Volatile.Write(&totalBudget, bytes)

    static member DefaultTotalBytes = 1024L * 1024L * 1024L

    /// One thread pool item at a time, at most every 10 ms, sheds (`Shed`).
    member private this.ShedLater() : unit =
        let now = Diagnostics.Stopwatch.GetTimestamp()
        if now - Volatile.Read(&shedAt) >= Diagnostics.Stopwatch.Frequency / 100L && Interlocked.CompareExchange(&shedding, 1, 0) = 0 then
            Volatile.Write(&shedAt, now)
            ThreadPool.UnsafeQueueUserWorkItem(
                WaitCallback(fun _ ->
                    try
                        this.Shed()
                    finally
                        Volatile.Write(&shedding, 0)),
                null
            )
            |> ignore

    /// Unit R5.2: brings the logs under `TotalBudget`. First every log empties the slots its subscribers have read (what a chunk holds
    /// beyond that is not memory anyone needs), so a client that reads, however many streams it has, pins nothing. If the logs still
    /// hold more, the subscribers with the most bytes yet to read, in any chunk of any log, are cut one at a time until they do not:
    /// the memory over the total is held by clients that are not reading, and a log left without subscribers holds nothing. Rails
    /// holds all of it, in a per-connection queue that never ends.
    member internal _.Shed() : unit =
        if stats.Retained > Volatile.Read(&totalBudget) then
            let logs = Collections.Generic.List<LogGroup>()
            for groups in streams.Values do
                for group in groups do
                    match group with
                    | :? LogGroup as log -> logs.Add log
                    | _ -> ()
            for log in logs do
                log.Compact()
            if stats.Retained > Volatile.Read(&totalBudget) then
                let behind = Collections.Generic.List<struct (int64 * LogGroup * Subscriber)>()
                for log in logs do
                    log.Collect behind
                behind.Sort(fun (struct (a, _, _)) (struct (b, _, _)) -> b.CompareTo a)
                let cut = Collections.Generic.List<Wake>()
                let mutable i = 0
                while i < behind.Count && stats.Retained > Volatile.Read(&totalBudget) do
                    let struct (_, log, subscriber) = behind[i]
                    match log.CutOne subscriber with
                    | null -> ()
                    | wake -> cut.Add wake
                    i <- i + 1
                if cut.Count > 0 then LogGroup.CutLater(cut, stats, onCut, Volatile.Read(&totalBudget))

    member this.Broadcast(broadcasting: string, payload: string) : int =
        let bytes = Encoding.UTF8.GetBytes payload
        this.Broadcast(broadcasting, ReadOnlySpan bytes)

    /// Subscribes to `broadcasting`, receiving each payload wrapped as a message frame for the
    /// encoded channel `identifier`, or raw when it's null. `wake` is set when a frame arrives.
    member this.Subscribe(broadcasting: string, identifier: string | null, wake: Wake) : Subscriber =
        lock gate (fun () ->
            let groups =
                match streams.TryGetValue broadcasting with
                | true, groups -> groups
                | _ -> Array.empty
            let existing = groups |> Array.tryFind (fun g -> String.Equals(g.Identifier, identifier, StringComparison.Ordinal))
            let group =
                match existing with
                | Some group -> group
                | None ->
                    let group: GroupBase =
                        if ring || BenchFlip.get "log" = "ring" then RingGroup(identifier, capacity) else LogGroup(identifier, capacity, lagBytes, stats, onCut)
                    streams[broadcasting] <- Array.append groups [| group |]
                    if CableTrace.Enabled then CableTrace.GroupCreated(group.Id, broadcasting, identifier)
                    group
            group.Add(wake, this, broadcasting))

    /// Number of broadcastings with at least one live subscriber group.
    member _.StreamCount = streams.Count

    /// How many groups serve `broadcasting`.
    member internal _.GroupCount(broadcasting: string) : int =
        match streams.TryGetValue broadcasting with
        | true, groups -> groups.Length
        | _ -> 0

    /// Bytes the logs hold now, and at most since the hub was made (one shared copy of each frame per group, however many
    /// subscribers), and how many subscribers they have cut for being over the budget. Zero with `ring`.
    member _.RetainedBytes: int64 = stats.Retained
    member _.RetainedPeakBytes: int64 = stats.Peak
    member _.CutCount: int64 = stats.Cuts

    /// Unit R4.5: whether more than half of `broadcasting`'s subscribers are more than `frames` frames behind: the fan-out cannot keep
    /// up with what is posted, and a poster should wait (`Broadcasts.AwaitRoom`) rather than let the backlog grow to the budget.
    ///
    /// Round 4 verifier: counted over all of the broadcasting's groups (a client picks its identifier, so a group of its own is one
    /// client), and a subscriber whose connection has waited `ReaderBoundAfter` or longer on one socket write counts as not behind: it is
    /// behind because it reads slowly or not at all, which waiting posters cannot help (the byte budget and the stall cut it). It still
    /// counts among the subscribers: leaving it out of both sides closed the gate more often than R4.5's verdict under bin/reliability's
    /// saturated cable profiles (10-15% fewer messages a second), because there the connections waiting on their sockets are mostly near
    /// the head; counted as not behind, the verdict can only be the same as R4.5's or open.
    member _.Congested(broadcasting: string, frames: int) : bool =
        match streams.TryGetValue broadcasting with
        | true, groups ->
            let waitTicks = int64 ((Hub.ReaderBoundAfter: TimeSpan).TotalSeconds * float Diagnostics.Stopwatch.Frequency)
            let mutable behind = 0L
            let mutable counted = 0L
            for group in groups do
                let packed = group.Tally(frames, waitTicks)
                behind <- behind + (packed >>> 32)
                counted <- counted + (packed &&& 0xFFFFFFFFL)
            counted > 0L && behind * 2L > counted
        | _ -> false

    /// Round 4 verifier: how long a connection waits on one socket write before `Congested` treats it as limited by its reader.
    static member val ReaderBoundAfter = TimeSpan.FromMilliseconds 250.0 with get, set

    /// Frees the log behind the oldest subscriber of every group, and what every subscriber has read of the chunk it is in (the heartbeat
    /// calls it).
    member this.Trim() : unit =
        for groups in streams.Values do
            for group in groups do
                match group with
                | :? LogGroup as log -> log.Trim()
                | _ -> ()
        // Round 4 verifier: a hub over its total that nobody publishes to any more is shed on the beat.
        if stats.Retained > Volatile.Read(&totalBudget) then this.ShedLater()

    member internal _.Release(subscriber: Subscriber) : unit =
        lock gate (fun () ->
            subscriber.Group.Remove subscriber
            match streams.TryGetValue subscriber.Broadcasting with
            | true, groups ->
                let keep (g: GroupBase) =
                    if not (obj.ReferenceEquals(g, subscriber.Group)) || g.Count > 0 then
                        true
                    else
                        g.Retire()
                        false
                let remaining = groups |> Array.filter keep
                if remaining.Length = 0 then streams.TryRemove subscriber.Broadcasting |> ignore
                elif remaining.Length <> groups.Length then streams[subscriber.Broadcasting] <- remaining
            | _ -> ())
