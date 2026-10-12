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
        let frame = Frame.OfBytes(ReadOnlySpan(Array.init 10_298 (fun i -> byte (1 + i % 200))))
        let bytes = frame.Bytes
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
        let plain = Frame.OfBytes(ReadOnlySpan(Array.zeroCreate<byte> 100))
        CableVerify.Check(plain, plain.Bytes, "unit test", "none")
        CableVerify.Check(frame, Array.zeroCreate 5, "unit test", "none")
        Assert.Equal<int64>(before + 1L, CableVerify.Failures)
    finally
        CableVerify.Configure false

// --- Unit R5.2: the payloads a gathered write hands the kernel never move -------------------------------------------------------

/// A loopback pair with a detached writer on the server side and a thread reading the client side into whole server frames, each
/// payload compared with the next of `expected` (in order). Returns the writer, a function that waits for every expected payload and
/// returns how many differed, and the sockets to dispose.
let private gatherRig (expected: Collections.Concurrent.BlockingCollection<byte[]>) =
    use listener = new Net.Sockets.TcpListener(Net.IPAddress.Loopback, 0)
    listener.Start()
    let client = new Net.Sockets.Socket(Net.Sockets.SocketType.Stream, Net.Sockets.ProtocolType.Tcp)
    client.Connect(Net.IPAddress.Loopback, (listener.LocalEndpoint :?> Net.IPEndPoint).Port)
    let server = listener.AcceptSocket()
    let writer = Writer(IO.Stream.Null, false, TimeSpan.FromSeconds 30.0, ignore, server)
    writer.Detach()
    let mutable wrong = 0
    let mutable firstWrong = ""
    let reader =
        Task.Factory.StartNew(
            (fun () ->
                let stream = new Net.Sockets.NetworkStream(client, false)
                let header = Array.zeroCreate<byte> 10
                let read (buffer: byte[]) (count: int) = stream.ReadExactly(buffer, 0, count)
                let mutable payload: byte[] = Array.zeroCreate 0
                let mutable index = 0
                for want in expected.GetConsumingEnumerable() do
                    read header 2
                    let length =
                        match int (header[1] &&& 0x7fuy) with
                        | 126 ->
                            read header 2
                            (int header[0] <<< 8) ||| int header[1]
                        | 127 ->
                            read header 8
                            int (Buffers.Binary.BinaryPrimitives.ReadUInt64BigEndian(ReadOnlySpan header))
                        | n -> n
                    if payload.Length < length then payload <- Array.zeroCreate length
                    read payload length
                    if length <> want.Length || not (ReadOnlySpan(payload, 0, length).SequenceEqual(ReadOnlySpan want)) then
                        wrong <- wrong + 1
                        if firstWrong = "" then
                            let zeros = payload |> Seq.take length |> Seq.filter ((=) 0uy) |> Seq.length
                            firstWrong <- $"frame {index}: {length} bytes for {want.Length}, {zeros} of them NUL"
                    index <- index + 1),
            TaskCreationOptions.LongRunning
        )
    let finish () =
        expected.CompleteAdding()
        if not (reader.Wait(TimeSpan.FromSeconds 60.0)) then failwith "the reader did not get every frame in 60 s"
        wrong, firstWrong
    writer, finish, server, client

/// Frames of `size` bytes, each with its own contents, made between short-lived arrays, so that a compacting collection has garbage to
/// close up and anything movable moves.
let private distinctFrames (seed: int) (count: int) (size: int) : Frame[] =
    Array.init count (fun j ->
        Array.zeroCreate<byte> 4096 |> ignore
        let frame = Frame.OfBytes(ReadOnlySpan(Array.init size (fun k -> byte (1 + (seed * 31 + j * 7 + k) % 251))))
        Array.zeroCreate<byte> 4096 |> ignore
        frame.Probe <- Frame.ProbeOf frame.Bytes
        frame)

/// The deterministic form of round 5's finding (`bench/results/oncrack-r5-lost-frame.md`): a full compacting collection runs after the
/// gathered write has put every payload's address in its iovec table and before the `sendmsg`. Round 4's write (payloads on the ordinary
/// heap, pinned by a `fixed` local in a recursion that F# compiled to a loop, so only the last one was pinned) fails it: the verify switch
/// finds 620 of the 640 payloads elsewhere (all but the last of each batch). In this small process the client still reads the right
/// bytes, because nothing has reused the vacated memory yet; in the server, under load, something had, and a client read NULs and other
/// objects' bytes. Now every payload is on the pinned object heap and it passes. Mutation: `Frame.Allocate` with `pinned = false` fails it.
[<Fact>]
let ``a compacting collection just before a gathered write's sendmsg changes nothing the client reads`` () =
    if not GatherAvailable then Assert.Skip "gathered writes are Linux-only (bin/linux-tests Cable)"
    let expected = new Collections.Concurrent.BlockingCollection<byte[]>()
    let writer, finish, server, client = gatherRig expected
    use _ = server
    use _ = client
    CableVerify.Configure true
    SetBeforeSendmsg(fun () -> GC.Collect(2, GCCollectionMode.Forced, true, true))
    let before = CableVerify.Failures
    try
        for batch in 1..20 do
            let frames = distinctFrames batch 32 10_298
            for frame in frames do
                expected.Add frame.Bytes
            // The client reads as fast as it can; a batch the socket does not take whole finishes through the copy of its rest.
            if not ((writer.Send frames).AsTask().Wait(TimeSpan.FromSeconds 30.0)) then failwith "a gathered write did not finish"
    finally
        SetBeforeSendmsg null
        CableVerify.Configure false
    let wrong, first = finish ()
    let moved = CableVerify.Failures - before
    Assert.True(
        (moved = 0L && wrong = 0),
        $"{moved} of 640 payloads were not where the kernel was told when sendmsg returned; {wrong} of 640 frames reached the client with other bytes than the frame's ({first})"
    )

/// Round 5's reproducer, under contention: gathered writes on one thread while another runs compacting gen1 collections (the
/// generation of every move the verify switch reported in the hunt), and a client checking every byte. With `CAMPFIRE_PIN_STRESS=1`
/// (`LINUX_TESTS_ENV=CAMPFIRE_PIN_STRESS=1 bin/linux-tests Cable --filter-method "*contention*"`); bounded at 60 s of writes so that it
/// always reaches a verdict (round 5.1's version, 4,000 writes beside a collector that never paused, ran 22 minutes without one).
[<Fact>]
let ``gathered writes keep their payloads where the kernel was told under contention with compacting collections`` () =
    if not GatherAvailable then Assert.Skip "gathered writes are Linux-only (bin/linux-tests Cable)"
    if Environment.GetEnvironmentVariable "CAMPFIRE_PIN_STRESS" <> "1" then Assert.Skip "gated: CAMPFIRE_PIN_STRESS=1 runs it"
    do
        let expected = new Collections.Concurrent.BlockingCollection<byte[]>()
        let writer, finish, server, client = gatherRig expected
        use _ = server
        use _ = client
        CableVerify.Configure true
        let stop = ref false
        let mutable collections = 0
        let collector =
            Threading.Thread(
                (fun () ->
                    while not stop.Value do
                        GC.Collect(1, GCCollectionMode.Forced, true, true)
                        collections <- collections + 1
                        Threading.Thread.Sleep 1),
                IsBackground = true
            )
        let before = CableVerify.Failures
        let clock = Diagnostics.Stopwatch.StartNew()
        let mutable batches = 0
        try
            collector.Start()
            while batches < 1500 && clock.Elapsed < TimeSpan.FromSeconds 60.0 do
                batches <- batches + 1
                let frames = distinctFrames batches 32 10_298
                for frame in frames do
                    expected.Add frame.Bytes
                if not ((writer.Send frames).AsTask().Wait(TimeSpan.FromSeconds 30.0)) then failwith "a gathered write did not finish"
        finally
            stop.Value <- true
            CableVerify.Configure false
        let wrong, first = finish ()
        let moved = CableVerify.Failures - before
        eprintfn "pin stress: %d batches of 32 frames in %.1f s beside %d forced gen1 collections; %d moved, %d frames wrong" batches clock.Elapsed.TotalSeconds collections moved wrong
        Assert.True((moved = 0L), $"{moved} payloads were not where the kernel was told when sendmsg returned ({batches} batches, {collections} collections)")
        Assert.True((wrong = 0), $"{wrong} frames reached the client with other bytes than the frame's ({first})")
