// Port of the tests in rust/crates/cable/src/pubsub.rs
module Campfire.Cable.Tests.PubsubTests

open System
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

[<Fact>]
let ``slow subscribers see lag instead of gaps`` () =
    let hub = Hub(2)
    let slow = hub.Subscribe("room", null, Wake())
    for i in 0..4 do
        hub.Broadcast("room", string i) |> ignore
    Assert.Equal(Error RecvStatus.Lagged, recv slow)

[<Fact>]
let ``a subscriber that keeps up never lags, and one that fell behind reads on from the oldest kept`` () =
    let hub = Hub(4)
    let steady = hub.Subscribe("room", null, Wake())
    let slow = hub.Subscribe("room", null, Wake())
    for i in 0..99 do
        hub.Broadcast("room", string i) |> ignore
        Assert.Equal(Ok(string i), recv steady)
    Assert.Equal(Error RecvStatus.Lagged, recv slow)
    // As tokio's receiver does after `Lagged`: the oldest message still in the ring comes next.
    Assert.Equal(Ok "96", recv slow)

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
