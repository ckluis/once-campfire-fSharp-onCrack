// Round 4 verifier: the posting pressure gate of unit R4.5 (`Broadcasts.AwaitRoom`, called by `MessagesController#create` before it
// writes). A post waits, at most `Config.PressureWait` (2 s), while more than half of its room's subscribers are more than
// `Config.PressureFrames` (2,048) frames behind. These hold it to that: nothing waits when nobody is behind; a waiting post is bounded,
// stops waiting as soon as the subscribers catch up, holds no database connection, no writer and no place in the broadcast line while
// it waits, and is written once and broadcast once, in commit order; and subscribers that are behind because they read slowly (their
// connection waiting on its socket) or under an identifier of their own do not make everyone's posts wait.
module Campfire.App.Tests.CablePressureTests

open System
open System.Diagnostics
open System.Text.RegularExpressions
open System.Threading
open System.Threading.Tasks
open Xunit
open Campfire.App
open Campfire.Cable
open Campfire.Db
open Campfire.App.Tests.Support

let private unwrap (result: Result<'T, DbError>) : 'T =
    match result with
    | Ok value -> value
    | Error e -> failwith (DbError.display e)

let private read (test: Test) (f: Conn -> 'T) : 'T = test.App.Db.ReadBlocking f |> unwrap

let private roomOf (test: Test) (id: int64) = read test (fun conn -> Room.find conn id)

let private streamOf (test: Test) (id: int64) : string =
    Naming.streamNameFrom [ Campfire.RailsCompat.GlobalId.toParam (Campfire.App.Channels.Gid.roomGid (roomOf test id)); "messages" ]

let private postForm (roomId: int64) (body: string) : Req =
    ((request "POST" $"/rooms/{roomId}/messages").With("accept", "text/vnd.turbo-stream.html, text/html, application/xhtml+xml"))
        .Form(formBody [ "message[body]", body ])

let private stored (test: Test) (token: string) : int64 =
    read test (fun conn ->
        conn.QueryRow("SELECT count(*) FROM action_text_rich_texts WHERE body LIKE ?", [| S("%" + token + "%") |], fun r -> r.Int64 0))

/// Every frame `subscriber` has now.
let private drain (subscriber: Subscriber) : string list =
    let seen = Collections.Generic.List<string>()
    let mutable frame = Unchecked.defaultof<Campfire.Cable.Socket.Frame>
    let mutable reading = true
    while reading do
        match subscriber.TryRecv(&frame) with
        | RecvStatus.Got -> seen.Add frame.Text
        | RecvStatus.Lagged -> failwith "lagged"
        | _ -> reading <- false
    List.ofSeq seen

/// Puts every one of `subscribers` more than the gate's 2,048 frames behind, then lets the 10 ms verdict expire.
let private congest (test: Test) (name: string) : unit =
    let filler = Text.Encoding.UTF8.GetBytes "{\"filler\":true}"
    for _ in 1..2100 do
        test.App.Cable.Hub.Broadcast(name, ReadOnlySpan filler) |> ignore
    Thread.Sleep 25

let private seconds (since: int64) = float (Stopwatch.GetTimestamp() - since) / float Stopwatch.Frequency

[<Fact>]
let ``nothing waits when nobody is behind, or nobody listens`` () =
    task {
        use! test = bootSeeded "default"
        let room = roomOf test ALL_TALK
        Assert.True((test.App.Broadcasts.AwaitRoom room).IsCompleted, "no subscribers")
        let name = streamOf test ALL_TALK
        use a = test.App.Cable.Hub.Subscribe(name, null, Wake())
        use b = test.App.Cable.Hub.Subscribe(name, null, Wake())
        Assert.True((test.App.Broadcasts.AwaitRoom room).IsCompleted, "subscribers that are caught up")
        let browser = david test
        let started = Stopwatch.GetTimestamp()
        let! reply = browser.Write(postForm ALL_TALK "gate idle post")
        Assert.Equal(200, reply.Status)
        Assert.True(seconds started < 1.0, $"an uncongested post took {seconds started} s")
        Assert.Equal(1, drain a |> List.filter (fun f -> f.Contains "gate idle post") |> List.length)
        ignore b
    }

[<Fact>]
let ``a post waits while most subscribers are far behind, for at most the limit, and is written and broadcast once`` () =
    task {
        use! test = bootSeeded "default"
        let name = streamOf test ALL_TALK
        let subscribers = [ for _ in 1..3 -> test.App.Cable.Hub.Subscribe(name, null, Wake()) ]
        try
            congest test name
            Assert.True(test.App.Cable.Hub.Congested(name, test.App.Cable.Config.PressureFrames))
            Assert.False((test.App.Broadcasts.AwaitRoom(roomOf test ALL_TALK)).IsCompleted, "the gate is closed")
            let browser = david test
            let started = Stopwatch.GetTimestamp()
            let! reply = browser.Write(postForm ALL_TALK "gate bounded post")
            let took = seconds started
            Assert.Equal(200, reply.Status)
            Assert.Contains("gate bounded post", reply.Text)
            Assert.True(took >= 1.8 && took < 4.0, $"the post waited {took} s, not about 2 s")
            Assert.Equal(1L, stored test "gate bounded post")
            for subscriber in subscribers do
                let frames = drain subscriber
                Assert.Equal(2100, frames |> List.filter (fun f -> f.Contains "filler") |> List.length)
                Assert.Equal(1, frames |> List.filter (fun f -> f.Contains "gate bounded post") |> List.length)
                Assert.Contains("gate bounded post", List.last frames)
        finally
            for subscriber in subscribers do
                (subscriber :> IDisposable).Dispose()
    }

[<Fact>]
let ``a waiting post goes as soon as the subscribers catch up`` () =
    task {
        use! test = bootSeeded "default"
        let name = streamOf test ALL_TALK
        let subscribers = [ for _ in 1..3 -> test.App.Cable.Hub.Subscribe(name, null, Wake()) ]
        try
            congest test name
            let browser = david test
            let started = Stopwatch.GetTimestamp()
            let post = browser.Write(postForm ALL_TALK "gate released post")
            do! Task.Delay 300
            Assert.False(post.IsCompleted, "the post is waiting")
            // Two of three catch up: no longer more than half behind.
            drain subscribers[0] |> ignore
            drain subscribers[1] |> ignore
            let! reply = post
            let took = seconds started
            Assert.Equal(200, reply.Status)
            Assert.True(took < 1.2, $"the post took {took} s after the subscribers caught up at 0.3 s")
            Assert.Equal(1L, stored test "gate released post")
        finally
            for subscriber in subscribers do
                (subscriber :> IDisposable).Dispose()
    }

[<Fact>]
let ``waiting posts hold no connection, writer or place in line, and go out once each in commit order`` () =
    task {
        use! test = bootSeeded "default"
        let name = streamOf test ALL_TALK
        let behind = [ for _ in 1..3 -> test.App.Cable.Hub.Subscribe(name, null, Wake()) ]
        // A subscriber that keeps up is one of four: three of four are behind.
        use watcher = test.App.Cable.Hub.Subscribe(name, null, Wake())
        use quiet = test.App.Cable.Hub.Subscribe(streamOf test QUIET_CORNER, null, Wake())
        try
            congest test name
            drain watcher |> ignore
            Thread.Sleep 25
            Assert.True(test.App.Cable.Hub.Congested(name, test.App.Cable.Config.PressureFrames))
            // More waiting posts than the read pool has connections.
            let posts = [| for i in 1..24 -> task { return! (david test).Write(postForm ALL_TALK $"gate queued {i} post") } |]
            do! Task.Delay 300
            Assert.True(posts |> Array.forall (fun p -> not p.IsCompleted), "the posts are waiting")
            // Meanwhile: a page read, a post into another room (a write, and a broadcast through the line) and a bare write all go through.
            let others = david test
            let started = Stopwatch.GetTimestamp()
            let! page = others.Get $"/rooms/{ALL_TALK}"
            Assert.Equal(200, page.Status)
            let! elsewhere = others.Write(postForm QUIET_CORNER "gate elsewhere post")
            Assert.Equal(200, elsewhere.Status)
            test.App.Db.WriteBlocking(fun _ -> ()) |> unwrap
            Assert.True(seconds started < 1.0, $"reads and writes beside the waiting posts took {seconds started} s")
            Assert.Equal(1, drain quiet |> List.filter (fun f -> f.Contains "gate elsewhere post") |> List.length)
            Assert.True(posts |> Array.forall (fun p -> not p.IsCompleted), "the posts are still waiting")
            let! replies = Task.WhenAll posts
            for reply in replies do
                Assert.Equal(200, reply.Status)
            for i in 1..24 do
                Assert.Equal(1L, stored test $"gate queued {i} post")
            // The watcher saw each once, in the order of their ids (commit order).
            let frames = drain watcher
            let ids =
                frames
                |> List.choose (fun f ->
                    let m = Regex.Match(f, "gate queued \\d+ post")
                    if m.Success then
                        let id = Regex.Match(f, "data-message-id=\\\\\"(\\d+)")
                        Some(int64 id.Groups[1].Value)
                    else
                        None)
            Assert.Equal(24, ids.Length)
            Assert.Equal(24, ids |> List.distinct |> List.length)
            Assert.Equal<int64 list>(List.sort ids, ids)
        finally
            for subscriber in behind do
                (subscriber :> IDisposable).Dispose()
    }

[<Fact>]
let ``a few clients that do not read, or subscribe under identifiers of their own, do not make posts wait`` () =
    task {
        use! test = bootSeeded "default"
        let name = streamOf test ALL_TALK
        let hub = test.App.Cable.Hub
        let shared = "\"{\\\"channel\\\":\\\"Turbo::StreamsChannel\\\",\\\"signed_stream_name\\\":\\\"x\\\"}\""
        let readers = [ for _ in 1..3 -> hub.Subscribe(name, shared, Wake()) ]
        // One client alone in a group of its own (its identifier's keys in another order), never reading.
        use loner = hub.Subscribe(name, "\"{\\\"signed_stream_name\\\":\\\"x\\\",\\\"channel\\\":\\\"Turbo::StreamsChannel\\\"}\"", Wake())
        // Four clients whose connections have waited a second on their sockets: slow readers, more than the three that keep up.
        let stalledWakes = [ for _ in 1..4 -> Wake() ]
        let stalled = [ for wake in stalledWakes -> hub.Subscribe(name, shared, wake) ]
        try
            let since = Stopwatch.GetTimestamp() - Stopwatch.Frequency
            for wake in stalledWakes do
                wake.WriteWaitSince <- since
            congest test name
            for reader in readers do
                drain reader |> ignore
            Thread.Sleep 25
            Assert.False(hub.Congested(name, test.App.Cable.Config.PressureFrames))
            Assert.Equal(2100, (drain loner).Length)
            let started = Stopwatch.GetTimestamp()
            let! reply = (david test).Write(postForm ALL_TALK "gate unaffected post")
            Assert.Equal(200, reply.Status)
            Assert.True(seconds started < 1.0, $"the post took {seconds started} s")
        finally
            for subscriber in readers @ stalled do
                (subscriber :> IDisposable).Dispose()
    }
