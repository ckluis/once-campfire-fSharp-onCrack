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

    /// Wakes the connection, which finds its subscriber lagged and says goodbye; its socket is aborted after `CutGrace` if it
    /// has not finished (a client that has stopped reading cannot take the goodbye). Called from a thread pool item.
    member this.Cut() : unit =
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
    let prefix: byte[] | null =
        match identifier with
        | null -> null
        | identifier -> Encoding.UTF8.GetBytes(Protocol.messagePrefix identifier)

    member _.Identifier = identifier

    /// The frame a payload makes for this group's subscribers.
    member _.Frame(payload: ReadOnlySpan<byte>) : Frame =
        match prefix with
        | null -> Frame(payload.ToArray())
        | prefix ->
            let bytes = GC.AllocateUninitializedArray<byte>(prefix.Length + payload.Length + 1)
            prefix.CopyTo(bytes, 0)
            payload.CopyTo(Span(bytes, prefix.Length, payload.Length))
            bytes[bytes.Length - 1] <- byte '}'
            Frame bytes

    abstract Count: int

    /// Appends the frame and wakes every subscriber. Returns how many there are.
    abstract Publish: Frame -> int

    /// A subscriber that will see what is published from now on.
    abstract Add: Wake * Hub * string -> Subscriber

    abstract Remove: Subscriber -> unit

    /// The group has been dropped from its hub: it no longer counts toward the hub's retained bytes.
    abstract Retire: unit -> unit
    default _.Retire() = ()

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

    /// Moves `head` to the oldest chunk a subscriber is in (or the tail, with none), freeing what is behind it. Under `gate`.
    let trim () : unit =
        let mutable oldest = tail
        for i in 0 .. count - 1 do
            let chunk = receivers[i].Chunk
            if chunk.Id < oldest.Id then oldest <- chunk
        if oldest.Id > head.Id then
            if not retired then stats.Add(-(oldest.Start - head.Start))
            head <- oldest

    /// Cuts the subscribers in the oldest chunk until the log is within its budget (or only the tail's chunk is left, which is
    /// at most `chunkSize` frames). Returns the cut subscribers' wakes, for a thread pool item to close. Under `gate`.
    let enforce () : Collections.Generic.List<Wake> | null =
        let mutable cut: Collections.Generic.List<Wake> | null = null
        trim ()
        while written - head.Start > budget && not (obj.ReferenceEquals(head, tail)) do
            let mutable i = count - 1
            while i >= 0 do
                let subscriber = receivers[i]
                if obj.ReferenceEquals(subscriber.Chunk, head) then
                    subscriber.MarkOverrun()
                    receivers[i] <- receivers[count - 1]
                    receivers[count - 1] <- Unchecked.defaultof<_>
                    Volatile.Write(&count, count - 1)
                    match cut with
                    | null -> cut <- Collections.Generic.List<Wake>()
                    | _ -> ()
                    (nonNull cut).Add subscriber.Wake
                i <- i - 1
            trim ()
        cut

    override _.Count = Volatile.Read(&count)

    override _.Publish(frame: Frame) : int =
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
                chunk.Sequences[chunk.Filled] <- stats.NextSequence()
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
        | wakes ->
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
        shared

    override this.Add(wake: Wake, hub: Hub, broadcasting: string) : Subscriber =
        lock gate (fun () ->
            let subscriber = new Subscriber(this, hub, broadcasting, wake, 0L, tail, tail.Filled)
            if count = receivers.Length then Array.Resize(&receivers, count * 2)
            receivers[count] <- subscriber
            Volatile.Write(&count, count + 1)
            subscriber)

    override _.Remove(subscriber: Subscriber) : unit =
        lock gate (fun () ->
            let at = Array.IndexOf(receivers, subscriber, 0, count)
            if at >= 0 then
                receivers[at] <- receivers[count - 1]
                receivers[count - 1] <- Unchecked.defaultof<_>
                Volatile.Write(&count, count - 1)
                // The oldest subscriber leaving frees the log behind the next one.
                if obj.ReferenceEquals(subscriber.Chunk, head) && not (obj.ReferenceEquals(head, tail)) then trim ())

    override _.Retire() : unit =
        lock gate (fun () ->
            if not retired then
                retired <- true
                stats.Add(-(written - head.Start)))

    /// Frees what no subscriber can read: the heartbeat calls it, so a log that nobody publishes to any more does not hold what
    /// its subscribers have since read.
    member _.Trim() : unit =
        lock gate (fun () -> if not (obj.ReferenceEquals(head, tail)) then trim ())

    /// Bytes this log holds now (from its oldest chunk).
    member _.Retained = lock gate (fun () -> written - head.Start)

    /// Finds `subscriber`'s next slot, following the link out of a chunk it has read to the end.
    static member private Locate(subscriber: Subscriber, chunk: byref<Chunk>, index: byref<int>) : bool =
        chunk <- subscriber.Chunk
        index <- subscriber.Index
        if index = chunk.Size then
            // All of this chunk is read; the next may not exist yet.
            match chunk.Next with
            | null -> ()
            | next ->
                chunk <- next
                index <- 0
                subscriber.MoveTo next
                subscriber.Index <- 0
        index < chunk.Filled

    override _.TryRead(subscriber: Subscriber, frame: byref<Frame>) : RecvStatus =
        if subscriber.Overrun then
            RecvStatus.Lagged
        else
            let mutable chunk = subscriber.Chunk
            let mutable index = 0
            if LogGroup.Locate(subscriber, &chunk, &index) then
                frame <- chunk.Frames[index]
                subscriber.Index <- index + 1
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

    override _.Publish(frame: Frame) : int =
        lock slots (fun () ->
            Volatile.Write(&slots[int (tail % int64 slots.Length)], frame)
            Volatile.Write(&tail, tail + 1L)
            GroupBase.WakeAll(receivers, count)
            count)

    override this.Add(wake: Wake, hub: Hub, broadcasting: string) : Subscriber =
        lock slots (fun () ->
            let subscriber = new Subscriber(this, hub, broadcasting, wake, tail, Chunk.None, 0)
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
    let mutable stopped = 0
    let mutable overrun = 0

    member _.Broadcasting: string = broadcasting
    member internal _.Wake: Wake = wake
    member internal _.Group: GroupBase = group
    member internal _.Hub: Hub = hub

    /// The ring's place (ring groups).
    member val internal Position = start with get, set

    /// The log's place: the chunk, which the group's `trim` reads from its own thread, and the next slot in it.
    member internal _.Chunk: Chunk = Volatile.Read(&chunk)
    member val internal Index = index0 with get, set
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

    new(capacity: int) = Hub(capacity, Hub.DefaultLagBytes, false, null)
    new(capacity: int, lagBytes: int64, ring: bool) = Hub(capacity, lagBytes, ring, null)

    /// A group's log may hold this much behind its oldest subscriber (`CAMPFIRE_CABLE_LAG_BYTES`): about 45,000 Campfire messages.
    static member DefaultLagBytes = 64L * 1024L * 1024L

    /// onCrack: whether `broadcasting` has a subscriber now, so that a broadcast nobody would receive needn't be
    /// encoded. One that subscribes after this answer misses the broadcast, as it would one sent a moment earlier.
    member _.HasSubscribers(broadcasting: string) : bool = streams.ContainsKey broadcasting

    /// Publishes to every current subscriber of `broadcasting`; `payload` is encoded JSON as UTF-8.
    /// Returns how many received it.
    member _.Broadcast(broadcasting: string, payload: ReadOnlySpan<byte>) : int =
        match streams.TryGetValue broadcasting with
        | true, groups ->
            let mutable receivers = 0
            for group in groups do
                receivers <- receivers + group.Publish(group.Frame payload)
            receivers
        | _ -> 0

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
                        if ring then RingGroup(identifier, capacity) else LogGroup(identifier, capacity, lagBytes, stats, onCut)
                    streams[broadcasting] <- Array.append groups [| group |]
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

    /// Frees the log behind the oldest subscriber of every group (the heartbeat calls it).
    member _.Trim() : unit =
        for groups in streams.Values do
            for group in groups do
                match group with
                | :? LogGroup as log -> log.Trim()
                | _ -> ()

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
