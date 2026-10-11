// Unit R5.1: an evidence switch for the Cable server, off unless CAMPFIRE_CABLE_TRACE=PATH is set. It changes nothing else.
//
// Round 4's final cable suite saw one message (of 34,741 acknowledged posts, 500 clients, rep 1) that the load generator never
// counted for every client. Was it the server dropping a frame, or the generator missing one? With the switch on the server
// appends JSON lines to PATH:
//
//   {"t":"G",...}  a subscriber group made: its id, broadcasting name and channel identifier;
//   {"t":"P",...}  a frame published to a group: the hub-wide publish number (`s`), the group (`g`), the frame's place in the
//                  group's log (`o`), its length, the load generator's marker number in it if it has one (`m`), the time;
//   {"t":"C",...}  one connection, written when it ends: the groups it subscribed to, every frame it handed to a socket write as
//                  runs of consecutive publish numbers, the number of frames, bytes, writes, partial writes, control frames,
//                  the last writes, and its events (chunk crossings, cuts, revocations, lag, probe and detach, aborts, close).
//
// bench/cable/trace-report reads them with the load generator's dumps (loadgen cable --trace-dir) and says, for a message a client
// lacks, whether the server published it, whether that client's cursor took it, and whether it was handed to a write.
//
// Cost: a publish scans its frame once for the marker and queues one record; a connection counts what it sends; nothing is written
// until the connection ends, except the publish records, which a timer appends every 200 ms. Without the variable there is one
// null test per frame read.
namespace Campfire.Cable

open System
open System.Buffers
open System.Collections.Concurrent
open System.Collections.Generic
open System.IO
open System.Text
open System.Text.Json
open System.Threading

[<Struct>]
type internal TraceEvent =
    { Ms: int64
      Code: string
      A: int64
      B: int64 }

[<Struct>]
type internal JournalEntry =
    { /// 0: a frame published; 1: a group made (`Name`, `Identifier`).
      Kind: byte
      Name: string | null
      Identifier: string | null
      Seq: int64
      Group: int
      Ordinal: int64
      Length: int
      Marker: int64
      Ms: int64 }

/// The trace file and the publish journal. Nothing here may break the server: a trace that cannot be written turns itself off.
[<AbstractClass; Sealed>]
type internal CableTrace private () =
    static let mutable path: string | null =
        match Environment.GetEnvironmentVariable "CAMPFIRE_CABLE_TRACE" with
        | null
        | "" -> null
        | p -> p

    static let journal = ConcurrentQueue<JournalEntry>()
    static let fileGate = obj ()
    static let mutable stream: FileStream | null = null
    static let mutable timer: Timer | null = null
    static let mutable connections = 0L
    static let mutable groups = 0
    static let mutable ringSeq = 0L
    static let marker = "bmk"B

    /// Whether the switch is on.
    static member Enabled = not (isNull path)

    /// For tests: turns the switch on for `file` (or off with null), closing the file the last one wrote.
    static member Configure(file: string | null) : unit =
        lock fileGate (fun () ->
            (match timer with
             | null -> ()
             | t -> t.Dispose())
            timer <- null
            (match stream with
             | null -> ()
             | s -> s.Dispose())
            stream <- null
            journal.Clear()
            path <- file)

    static member NextGroupId() : int = Interlocked.Increment(&groups)

    static member NextConnection() : int64 = Interlocked.Increment(&connections)

    /// A publish number for a ring group's frame (a log's frames take the hub's).
    static member RingSeq() : int64 = Interlocked.Increment(&ringSeq)

    /// The open file, opened on first use; null when the switch is off or the file cannot be opened (which turns it off).
    static member private Open() : FileStream | null =
        match stream with
        | null ->
            lock fileGate (fun () ->
                match stream, path with
                | null, null -> ()
                | null, file ->
                    try
                        let s = new FileStream(nonNull file, FileMode.Append, FileAccess.Write, FileShare.ReadWrite)
                        stream <- s
                        timer <- new Timer((fun _ -> CableTrace.Drain()), null, 200, 200)
                    with e ->
                        eprintfn "WARN campfire: CAMPFIRE_CABLE_TRACE could not open %s: %s" (string file) e.Message
                        path <- null
                | _ -> ()
                stream)
        | s -> s

    /// Appends one JSON line (written by `write`) to the file.
    static member private Line(s: FileStream, write: Utf8JsonWriter -> unit) : unit =
        try
            lock fileGate (fun () ->
                let buffer = ArrayBufferWriter<byte>()
                use w = new Utf8JsonWriter(buffer)
                write w
                w.Flush()
                s.Write(buffer.WrittenSpan)
                s.WriteByte 10uy
                s.Flush())
        with _ ->
            ()

    /// Appends the journal's records to the file.
    static member Drain() : unit =
        if not journal.IsEmpty then
            try
                lock fileGate (fun () ->
                    match stream with
                    | null -> ()
                    | s ->
                        let sb = StringBuilder()
                        let mutable entry = Unchecked.defaultof<JournalEntry>
                        let mutable n = 0
                        while n < 5000 && journal.TryDequeue(&entry) do
                            n <- n + 1
                            if entry.Kind = 0uy then
                                sb.Append("{\"t\":\"P\",\"s\":").Append(entry.Seq).Append(",\"g\":").Append(entry.Group)
                                  .Append(",\"o\":").Append(entry.Ordinal).Append(",\"n\":").Append(entry.Length)
                                  .Append(",\"m\":").Append(entry.Marker).Append(",\"ms\":").Append(entry.Ms).Append("}\n")
                                |> ignore
                            else
                                let buffer = ArrayBufferWriter<byte>()
                                use w = new Utf8JsonWriter(buffer)
                                w.WriteStartObject()
                                w.WriteString("t", "G")
                                w.WriteNumber("g", entry.Group)
                                w.WriteString("name", entry.Name)
                                w.WriteString("identifier", entry.Identifier)
                                w.WriteNumber("ms", entry.Ms)
                                w.WriteEndObject()
                                w.Flush()
                                sb.Append(Encoding.UTF8.GetString(buffer.WrittenSpan)).Append('\n') |> ignore
                        let bytes = Encoding.UTF8.GetBytes(sb.ToString())
                        s.Write(bytes, 0, bytes.Length)
                        s.Flush())
            with _ ->
                ()

    /// A group was made.
    static member GroupCreated(id: int, broadcasting: string, identifier: string | null) : unit =
        if not (isNull (CableTrace.Open())) then
            journal.Enqueue
                { Kind = 1uy
                  Name = broadcasting
                  Identifier = identifier
                  Seq = 0L
                  Group = id
                  Ordinal = 0L
                  Length = 0
                  Marker = 0L
                  Ms = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() }

    /// The load generator's marker, `bmk<digits>z`, in a frame (its first complete one), or -1.
    static member private MarkerIn(bytes: byte[]) : int64 =
        let span = ReadOnlySpan<byte>(bytes)
        let mutable m = -1L
        let mutable from = 0
        while m < 0L && from < span.Length do
            let at = span.Slice(from).IndexOf(ReadOnlySpan<byte> marker)
            if at < 0 then
                from <- span.Length
            else
                let mutable i = from + at + 3
                let mutable v = 0L
                let mutable digits = 0
                while i < span.Length && span[i] >= byte '0' && span[i] <= byte '9' && digits < 18 do
                    v <- v * 10L + int64 (span[i] - byte '0')
                    digits <- digits + 1
                    i <- i + 1
                if digits > 0 && i < span.Length && span[i] = byte 'z' then m <- v
                from <- from + at + 3
        m

    /// A frame was published to a group (under the group's lock): `bytes` is its payload.
    static member Published(group: int, ordinal: int64, seq: int64, bytes: byte[]) : unit =
        if not (isNull (CableTrace.Open())) then
            journal.Enqueue
                { Kind = 0uy
                  Name = null
                  Identifier = null
                  Seq = seq
                  Group = group
                  Ordinal = ordinal
                  Length = bytes.Length
                  Marker = CableTrace.MarkerIn bytes
                  Ms = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() }

    /// Appends one connection's line (the journal first, so that the file reads in order).
    static member WriteConnection(write: Utf8JsonWriter -> unit) : unit =
        match CableTrace.Open() with
        | null -> ()
        | s ->
            CableTrace.Drain()
            CableTrace.Line(s, write)

/// One connection's counters and events. The connection's own task calls everything but `Event`, which any thread may.
[<Sealed>]
type internal ConnTrace(id: int64, remote: string) =
    let gate = obj ()
    let opened = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
    let subs = List<struct (int * string * int64)>()
    let events = List<TraceEvent>()
    let mutable eventsDropped = 0
    // Frames handed to writes, as runs of consecutive publish numbers: (first, count). A frame without one (a welcome, a
    // confirmation, the heartbeat) is only counted.
    let runs = List<struct (int64 * int)>()
    let mutable runFirst = 0L
    let mutable runCount = 0
    let mutable lastSeq = 0L
    let mutable nonMonotone = 0
    let mutable framesCalled = 0L
    let mutable framesDone = 0L
    let mutable seqless = 0L
    let mutable dataBytes = 0L
    let mutable writes = 0L
    let mutable writesPending = 0L
    let mutable writesPartial = 0L
    let mutable gatherCalls = 0L
    let mutable copyCalls = 0L
    let mutable ctlPing = 0L
    let mutable ctlPong = 0L
    let mutable ctlClose = 0L
    let mutable ctlOther = 0L
    let mutable crossings = 0L
    // The last writes: time, frames, first and last publish number, flags (1: detached, 2: not complete at once, 4: partial).
    let lastWrites: struct (int64 * int * int64 * int64 * int)[] = Array.zeroCreate 32
    let mutable batchFrames = 0
    let mutable batchFirst = 0L
    let mutable batchLast = 0L
    let mutable batchFlags = 0
    let mutable batchSlot = 0
    let mutable closed = 0

    static let MaxEvents = 4096
    static let MaxRuns = 20000

    static let now () = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()

    member _.Id = id
    member _.Remote = remote

    member private _.FlushRun() : unit =
        if runCount > 0 && runs.Count < MaxRuns then runs.Add(struct (runFirst, runCount))
        runCount <- 0

    /// The connection subscribed to a group (its log starts at `start`).
    member _.Subscribed(group: int, name: string, start: int64) : unit =
        lock gate (fun () -> subs.Add(struct (group, name, start)))

    member this.Event(code: string, a: int64, b: int64) : unit =
        lock gate (fun () ->
            if events.Count < MaxEvents then events.Add { Ms = now (); Code = code; A = a; B = b } else eventsDropped <- eventsDropped + 1)

    /// The cursor moved on into chunk `chunk` of `group`'s log.
    member this.Cross(group: int, chunk: int64) : unit =
        Interlocked.Increment(&crossings) |> ignore
        this.Event("cross", int64 group, chunk)

    /// A write is about to be made (`Writer.Send`): its frames follow, one `Frame` each.
    member _.BeginBatch(detached: bool) : unit =
        batchFrames <- 0
        batchFirst <- 0L
        batchLast <- 0L
        batchFlags <- (if detached then 1 else 0)

    member _.Frame(seq: int64, payloadLength: int) : unit =
        batchFrames <- batchFrames + 1
        framesCalled <- framesCalled + 1L
        dataBytes <- dataBytes + int64 payloadLength + (if payloadLength < 126 then 2L elif payloadLength < 65536 then 4L else 10L)
        if seq <= 0L then
            seqless <- seqless + 1L
        else
            if batchFirst = 0L then batchFirst <- seq
            batchLast <- seq
            if runCount > 0 && seq = lastSeq + 1L then
                runCount <- runCount + 1
            else
                if runCount > 0 && seq <= lastSeq then nonMonotone <- nonMonotone + 1
                if runCount > 0 && runs.Count < MaxRuns then runs.Add(struct (runFirst, runCount))
                runFirst <- seq
                runCount <- 1
            lastSeq <- seq

    member _.EndBatch() : unit =
        writes <- writes + 1L
        batchSlot <- int (writes % 32L)
        lastWrites[batchSlot] <- struct (now (), batchFrames, batchFirst, batchLast, batchFlags)

    member _.Gather() : unit = gatherCalls <- gatherCalls + 1L
    member _.Copy() : unit = copyCalls <- copyCalls + 1L

    /// The last write was not complete at once (the socket's buffer was full or it went through the stream).
    member _.WriteIssued(completedAtOnce: bool) : unit =
        if not completedAtOnce then
            writesPending <- writesPending + 1L
            let struct (ms, frames, first, last, flags) = lastWrites[batchSlot]
            lastWrites[batchSlot] <- struct (ms, frames, first, last, flags ||| 2)

    /// `sendmsg` took `sent` of `total` bytes.
    member this.Partial(sent: int, total: int) : unit =
        writesPartial <- writesPartial + 1L
        let struct (ms, frames, first, last, flags) = lastWrites[batchSlot]
        lastWrites[batchSlot] <- struct (ms, frames, first, last, flags ||| 4)
        this.Event("partial", int64 sent, int64 total)

    /// The awaited write returned (its `frames` are on the socket's way).
    member _.WriteDone(frames: int) : unit = framesDone <- framesDone + int64 frames

    member _.Control(opcode: byte, _length: int) : unit =
        match opcode with
        | 0x9uy -> ctlPing <- ctlPing + 1L
        | 0xAuy -> ctlPong <- ctlPong + 1L
        | 0x8uy -> ctlClose <- ctlClose + 1L
        | _ -> ctlOther <- ctlOther + 1L

    /// Appends this connection's line to the trace file; once.
    member this.Finish(reason: string) : unit =
        if Interlocked.Exchange(&closed, 1) = 0 then
            this.Event("end", 0L, 0L)
            this.FlushRun()
            CableTrace.WriteConnection(
                fun (w: Utf8JsonWriter) ->
                    w.WriteStartObject()
                    w.WriteString("t", "C")
                    w.WriteNumber("id", id)
                    w.WriteString("remote", remote)
                    w.WriteNumber("opened_ms", opened)
                    w.WriteNumber("closed_ms", now ())
                    w.WriteString("reason", reason)
                    lock gate (fun () ->
                        w.WriteStartArray "subs"
                        for struct (group, name, start) in subs do
                            w.WriteStartObject()
                            w.WriteNumber("g", group)
                            w.WriteString("name", name)
                            w.WriteNumber("start", start)
                            w.WriteEndObject()
                        w.WriteEndArray()
                        w.WriteNumber("frames_called", framesCalled)
                        w.WriteNumber("frames_done", framesDone)
                        w.WriteNumber("seqless_frames", seqless)
                        w.WriteNumber("data_bytes", dataBytes)
                        w.WriteStartObject "ctl"
                        w.WriteNumber("ping", ctlPing)
                        w.WriteNumber("pong", ctlPong)
                        w.WriteNumber("close", ctlClose)
                        w.WriteNumber("other", ctlOther)
                        w.WriteEndObject()
                        w.WriteStartObject "writes"
                        w.WriteNumber("n", writes)
                        w.WriteNumber("pending", writesPending)
                        w.WriteNumber("partial", writesPartial)
                        w.WriteNumber("gather", gatherCalls)
                        w.WriteNumber("copy", copyCalls)
                        w.WriteEndObject()
                        w.WriteNumber("crossings", crossings)
                        w.WriteNumber("non_monotone", nonMonotone)
                        w.WriteBoolean("runs_truncated", runs.Count >= MaxRuns)
                        w.WriteStartArray "runs"
                        for struct (first, count) in runs do
                            w.WriteStartArray()
                            w.WriteNumberValue first
                            w.WriteNumberValue count
                            w.WriteEndArray()
                        w.WriteEndArray()
                        w.WriteStartArray "last_writes"
                        let count = int (min writes 32L)
                        for i in 0 .. count - 1 do
                            let slot = int ((writes - int64 count + 1L + int64 i) % 32L)
                            let struct (ms, frames, first, last, flags) = lastWrites[slot]
                            w.WriteStartObject()
                            w.WriteNumber("ms", ms)
                            w.WriteNumber("frames", frames)
                            w.WriteNumber("first", first)
                            w.WriteNumber("last", last)
                            w.WriteNumber("flags", flags)
                            w.WriteEndObject()
                        w.WriteEndArray()
                        w.WriteStartArray "events"
                        for e in events do
                            w.WriteStartArray()
                            w.WriteNumberValue e.Ms
                            w.WriteStringValue e.Code
                            w.WriteNumberValue e.A
                            w.WriteNumberValue e.B
                            w.WriteEndArray()
                        w.WriteEndArray()
                        w.WriteNumber("events_dropped", eventsDropped))
                    w.WriteEndObject()
            )


/// Starting a connection's trace.
module internal ConnTraceFactory =
    /// A connection began; null when the switch is off. `remote` is the client's address (its port is the load generator's local port).
    let openConnection (remote: string) : ConnTrace | null =
        if CableTrace.Enabled then ConnTrace(CableTrace.NextConnection(), remote) else null
