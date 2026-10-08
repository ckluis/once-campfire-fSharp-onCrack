// onCrack (unit R2.1): a connection on plain TCP writes to its socket itself once the pong answering its probe arrives
// (`Connection.run`, `Writer.Detach`). These try to break the ordering argument: frames held while the probe is out, a
// client that never answers, one that pings or pongs on its own, TLS, a reader that stops reading (partial sends), the
// switch turned off, and many connections at once.
module Campfire.Cable.Tests.DirectTests

open System
open System.Threading.Tasks
open Xunit
open Campfire.RailsCompat
open Campfire.Cable
open Campfire.Cable.Tests.Support

[<Literal>]
let private Welcome = """{"type":"welcome"}"""

let private str (s: string) = Value.String s
let private int' (n: int) = Value.Int(int64 n)

let private room (id: int) : string =
    identifier (object' [ "channel", str "RoomChannel"; "room_id", int' id ])

let private confirm (identifier: string) : string =
    $"""{{"identifier":{Json.generate (str identifier)},"type":"confirm_subscription"}}"""

let private message (identifier: string) (message: string) : string =
    $"""{{"identifier":{Json.generate (str identifier)},"message":{message}}}"""

let private eq (expected: 'a) (actual: 'a) = Assert.Equal<'a>(expected, actual)

let private withServer (config: Config) (body: TestServer -> Task) : Task =
    task {
        let! app = start config
        try
            do! (body app).WaitAsync(TimeSpan.FromSeconds 60.0)
        finally
            (app :> IAsyncDisposable).DisposeAsync().AsTask().Wait()
    }

let private expectText (expected: string) (client: Client) : Task =
    task {
        let! text = client.NextText()
        eq expected text
    }

/// Broadcasts `count` numbered payloads (with `pad` bytes of padding each) to room 1, then reads them back in order.
let private roundTrip (app: TestServer) (client: Client) (first: int) (count: int) (pad: int) : Task =
    task {
        let body (i: int) = object' [ "n", int' i; "pad", str (String('x', pad)) ]
        for i in first .. first + count - 1 do
            app.Server.Broadcast("room:room-1", body i) |> ignore
        for i in first .. first + count - 1 do
            do! expectText (message (room 1) (Json.generate (body i))) client
    }

[<Fact>]
let ``a plain TCP connection writes to its socket once its probe is answered`` () =
    withServer testConfig (fun app ->
        task {
            use! client = connect app 1UL
            do! expectText Welcome client
            do! client.Subscribe(room 1)
            do! expectText (confirm (room 1)) client
            do! roundTrip app client 0 300 40
            eq 1 client.Pings
            eq 1L app.Server.DirectConnections
        })

[<Fact>]
let ``frames held while the probe is out come after the welcome, in order`` () =
    withServer testConfig (fun app ->
        task {
            use! client = connect app 1UL
            do! expectText Welcome client
            // The probe has not been read (so not answered) yet: the confirmation and every broadcast are held.
            do! client.Subscribe(room 1)
            do! Task.Delay 150
            let body (i: int) = object' [ "n", int' i ]
            for i in 0..49 do
                app.Server.Broadcast("room:room-1", body i) |> ignore
            eq 0L app.Server.DirectConnections
            // Reading the probe answers it; everything held follows in order.
            do! expectText (confirm (room 1)) client
            for i in 0..49 do
                do! expectText (message (room 1) (Json.generate (body i))) client
            eq 1L app.Server.DirectConnections
            do! roundTrip app client 50 100 10
        })

[<Fact>]
let ``a client that never answers is served through the stream, in order`` () =
    withServer testConfig (fun app ->
        task {
            use! client = connect app 1UL
            client.AnswerPings <- false
            do! expectText Welcome client
            do! client.Subscribe(room 1)
            let started = Diagnostics.Stopwatch.StartNew()
            do! expectText (confirm (room 1)) client
            // Held until the probe timed out.
            Assert.True(started.Elapsed > TimeSpan.FromSeconds 1.0, $"confirmed after {started.Elapsed}")
            do! roundTrip app client 0 200 40
            eq 0L app.Server.DirectConnections
        })

[<Fact>]
let ``a pong that does not echo the probe does not detach`` () =
    withServer testConfig (fun app ->
        task {
            use! client = connect app 1UL
            client.AnswerPings <- false
            do! expectText Welcome client
            // Unsolicited pongs (RFC 6455 allows them), one empty, one with a payload of the probe's length.
            do! client.SendBytes(clientFrame 0xAuy true false [||])
            do! client.SendBytes(clientFrame 0xAuy true false (Array.zeroCreate 8))
            do! client.Subscribe(room 1)
            do! expectText (confirm (room 1)) client
            do! roundTrip app client 0 50 10
            eq 0L app.Server.DirectConnections
        })

[<Fact>]
let ``a client ping during the probe is answered and the probe is sent again`` () =
    withServer testConfig (fun app ->
        task {
            use! client = connect app 1UL
            do! expectText Welcome client
            // Ahead of the pong to the first probe: the server's pong goes through the stream after that probe, so the first
            // probe's answer no longer proves the stream is empty, and a second probe follows.
            do! client.SendBytes(clientFrame 0x9uy true false "abc"B)
            do! client.Subscribe(room 1)
            do! expectText (confirm (room 1)) client
            do! roundTrip app client 0 100 10
            eq 2 client.Pings
            eq 1L app.Server.DirectConnections
        })

[<Fact>]
let ``a client's ping is answered on the socket after the switch`` () =
    withServer testConfig (fun app ->
        task {
            use! client = connect app 1UL
            do! expectText Welcome client
            do! client.Subscribe(room 1)
            do! expectText (confirm (room 1)) client
            eq 1L app.Server.DirectConnections
            do! client.SendBytes(clientFrame 0x9uy true false (Text.Encoding.UTF8.GetBytes "hi"))
            let reply = Array.zeroCreate<byte> 4
            use limit = new Threading.CancellationTokenSource(TimeSpan.FromSeconds 5.0)
            let mutable got = 0
            while got < 4 do
                let! n = client.Stream.ReadAsync(Memory<byte>(reply, got, 4 - got), limit.Token)
                got <- got + n
            eq [| 0x8auy; 0x02uy; byte 'h'; byte 'i' |] reply
        })

[<Fact>]
let ``with direct writes off there is no probe`` () =
    withServer { testConfig with DirectWrites = false } (fun app ->
        task {
            use! client = connect app 1UL
            do! expectText Welcome client
            do! client.Subscribe(room 1)
            do! expectText (confirm (room 1)) client
            do! roundTrip app client 0 100 10
            eq 0 client.Pings
            eq 0L app.Server.DirectConnections
        })

[<Fact>]
let ``TLS connections never write to the socket themselves`` () =
    task {
        let log = Log()
        let server =
            Server.builder testConfig cookieAuth identify
            |> ServerBuilder.channel "RoomChannel" (roomChannel log)
            |> ServerBuilder.build
        let! app, address = hostOn server true
        try
            let authority = (Uri address).Authority
            let headers =
                [ "Origin", $"https://{authority}"
                  "Cookie", "session_token=1"
                  "Sec-WebSocket-Protocol", "actioncable-v1-json"
                  "X-Forwarded-Proto", "https" ]
            match! Client.Open(authority, headers, true) with
            | Choice2Of2 response -> failwith $"{response.Status}"
            | Choice1Of2 client ->
                use _ = client
                do! expectText Welcome client
                do! client.Subscribe(room 1)
                do! expectText (confirm (room 1)) client
                let body (i: int) = object' [ "n", int' i; "pad", str (String('y', 3000)) ]
                for i in 0..99 do
                    server.Broadcast("room:room-1", body i) |> ignore
                for i in 0..99 do
                    do! expectText (message (room 1) (Json.generate (body i))) client
                eq 0 client.Pings
                eq 0L server.DirectConnections
        finally
            (server :> IDisposable).Dispose()
            app.DisposeAsync().AsTask().Wait()
    }

[<Fact>]
let ``a reader that stops reading gets every byte in order once it reads again`` () =
    withServer testConfig (fun app ->
        task {
            use! client = connect app 1UL
            do! expectText Welcome client
            do! client.Subscribe(room 1)
            do! expectText (confirm (room 1)) client
            eq 1L app.Server.DirectConnections
            // 200 frames of 40 kB (8 MB, far beyond the socket buffers) while the client reads nothing: the sends stop part way
            // and finish later.
            let body (i: int) = object' [ "n", int' i; "pad", str (String(char (97 + i % 26), 40000)) ]
            for i in 0..199 do
                app.Server.Broadcast("room:room-1", body i) |> ignore
            do! Task.Delay 500
            for i in 0..199 do
                do! expectText (message (room 1) (Json.generate (body i))) client
            do! roundTrip app client 200 20 10
        })

[<Fact>]
let ``many connections, each sees every frame once and in order`` () =
    withServer testConfig (fun app ->
        task {
            let clients = Collections.Generic.List<Client>()
            try
                for i in 1..40 do
                    let! client = connect app (uint64 (1 + i % 2))
                    // Every fourth never answers its probe: those stay on the stream, beside the rest.
                    if i % 4 = 0 then client.AnswerPings <- false
                    clients.Add client
                for client in clients do
                    do! expectText Welcome client
                    do! client.Subscribe(room 1)
                // Read at once: a client that doesn't answer holds its own confirmation for the probe's timeout, which would
                // otherwise let the later clients' probes time out too.
                let! _ = Task.WhenAll [| for client in clients -> expectText (confirm (room 1)) client |]
                let body (i: int) = object' [ "n", int' i; "pad", str (String('z', i % 700)) ]
                let publisher =
                    Task.Run(fun () ->
                        for i in 0..199 do
                            app.Server.Broadcast("room:room-1", body i) |> ignore
                            if i % 20 = 0 then Threading.Thread.Sleep 1)
                let readers =
                    [| for client in clients ->
                           task {
                               for i in 0..199 do
                                   do! expectText (message (room 1) (Json.generate (body i))) client
                           } |]
                do! publisher
                let! _ = Task.WhenAll readers
                eq 30L app.Server.DirectConnections
            finally
                for client in clients do
                    (client :> IDisposable).Dispose()
        })
