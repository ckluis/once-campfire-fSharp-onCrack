// Port of the tests in rust/crates/cable/src/pubsub.rs
module Campfire.Cable.Tests.PubsubTests

open System
open System.Threading
open Xunit
open Campfire.Cable
open Campfire.Cable.Socket

let private recv (subscriber: Subscriber) : Result<string, RecvStatus> =
    let mutable frame = Unchecked.defaultof<Frame>
    match subscriber.TryRecv(&frame) with
    | RecvStatus.Got -> Ok frame.Text
    | status -> Error status

let private frameOf (subscriber: Subscriber) : Frame =
    let mutable frame = Unchecked.defaultof<Frame>
    Assert.Equal(RecvStatus.Got, subscriber.TryRecv(&frame))
    frame

[<Fact>]
let ``delivers to every subscriber and cleans up`` () =
    let hub = Hub(8)
    let a = hub.Subscribe("room", null, Wake())
    let b = hub.Subscribe("room", null, Wake())
    Assert.Equal(2, hub.Broadcast("room", "1"))
    Assert.Equal(Ok "1", recv a)
    Assert.Equal(Ok "1", recv b)
    (a :> IDisposable).Dispose()
    Assert.Equal(1, hub.StreamCount)
    (b :> IDisposable).Dispose()
    Assert.Equal(0, hub.StreamCount)
    Assert.Equal(0, hub.Broadcast("room", "2"))

[<Fact>]
let ``wraps payloads once per identifier`` () =
    let hub = Hub(8)
    let identifier = "\"{\\\"channel\\\":\\\"RoomChannel\\\"}\""
    let a = hub.Subscribe("room", identifier, Wake())
    let b = hub.Subscribe("room", identifier, Wake())
    let other = hub.Subscribe("room", "\"other\"", Wake())
    let raw = hub.Subscribe("room", null, Wake())
    Assert.Equal(4, hub.Broadcast("room", """{"id":1}"""))

    let a, b = frameOf a, frameOf b
    Assert.Equal("""{"identifier":"{\"channel\":\"RoomChannel\"}","message":{"id":1}}""", a.Text)
    Assert.Same(a, b) // one frame shared by both subscribers
    Assert.Equal(Ok """{"identifier":"other","message":{"id":1}}""", recv other)
    Assert.Equal(Ok """{"id":1}""", recv raw)

    (other :> IDisposable).Dispose()
    (raw :> IDisposable).Dispose()
    Assert.Equal(1, hub.GroupCount "room")

// Unit R4.5: the fixed ring (`CAMPFIRE_CABLE_LOG=ring`) still cuts a subscriber that is its capacity behind.

[<Fact>]
let ``ring: slow subscribers see lag instead of gaps`` () =
    let hub = Hub(2, 0L, true)
    let slow = hub.Subscribe("room", null, Wake())
    for i in 0..4 do
        hub.Broadcast("room", string i) |> ignore
    Assert.Equal(Error RecvStatus.Lagged, recv slow)

[<Fact>]
let ``ring: a subscriber that keeps up never lags, and one that fell behind reads on from the oldest kept`` () =
    let hub = Hub(4, 0L, true)
    let steady = hub.Subscribe("room", null, Wake())
    let slow = hub.Subscribe("room", null, Wake())
    for i in 0..99 do
        hub.Broadcast("room", string i) |> ignore
        Assert.Equal(Ok(string i), recv steady)
    Assert.Equal(Error RecvStatus.Lagged, recv slow)
    // As tokio's receiver does after `Lagged`: the oldest message still in the ring comes next.
    Assert.Equal(Ok "96", recv slow)

// Unit R4.5: the log keeps every frame for a subscriber within its byte budget, however many frames behind.

let private drainAll (subscriber: Subscriber) : string list =
    let seen = Collections.Generic.List<string>()
    let mutable reading = true
    while reading do
        match recv subscriber with
        | Ok text ->
            seen.Add text
            // A reader that never gets to the end (a cursor that does not advance) fails here, not by hanging.
            if seen.Count > 5_000_000 then failwith "the subscriber reads without end"
        | Error status ->
            Assert.Equal(RecvStatus.Empty, status)
            reading <- false
    List.ofSeq seen

[<Fact>]
let ``log: a subscriber 100,000 frames behind reads every one, in order, then finds nothing`` () =
    let hub = Hub(256)
    let behind = hub.Subscribe("room", null, Wake())
    let steady = hub.Subscribe("room", null, Wake())
    for i in 0..99999 do
        hub.Broadcast("room", string i) |> ignore
    let got = drainAll behind
    Assert.Equal<string list>([ for i in 0..99999 -> string i ], got)
    Assert.Equal(100000, (drainAll steady).Length)
    Assert.Equal(0L, hub.CutCount)
    // It goes on from there.
    hub.Broadcast("room", "next") |> ignore
    Assert.Equal(Ok "next", recv behind)

[<Fact>]
let ``log: reads are exact at the chunk's edges`` () =
    for frames in [ 0; 1; 7; 8; 9; 15; 16; 17; 255; 256; 257; 511; 512; 513 ] do
        // Small chunks (8) and the default (256) both: the edges are the chunk size, a chunk and one either side.
        for chunk in [ 8; 256 ] do
            let hub = Hub(chunk)
            let late = hub.Subscribe("room", null, Wake())
            let eager = hub.Subscribe("room", null, Wake())
            let eagerSeen = Collections.Generic.List<string>()
            for i in 0 .. frames - 1 do
                hub.Broadcast("room", string i) |> ignore
                // One reader reads as it goes, so it is often at the end of a full chunk when the next publish comes.
                eagerSeen.AddRange(drainAll eager)
            let expected = [ for i in 0 .. frames - 1 -> string i ]
            Assert.Equal<string list>(expected, List.ofSeq eagerSeen)
            Assert.Equal<string list>(expected, drainAll late)
            // A subscriber added at the edge sees exactly what comes after.
            let after = hub.Subscribe("room", null, Wake())
            Assert.Equal(0, (drainAll after).Length)
            hub.Broadcast("room", "x") |> ignore
            Assert.Equal<string list>([ "x" ], drainAll after)
            Assert.Equal<string list>([ "x" ], drainAll late)

[<Fact>]
let ``log: one publisher and eight readers that stall lose and reorder nothing`` () =
    let hub = Hub(16, Int64.MaxValue, false)
    let readers = 8
    let subscribers = [| for _ in 1..readers -> hub.Subscribe("room", null, Wake()) |]
    let total = ref 0
    let running = ref true
    let deadline = Diagnostics.Stopwatch.StartNew()
    let readerTasks =
        [| for r in 0 .. readers - 1 ->
               System.Threading.Tasks.Task.Run(fun () ->
                   let random = Random(r)
                   let mutable next = 0
                   let mutable finished = false
                   while not finished do
                       match recv subscribers[r] with
                       | Ok text ->
                           if text <> string next then failwith $"reader {r}: expected {next}, got {text}"
                           next <- next + 1
                           if random.Next 20000 = 0 then Threading.Thread.Sleep(random.Next 20)
                       | Error RecvStatus.Empty ->
                           if not (Volatile.Read(&running.contents)) && next = Volatile.Read(&total.contents) then finished <- true else Threading.Thread.Yield() |> ignore
                       | Error status -> failwith $"reader {r}: {status}"
                   next) |]
    let publisher =
        System.Threading.Tasks.Task.Run(fun () ->
            let mutable i = 0
            while deadline.Elapsed < TimeSpan.FromSeconds 2.0 do
                hub.Broadcast("room", string i) |> ignore
                i <- i + 1
            Volatile.Write(&total.contents, i)
            Volatile.Write(&running.contents, false))
    publisher.Wait()
    let counts = readerTasks |> Array.map (fun t -> t.Result)
    for count in counts do
        Assert.Equal(total.Value, count)
    Assert.True(total.Value > 1000, $"published {total.Value}")
    Assert.Equal(0L, hub.CutCount)

let private chunkOf (subscriber: Subscriber) : WeakReference = WeakReference(subscriber.Chunk)

[<System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)>]
let private forgottenChunkAfterCatchUp (hub: Hub) (subscribers: Subscriber list) : WeakReference =
    let first = chunkOf subscribers.Head
    for i in 0..9999 do
        hub.Broadcast("room", string i) |> ignore
    Assert.True(hub.RetainedBytes > 1000L, $"{hub.RetainedBytes}")
    for s in subscribers do
        Assert.Equal(10000, (drainAll s).Length)
    first

[<Fact>]
let ``log: chunks nobody can read are freed and the retained bytes come back down`` () =
    let hub = Hub(8)
    let subscribers = [ for _ in 1..3 -> hub.Subscribe("room", null, Wake()) ]
    let first = forgottenChunkAfterCatchUp hub subscribers
    // Nothing is published now: the heartbeat's trim frees what the readers have passed.
    hub.Trim()
    // The subscribers are in the last chunk (8 frames of up to 5 bytes).
    Assert.True(hub.RetainedBytes <= 8L * 5L, $"{hub.RetainedBytes} retained after catching up")
    Assert.True(hub.RetainedPeakBytes >= 10000L, $"{hub.RetainedPeakBytes}")
    GC.Collect()
    GC.WaitForPendingFinalizers()
    GC.Collect()
    Assert.False(first.IsAlive, "the first chunk is still held")
    // Disposing the last subscriber of the group takes the rest.
    for s in subscribers do
        (s :> IDisposable).Dispose()
    Assert.Equal(0L, hub.RetainedBytes)

[<Fact>]
let ``log: the oldest subscriber leaving or the others moving on frees the log behind it`` () =
    let hub = Hub(8)
    let slow = hub.Subscribe("room", null, Wake())
    let quick = hub.Subscribe("room", null, Wake())
    for i in 0..999 do
        hub.Broadcast("room", $"{i:D4}") |> ignore
    drainAll quick |> ignore
    // 1000 frames of 4 bytes; the slow one still holds all of them.
    Assert.Equal(4000L, hub.RetainedBytes)
    // Reading it all is not enough on its own to free: the group is told by the next trim.
    drainAll slow |> ignore
    hub.Trim()
    Assert.True(hub.RetainedBytes <= 8L * 4L, $"{hub.RetainedBytes}")
    // A dispose of the one holding the oldest chunk does it too.
    let holder = hub.Subscribe("room", null, Wake())
    for i in 0..999 do
        hub.Broadcast("room", $"{i:D4}") |> ignore
    drainAll quick |> ignore
    drainAll slow |> ignore
    Assert.True(hub.RetainedBytes >= 4000L)
    (holder :> IDisposable).Dispose()
    Assert.True(hub.RetainedBytes <= 8L * 4L, $"{hub.RetainedBytes}")

[<Fact>]
let ``log: a subscriber over the byte budget is cut, the others read on, and its connection is aborted`` () =
    task {
        // Chunks of 4 frames of 1,000 bytes; the budget is 20 KB.
        let hub = Hub(4, 20_000L, false)
        let cutWake = Wake()
        let aborted = Threading.Tasks.TaskCompletionSource()
        cutWake.Abort <- (fun () -> aborted.TrySetResult() |> ignore)
        let stalled = hub.Subscribe("room", null, cutWake)
        let steadyWake = Wake()
        steadyWake.Abort <- (fun () -> failwith "the steady subscriber must not be cut")
        let steady = hub.Subscribe("room", null, steadyWake)
        let payload = String('x', 1000)
        let mutable steadyCount = 0
        for _ in 0..99 do
            hub.Broadcast("room", payload) |> ignore
            steadyCount <- steadyCount + (drainAll steady).Length
        Assert.Equal(100, steadyCount)
        Assert.Equal(1L, hub.CutCount)
        Assert.Equal(Error RecvStatus.Lagged, recv stalled)
        // It stays lagged; the memory it pinned is gone: the log holds at most the budget and the slack of one chunk.
        Assert.Equal(Error RecvStatus.Lagged, recv stalled)
        Assert.True(hub.RetainedBytes <= 20_000L + 4L * 1008L, $"{hub.RetainedBytes} retained")
        Assert.True(hub.RetainedPeakBytes <= 20_000L + 2L * 4L * 1008L, $"{hub.RetainedPeakBytes} peak")
        // Its connection is woken, and cut once the grace is over (the default is a second).
        let! woke = cutWake.WaitAsync()
        Assert.True woke
        let! finished = Threading.Tasks.Task.WhenAny(aborted.Task, Threading.Tasks.Task.Delay(TimeSpan.FromSeconds 5.0))
        Assert.True(obj.ReferenceEquals(finished, aborted.Task), "the cut connection was never aborted")
        // A connection that finished by itself in the grace is left alone.
        let wake = Wake()
        let touched = ref false
        wake.Abort <- (fun () -> touched.Value <- true)
        wake.Retire()
        wake.Cut()
        do! Threading.Tasks.Task.Delay(TimeSpan.FromSeconds 1.5)
        Assert.False touched.Value
        // The cut subscriber is out of its group: the next broadcast does not count it.
        Assert.Equal(1, hub.Broadcast("room", payload))
    }

[<Fact>]
let ``log: a subscriber that never reads is cut once 70 MB have been published past a 64 MB budget`` () =
    Assert.Equal(256L * 1024L * 1024L, Hub.DefaultLagBytes)
    let budget = 64L * 1024L * 1024L
    let hub = Hub(256, budget, false)
    let never = hub.Subscribe("room", null, Wake())
    let steady = hub.Subscribe("room", null, Wake())
    let payload = String('x', 1400)
    let mutable steadyCount = 0
    // 50,000 frames of about 1.4 KB: past the 64 MB default budget.
    for i in 0..49999 do
        hub.Broadcast("room", payload) |> ignore
        if i % 100 = 99 then steadyCount <- steadyCount + (drainAll steady).Length
    steadyCount <- steadyCount + (drainAll steady).Length
    Assert.Equal(50000, steadyCount)
    Assert.Equal(1L, hub.CutCount)
    Assert.Equal(Error RecvStatus.Lagged, recv never)
    Assert.True(hub.RetainedPeakBytes <= budget + 256L * 1410L, $"{hub.RetainedPeakBytes}")

[<Fact>]
let ``a broadcast sets the wake of every subscriber`` () =
    task {
        let hub = Hub(8)
        let wakes = [ for _ in 1..3 -> Wake() ]
        let subscribers = [ for wake in wakes -> hub.Subscribe("room", null, wake) ]
        hub.Broadcast("room", "x") |> ignore
        for wake in wakes do
            let! woke = wake.WaitAsync()
            Assert.True woke
        ignore subscribers
    }

[<Fact>]
let ``a wake waits for a set, which counts once however many there were`` () =
    task {
        let wake = Wake()
        let waiting = wake.WaitAsync()
        Assert.False waiting.IsCompleted
        wake.Set()
        let! _ = waiting
        wake.Set()
        wake.Set()
        Assert.True(wake.WaitAsync().IsCompleted)
        Assert.False(wake.WaitAsync().IsCompleted)
    }

[<Fact>]
let ``stopped subscribers read nothing`` () =
    let hub = Hub(8)
    let subscriber = hub.Subscribe("room", null, Wake())
    hub.Broadcast("room", "1") |> ignore
    (subscriber :> IDisposable).Dispose()
    Assert.True subscriber.Stopped
    Assert.Equal(Error RecvStatus.Empty, recv subscriber)
    Assert.Equal(0, hub.StreamCount)

[<Fact>]
let ``concurrent broadcasts and subscribers lose nothing`` () =
    let hub = Hub(1 <<< 16)
    let subscribers = [| for _ in 1..8 -> hub.Subscribe("room", null, Wake()) |]
    let senders = 4
    let each = 5000
    let tasks =
        [| for s in 0 .. senders - 1 ->
               System.Threading.Tasks.Task.Run(fun () ->
                   for i in 0 .. each - 1 do
                       hub.Broadcast("room", $"{s}:{i}") |> ignore) |]
    System.Threading.Tasks.Task.WaitAll tasks
    for subscriber in subscribers do
        let seen = Collections.Generic.List<string>()
        let mutable reading = true
        while reading do
            match recv subscriber with
            | Ok text -> seen.Add text
            | Error status ->
                Assert.Equal(RecvStatus.Empty, status)
                reading <- false
        Assert.Equal(senders * each, seen.Count)
        // Each sender's messages arrive in the order it sent them.
        for s in 0 .. senders - 1 do
            let own = seen |> Seq.filter (fun t -> t.StartsWith $"{s}:") |> Seq.map (fun t -> int (t.Substring(t.IndexOf ':' + 1))) |> Seq.toArray
            Assert.Equal<int[]>([| 0 .. each - 1 |], own)

// onCrack (unit R2.1): `WakeBatch` holds the wakes a thread's broadcasts make until its scope ends.

[<Fact>]
let ``wakes held in a batch are set when it ends, each once, after every frame is in`` () =
    let hub = Hub(8)
    let wake = Wake()
    let room = hub.Subscribe("room", null, wake)
    let unread = hub.Subscribe("unread", null, wake)
    let other = Wake()
    let bystander = hub.Subscribe("room", null, other)
    let parked = wake.WaitAsync()
    let parkedOther = other.WaitAsync()
    WakeBatch.Begin()
    hub.Broadcast("room", "append") |> ignore
    hub.Broadcast("unread", "ping") |> ignore
    hub.Broadcast("room", "append 2") |> ignore
    Assert.False(parked.IsCompleted, "woken inside the batch")
    Assert.False(parkedOther.IsCompleted, "woken inside the batch")
    WakeBatch.End()
    Assert.True(parked.IsCompleted)
    Assert.True(parkedOther.IsCompleted)
    // One Set each: the next wait parks.
    Assert.False(wake.WaitAsync().IsCompleted)
    Assert.Equal(Ok "append", recv room)
    Assert.Equal(Ok "append 2", recv room)
    Assert.Equal(Ok "ping", recv unread)
    Assert.Equal(Ok "append", recv bystander)

[<Fact>]
let ``nested batches wake at the outermost end, and a throwing one still wakes`` () =
    let hub = Hub(8)
    let wake = Wake()
    let sub = hub.Subscribe("room", null, wake)
    let parked = wake.WaitAsync()
    WakeBatch.Begin()
    WakeBatch.Begin()
    hub.Broadcast("room", "1") |> ignore
    WakeBatch.End()
    Assert.False(parked.IsCompleted)
    WakeBatch.End()
    Assert.True(parked.IsCompleted)
    Assert.Equal(Ok "1", recv sub)
    let parked = wake.WaitAsync()
    Assert.Throws<InvalidOperationException>(fun () ->
        WakeBatch.Run(fun () ->
            hub.Broadcast("room", "2") |> ignore
            raise (InvalidOperationException "boom")))
    |> ignore
    Assert.True(parked.IsCompleted)
    Assert.Equal(Ok "2", recv sub)
    // Outside any batch, a broadcast wakes at once again.
    let parked = wake.WaitAsync()
    hub.Broadcast("room", "3") |> ignore
    Assert.True(parked.IsCompleted)

[<Fact>]
let ``a flush sets what is held and holds what comes after`` () =
    let hub = Hub(8)
    let wake = Wake()
    let sub = hub.Subscribe("room", null, wake)
    let parked = wake.WaitAsync()
    WakeBatch.Begin()
    hub.Broadcast("room", "1") |> ignore
    WakeBatch.Flush()
    Assert.True(parked.IsCompleted)
    Assert.Equal(Ok "1", recv sub)
    let parked = wake.WaitAsync()
    hub.Broadcast("room", "2") |> ignore
    Assert.False(parked.IsCompleted, "a broadcast after the flush is held again")
    WakeBatch.End()
    Assert.True(parked.IsCompleted)
    Assert.Equal(Ok "2", recv sub)

[<Fact>]
let ``batches on many threads at once lose no wake`` () =
    task {
        let hub = Hub(4096)
        let publishers, perPublisher, readers = 8, 400, 16
        let total = publishers * perPublisher
        let subs = [| for _ in 1..readers -> let w = Wake() in w, hub.Subscribe("room", null, w) |]
        let readerTasks =
            [| for (wake, sub) in subs ->
                   task {
                       let mutable got = 0
                       while got < total do
                           let! _ = wake.WaitAsync()
                           let mutable reading = true
                           while reading do
                               match recv sub with
                               | Ok _ -> got <- got + 1
                               | Error RecvStatus.Empty -> reading <- false
                               | Error status -> failwith $"{status}"
                       return got
                   } |]
        let publisherTasks =
            [| for p in 1..publishers ->
                   Threading.Tasks.Task.Run(fun () ->
                       for i in 1..perPublisher do
                           // Scopes of one to three broadcasts, some flushed part way.
                           WakeBatch.Begin()
                           hub.Broadcast("room", $"{p}-{i}") |> ignore
                           if i % 3 = 0 then WakeBatch.Flush()
                           WakeBatch.End()) |]
        do! Threading.Tasks.Task.WhenAll publisherTasks
        let! counts = Threading.Tasks.Task.WhenAll(readerTasks).WaitAsync(TimeSpan.FromSeconds 20.0)
        for count in counts do
            Assert.Equal(total, count)
    }

// Unit R4.5 change 2: a connection takes its streams' frames in publish order, across the streams.

let private mergeAll (readers: Collections.Generic.List<Subscriber>) (limit: int) : Collections.Generic.List<string> * Connection.Drained list =
    let merge = Connection.Merge()
    let pending = Collections.Generic.List<Frame>()
    let taken = Collections.Generic.List<string>()
    let outcomes = Collections.Generic.List<Connection.Drained>()
    let mutable going = true
    while going do
        let outcome = merge.Drain(readers, pending, limit)
        outcomes.Add outcome
        for frame in pending do
            taken.Add frame.Text
        pending.Clear()
        if outcome <> Connection.Drained.Full then going <- false
    taken, List.ofSeq outcomes

[<Fact>]
let ``merge: two interleaved streams come out in publish order, in batches, with nothing lost`` () =
    let hub = Hub(16)
    let a = hub.Subscribe("a", null, Wake())
    let b = hub.Subscribe("b", null, Wake())
    let c = hub.Subscribe("c", null, Wake())
    let random = Random(7)
    let expected = Collections.Generic.List<string>()
    // The reader is stalled while 10,000 frames go to the three streams in a random interleaving.
    for i in 0..9999 do
        let stream = [| "a"; "b"; "c" |][random.Next 3]
        let text = $"{stream}{i}"
        hub.Broadcast(stream, text) |> ignore
        expected.Add text
    let taken, outcomes = mergeAll (Collections.Generic.List [ a; b; c ]) 64
    Assert.Equal<string list>(List.ofSeq expected, List.ofSeq taken)
    Assert.Equal(Connection.Drained.Drained, List.last outcomes)
    Assert.True(outcomes.Length > 100, "taken in batches of 64")

[<Fact>]
let ``merge: a stream with a deep backlog does not hold back another`` () =
    let hub = Hub(16)
    let deep = hub.Subscribe("deep", null, Wake())
    let shallow = hub.Subscribe("shallow", null, Wake())
    for i in 0..999 do
        hub.Broadcast("deep", $"deep{i}") |> ignore
    hub.Broadcast("shallow", "one") |> ignore
    for i in 1000..1999 do
        hub.Broadcast("deep", $"deep{i}") |> ignore
    // The first batch of 64 takes 64 of deep's frames and stops before the shallow one's: it was published after the 1,000th.
    let merge = Connection.Merge()
    let pending = Collections.Generic.List<Frame>()
    let readers = Collections.Generic.List [ deep; shallow ]
    let mutable batches = 0
    let mutable position = -1
    while position < 0 && batches < 100 do
        merge.Drain(readers, pending, 64) |> ignore
        batches <- batches + 1
        position <- pending.FindIndex(fun f -> f.Text = "one")
        pending.Clear()
    // 1,000 frames of deep come before it: 16 batches of 64 (1,024), the 17th has it.
    Assert.Equal(16, batches)
    // The order of rounds 1-4 (a stream at a time) puts it after all of deep's 2,000 frames.
    let deep2 = hub.Subscribe("deep", null, Wake())
    let shallow2 = hub.Subscribe("shallow", null, Wake())
    ignore (deep2, shallow2)
    // (subscribed now, so they see only later frames: publish the same shape again for them)
    for i in 0..999 do
        hub.Broadcast("deep", $"deep{i}") |> ignore
    hub.Broadcast("shallow", "one") |> ignore
    for i in 1000..1999 do
        hub.Broadcast("deep", $"deep{i}") |> ignore
    let oldReaders = Collections.Generic.List [ deep2; shallow2 ]
    let mutable oldBatches = 0
    let mutable found = -1
    while found < 0 && oldBatches < 100 do
        Connection.drain oldReaders pending 64 |> ignore
        oldBatches <- oldBatches + 1
        found <- pending.FindIndex(fun f -> f.Text = "one")
        pending.Clear()
    Assert.Equal(32, oldBatches)

[<Fact>]
let ``merge: a lagged stream is reported and a stopped one dropped`` () =
    let hub = Hub(4, 100L, false)
    let stuck = hub.Subscribe("a", null, Wake())
    let other = hub.Subscribe("b", null, Wake())
    let payload = String('x', 60)
    for _ in 0..20 do
        hub.Broadcast("a", payload) |> ignore
    hub.Broadcast("b", "late") |> ignore
    let readers = Collections.Generic.List [ stuck; other ]
    let _, outcomes = mergeAll readers 64
    Assert.Equal(Connection.Drained.Lagged, List.last outcomes)
    (other :> IDisposable).Dispose()
    let _, outcomes = mergeAll (Collections.Generic.List [ other ]) 64
    Assert.Equal<Connection.Drained list>([ Connection.Drained.Drained ], outcomes)

// Unit R4.5: `Hub.Congested` says when most of a room's subscribers are far behind (a post then waits).

[<Fact>]
let ``congested: true only while more than half of the subscribers are more than the limit behind`` () =
    // The verdict is worked out at most every 10 ms.
    let settle () = Threading.Thread.Sleep 25
    let hub = Hub(8)
    let subscribers = [| for _ in 1..4 -> hub.Subscribe("room", null, Wake()) |]
    settle ()
    Assert.False(hub.Congested("room", 50))
    settle ()
    Assert.False(hub.Congested("nobody", 50))
    for i in 0..199 do
        hub.Broadcast("room", string i) |> ignore
    // The verdict is worked out at most every 10 ms.
    settle ()
    settle ()
    Assert.True(hub.Congested("room", 50))
    settle ()
    Assert.False(hub.Congested("room", 500), "200 frames behind is not 500")
    // Two of four caught up: exactly half is not more than half.
    drainAll subscribers[0] |> ignore
    drainAll subscribers[1] |> ignore
    settle ()
    settle ()
    Assert.False(hub.Congested("room", 50))
    // One more behind the limit tips it again: publish 100 more, so those two are 100 behind and the others 300.
    for i in 0..99 do
        hub.Broadcast("room", string i) |> ignore
    settle ()
    settle ()
    Assert.True(hub.Congested("room", 50))
    drainAll subscribers[2] |> ignore
    settle ()
    settle ()
    Assert.False(hub.Congested("room", 250), "only one subscriber is more than 250 behind")
    settle ()
    Assert.True(hub.Congested("room", 50), "three of four are more than 50 behind")
    for s in subscribers do
        drainAll s |> ignore
    settle ()
    settle ()
    Assert.False(hub.Congested("room", 0 + 1))

[<Fact>]
let ``congested: a ring has no measure`` () =
    let hub = Hub(8, 0L, true)
    let s = hub.Subscribe("room", null, Wake())
    for i in 0..99 do
        hub.Broadcast("room", string i) |> ignore
    Threading.Thread.Sleep 25
    Assert.False(hub.Congested("room", 1))
    ignore s

// Round 4 verifier: the pressure gate is about the fan-out falling behind, not about one client. A room's verdict is taken over all of
// its subscribers, whatever identifier each subscribed with (a client picks its own: key order and spacing make a group of its own),
// and a subscriber whose connection has been waiting on one socket write for longer than `Hub.ReaderBoundAfter` is limited by its own
// reader, so it is left out (the byte budget deals with it).

[<Fact>]
let ``congested (verifier): one subscriber under an identifier of its own does not make the room congested`` () =
    let hub = Hub(8)
    let shared = "\"{\\\"channel\\\":\\\"Turbo::StreamsChannel\\\",\\\"signed_stream_name\\\":\\\"x\\\"}\""
    let own = "\"{\\\"signed_stream_name\\\":\\\"x\\\",\\\"channel\\\":\\\"Turbo::StreamsChannel\\\"}\""
    let readers = [| for _ in 1..4 -> hub.Subscribe("room", shared, Wake()) |]
    let attacker = hub.Subscribe("room", own, Wake())
    Assert.Equal(2, hub.GroupCount "room")
    for i in 0..2999 do
        hub.Broadcast("room", string i) |> ignore
        if i % 100 = 0 then
            for r in readers do
                drainAll r |> ignore
    for r in readers do
        drainAll r |> ignore
    Threading.Thread.Sleep 25
    Assert.False(hub.Congested("room", 2048), "one of five subscribers is behind, alone in a group of its own")
    // Four of five behind is congestion, whatever the identifiers.
    for i in 0..2999 do
        hub.Broadcast("room", string i) |> ignore
    drainAll attacker |> ignore
    Threading.Thread.Sleep 25
    Assert.True(hub.Congested("room", 2048), "four of five are behind")

[<Fact>]
let ``congested (verifier): subscribers whose connections wait on their sockets do not count`` () =
    let hub = Hub(8)
    let wakes = [| for _ in 1..3 -> Wake() |]
    let subscribers = wakes |> Array.map (fun wake -> hub.Subscribe("room", null, wake))
    for i in 0..2999 do
        hub.Broadcast("room", string i) |> ignore
    drainAll subscribers[0] |> ignore
    let settle () = Threading.Thread.Sleep 25
    settle ()
    Assert.True(hub.Congested("room", 2048), "two of three are behind")
    // Their connections have waited a second on one socket write: their readers are the limit, not the fan-out.
    let longAgo = Diagnostics.Stopwatch.GetTimestamp() - Diagnostics.Stopwatch.Frequency
    wakes[1].WriteWaitSince <- longAgo
    wakes[2].WriteWaitSince <- longAgo
    settle ()
    Assert.False(hub.Congested("room", 2048), "both behind are waiting on their sockets")
    // A write that began just now still counts; so does one that completed.
    wakes[1].WriteWaitSince <- Diagnostics.Stopwatch.GetTimestamp()
    wakes[2].WriteWaitSince <- 0L
    settle ()
    Assert.True(hub.Congested("room", 2048), "neither has waited long")
    // Everyone waiting long: nobody counted, nothing congested.
    for wake in wakes do
        wake.WriteWaitSince <- longAgo
    settle ()
    Assert.False(hub.Congested("room", 2048))

// Round 4 verifier: each group's byte budget bounds one backlog, not how many there are. Every room, private stream and channel
// identifier (a client writes its own) is a group with its own copy of the frames, so the hub holds all of them to `TotalBudget`
// (`CAMPFIRE_CABLE_HUB_BYTES`), cutting the subscribers furthest behind, anywhere, first.

/// Polls `condition` for up to 5 s, calling the heartbeat's `Trim` between looks.
let private eventually (hub: Hub) (condition: unit -> bool) : bool =
    let deadline = DateTime.UtcNow.AddSeconds 5.0
    let mutable ok = condition ()
    while not ok && DateTime.UtcNow < deadline do
        Threading.Thread.Sleep 20
        hub.Trim()
        ok <- condition ()
    ok

[<Fact>]
let ``hub budget (verifier): slow subscribers in many rooms and groups are held to the hub's total, the readers untouched`` () =
    let run (total: int64) =
        let hub = Hub(8, 1024L * 1024L, false)
        hub.TotalBudget <- total
        let rooms = [| for r in 0..9 -> $"room-{r}" |]
        let keepers = rooms |> Array.map (fun room -> hub.Subscribe(room, null, Wake()))
        // A slow subscriber in each room, and nine more in room-0 under identifiers of their own: nineteen groups, each under 1 MB.
        let slow = [ for room in rooms -> hub.Subscribe(room, "\"a\"", Wake()) ] @ [ for k in 1..9 -> hub.Subscribe("room-0", $"\"id{k}\"", Wake()) ]
        let seen = Array.init keepers.Length (fun _ -> Collections.Generic.List<string>())
        for i in 0..599 do
            for room in rooms do
                hub.Broadcast(room, $"\"{i}:{String('p', 1000)}\"") |> ignore
            if i % 50 = 0 then
                keepers |> Array.iteri (fun k keeper -> seen[k].AddRange(drainAll keeper))
        keepers |> Array.iteri (fun k keeper -> seen[k].AddRange(drainAll keeper))
        for k in 0 .. keepers.Length - 1 do
            Assert.Equal(600, seen[k].Count)
            seen[k] |> Seq.iteri (fun i text -> Assert.StartsWith($"\"{i}:", text))
        hub, slow
    // Without a total, nobody is cut: each group is within its own budget, and together they hold about 11 MB.
    let unbounded, slowU = run Int64.MaxValue
    Assert.Equal(0L, unbounded.CutCount)
    Assert.True(unbounded.RetainedBytes > 10L * 1024L * 1024L, $"{unbounded.RetainedBytes}")
    ignore slowU
    // With a 2 MB total, the slow ones are cut until the hub holds about that (plus the groups' newest chunks of 8 frames).
    let hub, slow = run (2L * 1024L * 1024L)
    Assert.True(eventually hub (fun () -> hub.RetainedBytes <= 2L * 1024L * 1024L + 20L * 8L * 1100L), $"retained {hub.RetainedBytes}")
    Assert.True(hub.CutCount >= 15L, $"cut {hub.CutCount}")
    let lagged = slow |> List.filter (fun s -> (recv s) = Error RecvStatus.Lagged) |> List.length
    Assert.Equal(int hub.CutCount, lagged)

[<Fact>]
let ``hub budget (verifier): the subscriber furthest behind is cut first, wherever it is`` () =
    let hub = Hub(8, 64L * 1024L * 1024L, false)
    hub.TotalBudget <- 1024L * 1024L
    let old = hub.Subscribe("a", null, Wake())
    let frame = String('q', 1000)
    for i in 0..599 do
        hub.Broadcast("a", $"\"{i}{frame}\"") |> ignore
    let young = hub.Subscribe("b", null, Wake())
    for i in 0..299 do
        hub.Broadcast("b", $"\"{i}{frame}\"") |> ignore
    Assert.Equal(0L, hub.CutCount)
    for i in 300..499 do
        hub.Broadcast("b", $"\"{i}{frame}\"") |> ignore
    Assert.True(eventually hub (fun () -> hub.CutCount = 1L && hub.RetainedBytes <= 1024L * 1024L), $"cut {hub.CutCount}, retained {hub.RetainedBytes}")
    Assert.Equal(Error RecvStatus.Lagged, recv old)
    let got = drainAll young
    Assert.Equal(500, got.Length)
    got |> List.iteri (fun i text -> Assert.StartsWith($"\"{i}q", text))
