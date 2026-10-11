// Unit R5.1: the evidence switch (`CAMPFIRE_CABLE_TRACE`, src/Campfire.Cable/Trace.fs). Off, a connection has no trace; on, the file
// names the frames a connection was handed to its writes, as runs of the group's publish numbers, and its chunk crossings.
module Campfire.Cable.Tests.TraceTests

open System
open System.IO
open System.Text.Json
open System.Threading.Tasks
open Xunit
open Campfire.RailsCompat
open Campfire.Cable
open Campfire.Cable.Socket
open Campfire.Cable.Tests.Support

let private room1 = identifier (object' [ "channel", Value.String "RoomChannel"; "room_id", Value.Int 1L ])

let private lines (file: string) : JsonElement list =
    if not (File.Exists file) then
        []
    else
        use stream = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.ReadWrite)
        use reader = new StreamReader(stream)
        [ for line in reader.ReadToEnd().Split('\n', StringSplitOptions.RemoveEmptyEntries) do
              yield JsonDocument.Parse(line).RootElement.Clone() ]

[<Fact>]
let ``off, a connection has no trace; on, the file names every frame it was handed`` () =
    task {
        CableTrace.Configure null
        Assert.True(isNull (ConnTraceFactory.openConnection "127.0.0.1:1"))
        let file = Path.Combine(Path.GetTempPath(), $"cable-trace-{Guid.NewGuid():N}.jsonl")
        CableTrace.Configure file
        try
            let first = 900_000L
            let count = 300
            let! app = start testConfig
            let session =
                task {
                    use! client = connect app 1UL
                    let! _welcome = client.NextText()
                    do! client.Subscribe room1
                    let! _confirm = client.NextText()
                    for i in 0 .. count - 1 do
                        app.Server.Broadcast("room:room-1", object' [ "text", Value.String $"fanout bmk{first + int64 i}z" ]) |> ignore
                    for _ in 0 .. count - 1 do
                        let! _ = client.NextText()
                        ()
                }
            do! session
            // The connection ends when the client goes away; its line is written then. Other tests in the process publish too (the fan-out
            // tests, a hundred thousand records), so drain until this test's own are in the file.
            let kind (e: JsonElement) = string (e.GetProperty("t").GetString())
            let isConnection (e: JsonElement) = kind e = "C"
            let isMine (e: JsonElement) =
                kind e = "P" && e.GetProperty("m").GetInt64() >= first && e.GetProperty("m").GetInt64() < first + int64 count
            do! (app :> IAsyncDisposable).DisposeAsync().AsTask()
            let mutable all = lines file
            let until = DateTime.UtcNow.AddSeconds 30.0
            while (List.filter isMine all |> List.length) < count && DateTime.UtcNow < until do
                CableTrace.Drain()
                do! Task.Delay 20
                all <- lines file
            let until = DateTime.UtcNow.AddSeconds 15.0
            while not (all |> List.exists (fun e -> isConnection e && (string (e.GetProperty("remote").GetString())).StartsWith "127.0.0.1:")) && DateTime.UtcNow < until do
                do! Task.Delay 50
                all <- lines file
            let published = all |> List.filter isMine
            Assert.Equal(count, published.Length)
            let group = published.Head.GetProperty("g").GetInt32()
            Assert.All(published, fun e -> Assert.Equal(group, e.GetProperty("g").GetInt32()))
            // Markers come out in the order they were published, one publish number each.
            let seqs = published |> List.map (fun e -> e.GetProperty("s").GetInt64())
            Assert.Equal<int64 list>(List.sort seqs, seqs)
            Assert.Equal(count, List.distinct seqs |> List.length)
            let conn =
                all
                |> List.filter isConnection
                |> List.filter (fun e -> [ for s in e.GetProperty("subs").EnumerateArray() -> s.GetProperty("g").GetInt32() ] |> List.contains group)
                |> List.exactlyOne
            // Every published frame is in one of the connection's runs, once.
            let handed = Collections.Generic.HashSet<int64>()
            for run in conn.GetProperty("runs").EnumerateArray() do
                let start, n = run[0].GetInt64(), run[1].GetInt32()
                for k in 0L .. int64 n - 1L do
                    Assert.True(handed.Add(start + k), $"publish number {start + k} handed twice")
            for s in seqs do
                Assert.True(handed.Contains s, $"publish number {s} was never handed to a write")
            Assert.Equal(0, conn.GetProperty("non_monotone").GetInt32())
            Assert.Equal(conn.GetProperty("frames_called").GetInt64(), conn.GetProperty("frames_done").GetInt64())
            Assert.True(conn.GetProperty("frames_called").GetInt64() >= int64 count)
            // 300 frames in a log of 256-frame chunks: the cursor crossed into a second chunk, and the connection went direct.
            let events = [ for e in conn.GetProperty("events").EnumerateArray() -> string (e[1].GetString()) ]
            Assert.Contains("cross", events)
            Assert.Contains("detached", events)
            Assert.Equal("end", List.last events)
            // The welcome and the confirmation have no publish number; the client's ping is answered with a pong.
            Assert.True(conn.GetProperty("seqless_frames").GetInt64() >= 2L)
            Assert.True(conn.GetProperty("ctl").GetProperty("ping").GetInt64() >= 1L)
        finally
            CableTrace.Configure null
            try
                File.Delete file
            with _ ->
                ()
    }

[<Fact>]
let ``the verify switch notices a published array that was zeroed before a send`` () =
    CableVerify.Configure true
    try
        let bytes = Array.init 10_298 (fun i -> byte (1 + i % 200))
        let frame = Frame bytes
        CableVerify.Stamp frame
        Assert.NotEqual(0UL, frame.Probe)
        let before = CableVerify.Failures
        CableVerify.Check(frame, bytes, "unit test", "none")
        Assert.Equal<int64>(before, CableVerify.Failures)
        // The whole array reads as zeros, as the client of round 5's miss saw it: the probe of a zeroed array differs from any text's.
        Array.Clear bytes
        CableVerify.Check(frame, bytes, "unit test", "none")
        Assert.Equal<int64>(before + 1L, CableVerify.Failures)
        // A frame that was not stamped, and a deflated payload, are not checked.
        let plain = Frame(Array.zeroCreate 100)
        CableVerify.Check(plain, plain.Bytes, "unit test", "none")
        CableVerify.Check(frame, Array.zeroCreate 5, "unit test", "none")
        Assert.Equal<int64>(before + 1L, CableVerify.Failures)
    finally
        CableVerify.Configure false
