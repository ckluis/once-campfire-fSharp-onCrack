// Port of rust/crates/cable/src/pubsub.rs
//
// In-process replacement for the Redis subscription adapter: a ring buffer per group of subscribers
// (what `tokio::sync::broadcast` is in Rust), created on first subscribe and dropped with the last
// subscriber of a broadcasting.
//
// Payloads are already-encoded JSON, as they are on the Redis wire. Subscribers that would wrap a
// payload identically (the same channel identifier) share one ring, and each broadcast builds their
// `{"identifier":...,"message":...}` frame once for all of them. Each ring is bounded; a subscriber
// that falls behind is told it lagged and its connection is closed with `reconnect: true` rather than
// silently skipping messages.
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

/// The subscribers of one broadcasting that receive identical frames: the payload wrapped for the
/// same encoded channel identifier, or the raw payload when `Identifier` is null.
[<Sealed>]
type internal Group(identifier: string | null, capacity: int) =
    // `capacity + 1` slots, so that the slot a publish is writing never holds a frame a reader
    // still within `capacity` of the tail can want.
    let slots: Frame[] = Array.zeroCreate (capacity + 1)
    let mutable tail = 0L
    let mutable receivers: Subscriber[] = Array.zeroCreate 4
    let mutable count = 0

    let prefix: byte[] | null =
        match identifier with
        | null -> null
        | identifier -> Encoding.UTF8.GetBytes(Protocol.messagePrefix identifier)

    member _.Identifier = identifier
    member _.Capacity = capacity

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

    member _.Count = Volatile.Read(&count)

    /// Appends the frame and wakes every subscriber. Returns how many there are.
    member _.Publish(frame: Frame) : int =
        lock slots (fun () ->
            Volatile.Write(&slots[int (tail % int64 slots.Length)], frame)
            Volatile.Write(&tail, tail + 1L)
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
            count)

    /// A subscriber that will see what is published from now on.
    member this.Add(wake: Wake, hub: Hub, broadcasting: string) : Subscriber =
        lock slots (fun () ->
            let subscriber = new Subscriber(this, hub, broadcasting, wake, tail)
            if count = receivers.Length then Array.Resize(&receivers, count * 2)
            receivers[count] <- subscriber
            Volatile.Write(&count, count + 1)
            subscriber)

    member _.Remove(subscriber: Subscriber) : unit =
        lock slots (fun () ->
            let at = Array.IndexOf(receivers, subscriber, 0, count)
            if at >= 0 then
                receivers[at] <- receivers[count - 1]
                receivers[count - 1] <- Unchecked.defaultof<_>
                Volatile.Write(&count, count - 1))

    /// Reads from `position`: the frame there, or whether there is none yet or the ring has
    /// moved past it.
    member _.TryRead(position: byref<int64>, frame: byref<Frame>) : RecvStatus =
        let t = Volatile.Read(&tail)
        if position = t then
            RecvStatus.Empty
        elif t - position > int64 capacity then
            position <- t - int64 capacity
            RecvStatus.Lagged
        else
            let found = Volatile.Read(&slots[int (position % int64 slots.Length)])
            // A publish may have wrapped around to this slot while it was being read.
            let t = Volatile.Read(&tail)
            if t - position > int64 capacity then
                position <- t - int64 capacity
                RecvStatus.Lagged
            else
                frame <- found
                position <- position + 1L
                RecvStatus.Got

/// One subscription's place in a group's ring.
and [<Sealed>] Subscriber internal (group: Group, hub: Hub, broadcasting: string, wake: Wake, start: int64) =
    let mutable position = start
    let mutable stopped = 0

    member _.Broadcasting: string = broadcasting
    member internal _.Wake: Wake = wake
    member internal _.Group: Group = group
    member internal _.Hub: Hub = hub

    /// Whether it has been disposed: it reads nothing more.
    member _.Stopped = Volatile.Read(&stopped) <> 0

    /// The next frame, if there is one. Read by one thread at a time.
    member this.TryRecv(frame: byref<Frame>) : RecvStatus =
        if this.Stopped then RecvStatus.Empty else group.TryRead(&position, &frame)

    interface IDisposable with
        member this.Dispose() =
            if Interlocked.Exchange(&stopped, 1) = 0 then hub.Release this

/// The broadcast hub: `Hub.Broadcast` publishes to every subscriber of a broadcasting.
and [<Sealed>] Hub(capacity: int) =
    // tokio rounds a channel's capacity up to a power of two.
    let capacity = int (BitOperations.RoundUpToPowerOf2(uint32 (max capacity 1)))
    let streams = ConcurrentDictionary<string, Group[]>(StringComparer.Ordinal)
    let gate = obj ()

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
                    let group = Group(identifier, capacity)
                    streams[broadcasting] <- Array.append groups [| group |]
                    group
            group.Add(wake, this, broadcasting))

    /// Number of broadcastings with at least one live subscriber ring.
    member _.StreamCount = streams.Count

    /// How many rings serve `broadcasting`.
    member internal _.GroupCount(broadcasting: string) : int =
        match streams.TryGetValue broadcasting with
        | true, groups -> groups.Length
        | _ -> 0

    member internal _.Release(subscriber: Subscriber) : unit =
        lock gate (fun () ->
            subscriber.Group.Remove subscriber
            match streams.TryGetValue subscriber.Broadcasting with
            | true, groups ->
                let remaining = groups |> Array.filter (fun g -> not (obj.ReferenceEquals(g, subscriber.Group)) || g.Count > 0)
                if remaining.Length = 0 then streams.TryRemove subscriber.Broadcasting |> ignore
                elif remaining.Length <> groups.Length then streams[subscriber.Broadcasting] <- remaining
            | _ -> ())
