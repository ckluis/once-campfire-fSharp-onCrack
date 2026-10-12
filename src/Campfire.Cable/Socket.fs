// Port of rust/crates/cable/src/socket.rs
//
// The server side of a WebSocket (RFC 6455) for Action Cable connections, with per-message
// compression (RFC 7692, `permessage-deflate`) when the browser offers it, as browsers do.
//
// Written for fan-out to many sockets. A broadcast reaches every subscriber as the same `Frame`,
// whose payload is shared rather than copied: each socket's write is a few header bytes plus the
// shared payload in one buffer, and nothing is kept per socket once it's written (a general-purpose
// WebSocket copies each frame into a per-socket buffer that then keeps its size). Compression is
// negotiated without context takeover, so every message is compressed on its own, and a broadcast is
// compressed once for all of its subscribers. ASP.NET Core's `WebSocket` compresses per socket, so
// this takes the upgraded stream (`IHttpUpgradeFeature`) and frames it itself, as Rust does with
// the upgraded hyper connection.
//
// Only what Action Cable needs from a client is supported: text messages, fragmented or not,
// compressed or not, and control frames. Protocol errors close the connection, with the code Action
// Cable's websocket-driver would close it with.
module Campfire.Cable.Socket

open System
open System.Buffers
open System.Collections.Generic
open System.IO
open System.IO.Compression
open System.Numerics
open System.Security.Cryptography
open System.Text
open System.Threading
open System.Threading.Tasks
open Microsoft.AspNetCore.Http

/// The largest message a client may send (Action Cable commands are a few hundred bytes), where
/// websocket-driver takes up to 64 MiB (`WebSocket::Driver::MAX_LENGTH`).
[<Literal>]
let MaxMessage = 1048576

/// Smaller frames go out uncompressed even when compression is on: not worth a deflate stream.
[<Literal>]
let internal MinCompressed = 256

/// The extension response: every message compressed on its own, in both directions.
[<Literal>]
let internal DeflateResponse = "permessage-deflate; server_no_context_takeover; client_no_context_takeover"

/// RFC 6455's key suffix.
[<Literal>]
let private AcceptGuid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

/// A sync-flushed deflate stream ends with these; RFC 7692 leaves them off the wire.
let private deflateTail = [| 0uy; 0uy; 0xffuy; 0xffuy |]

[<Literal>]
let private OpContinuation = 0x0uy

[<Literal>]
let private OpText = 0x1uy

[<Literal>]
let private OpBinary = 0x2uy

[<Literal>]
let private OpClose = 0x8uy

[<Literal>]
let private OpPing = 0x9uy

[<Literal>]
let private OpPong = 0xAuy

// websocket-driver's codes for what a client can get wrong (`WebSocket::Driver::Hybi::ERRORS`).

/// Anything not covered below.
[<Literal>]
let ProtocolError = 1002us

/// An unmasked frame.
[<Literal>]
let Unacceptable = 1003us

/// A text message that isn't UTF-8.
[<Literal>]
let EncodingError = 1007us

/// A message over `MaxMessage`.
[<Literal>]
let TooLarge = 1009us

/// The client broke the protocol; the connection closes with `code`.
exception internal ProtocolFailure of code: uint16

// --- Frames ------------------------------------------------------------------------------------

/// Raw deflate at level 6, sync-flushed, without the trailing empty block's 4 bytes.
let internal deflate (input: ReadOnlySpan<byte>) : byte[] =
    use output = new MemoryStream(input.Length / 3 + 64)
    use stream = new DeflateStream(output, CompressionLevel.Optimal, true)
    stream.Write input
    stream.Flush()
    // Disposing the stream would append a final block; what was flushed is the message.
    let mutable length = int output.Length
    let buffer = output.GetBuffer()
    if length >= 4 && buffer.AsSpan(length - 4, 4).SequenceEqual(ReadOnlySpan deflateTail) then length <- length - 4
    buffer.AsSpan(0, length).ToArray()

/// A text frame's payload, shared by every connection that sends it and compressed at most once.
///
/// Unit R5.2: the constructor is private; a frame is made only by the factories below, which fill every byte of its array before the
/// frame exists (and so before anyone can publish it). A gathered write (`Writer.Send`, R4.2) hands the kernel the array's address, pinned
/// for the call by `Sendmsg.pinFrom` (`bench/results/oncrack-r5-lost-frame.md`: round 4's pin held only a batch's last payload).
[<Sealed>]
type Frame private (bytes: byte[]) =
    let mutable deflated: byte[] | null = null

    /// Unit R5.1: the hub-wide publish number of a published frame (0: not published, as a welcome or the heartbeat is not), for
    /// `CAMPFIRE_CABLE_TRACE`. Set once, under the group's lock, before any subscriber can read the frame.
    member val Seq = 0L with get, set

    /// Unit R5.1 (`CAMPFIRE_CABLE_VERIFY`): a probe of the payload taken when the frame is published (0: not taken), so that each send can
    /// check that the array still holds the bytes it was made with. Never 0 once taken.
    member val Probe = 0UL with get, set

    /// Four words of the array (its start, quarter, middle and end) mixed, with the low bit set: a zeroed array gives 1.
    static member ProbeOf(bytes: byte[]) : uint64 =
        if bytes.Length < 32 then
            1UL ||| (uint64 bytes.Length <<< 1)
        else
            let word (at: int) = System.Runtime.CompilerServices.Unsafe.ReadUnaligned<uint64>(&bytes[at])
            let rotl (v: uint64) (n: int) = (v <<< n) ||| (v >>> (64 - n))
            1UL ||| (word 0 ^^^ rotl (word (bytes.Length / 4)) 13 ^^^ rotl (word (bytes.Length / 2)) 29 ^^^ rotl (word (bytes.Length - 8)) 41)

    /// The text, as UTF-8.
    member _.Bytes: byte[] = bytes

    member _.Text: string = Encoding.UTF8.GetString bytes

    /// The payload for a socket with compression on: the deflated bytes when compressing is worth
    /// it, null when it isn't. Compressed on first use, once, whichever connection asks first.
    member this.Deflated: byte[] | null =
        if bytes.Length < MinCompressed then
            null
        else
            match Volatile.Read(&deflated) with
            | null ->
                lock this (fun () ->
                    match deflated with
                    | null -> Volatile.Write(&deflated, deflate (ReadOnlySpan bytes))
                    | _ -> ()
                    deflated)
            | ready -> ready

    /// An array of `length` bytes, its contents undefined: whoever takes it writes every byte.
    static member private Allocate(length: int) : byte[] = GC.AllocateUninitializedArray<byte>(length)

    static member OfString(text: string) : Frame =
        let bytes = Frame.Allocate(Encoding.UTF8.GetByteCount text)
        Encoding.UTF8.GetBytes(text, 0, text.Length, bytes, 0) |> ignore
        Frame bytes

    /// A frame of a copy of `payload`.
    static member OfBytes(payload: ReadOnlySpan<byte>) : Frame =
        let bytes = Frame.Allocate payload.Length
        payload.CopyTo(Span bytes)
        Frame bytes

    /// A frame of `prefix`, `payload` and `suffix` one after the other (a group's message: the identifier's wrapping around the payload).
    static member Concat(prefix: ReadOnlySpan<byte>, payload: ReadOnlySpan<byte>, suffix: ReadOnlySpan<byte>) : Frame =
        let bytes = Frame.Allocate(prefix.Length + payload.Length + suffix.Length)
        prefix.CopyTo(Span bytes)
        payload.CopyTo(Span(bytes, prefix.Length, payload.Length))
        suffix.CopyTo(Span(bytes, prefix.Length + payload.Length, suffix.Length))
        Frame bytes

    override this.ToString() = $"Frame({this.Text})"

#nowarn "9" // `CableVerify.CheckAddress` reads an array's address

/// Unit R5.1: `CAMPFIRE_CABLE_VERIFY=1` makes each published frame take a probe of its array (`Frame.Probe`) and each send check it,
/// before and after the `sendmsg` that reads the array, and say on stderr when it no longer matches: whether the array was already
/// wrong when this connection came to send it, or changed during the call, or (no message, and a client that still lacks the bytes) was
/// right throughout. Three or four loads a frame; off, one test of a static.
[<AbstractClass; Sealed>]
type internal CableVerify private () =
    static let mutable enabled =
        match Environment.GetEnvironmentVariable "CAMPFIRE_CABLE_VERIFY" with
        | null
        | ""
        | "0"
        | "off" -> false
        | _ -> true

    static let mutable failures = 0L
    static let mutable checks = 0L
    static let mutable lastReport = 0L

    static member Enabled = enabled

    /// For tests.
    static member Configure(on: bool) : unit = enabled <- on

    /// The first 20 failures are described, then one a second (with the running count in the line): a flood in the first phase of a
    /// container must not use up what a later phase would say.
    static member ShouldReport(n: int64) : bool =
        if n <= 20L then
            true
        else
            let now = Environment.TickCount64
            let last = Interlocked.Read(&lastReport)
            now - last >= 1000L && Interlocked.CompareExchange(&lastReport, now, last) = last

    /// Frames found changed since they were published, and frames checked.
    static member Failures = Interlocked.Read(&failures)
    static member Checks = Interlocked.Read(&checks)

    /// At publish.
    static member Stamp(frame: Frame) : unit = if enabled then frame.Probe <- Frame.ProbeOf frame.Bytes

    /// After a gathered `sendmsg`: the address the iovec table gave the kernel for `payload` against where the array is now. Different
    /// means the array moved while the kernel was reading it (it was not pinned), and what the kernel read was whatever was left there.
    static member CheckAddress(payload: byte[], given: nativeint, index: int) : unit =
        if payload.Length > 0 then
            let now =
                NativeInterop.NativePtr.toNativeInt (
                    NativeInterop.NativePtr.ofVoidPtr<byte> (
                        System.Runtime.CompilerServices.Unsafe.AsPointer(&System.Runtime.InteropServices.MemoryMarshal.GetArrayDataReference payload)
                    )
                )
            if now <> given then
                let n = Interlocked.Increment(&failures)
                if CableVerify.ShouldReport n then
                    eprintfn
                        "ERROR campfire: cable verify: payload %d of the batch (%d bytes) MOVED before sendmsg returned: the kernel was given %x, the array is at %x now, generation %d, GCs %d/%d/%d, thread %d, failure %d"
                        index
                        payload.Length
                        (int64 given)
                        (int64 now)
                        (GC.GetGeneration payload)
                        (GC.CollectionCount 0)
                        (GC.CollectionCount 1)
                        (GC.CollectionCount 2)
                        Environment.CurrentManagedThreadId
                        n

    /// At send: `payload` is what goes to the socket (the frame's own array, or its deflated form, which is not checked).
    static member Check(frame: Frame, payload: byte[], where: string, tag: string) : unit =
        if frame.Probe <> 0UL && obj.ReferenceEquals(payload, frame.Bytes) then
            Interlocked.Increment(&checks) |> ignore
            if Frame.ProbeOf payload <> frame.Probe then
                let n = Interlocked.Increment(&failures)
                if CableVerify.ShouldReport n then
                    let zeros = payload |> Array.forall (fun b -> b = 0uy)
                    eprintfn
                        "ERROR campfire: cable verify: frame seq %d (%d bytes) no longer matches its probe %s: all zero %b, generation %d, GCs %d/%d/%d, thread %d, connection %s, failure %d"
                        frame.Seq
                        payload.Length
                        where
                        zeros
                        (GC.GetGeneration payload)
                        (GC.CollectionCount 0)
                        (GC.CollectionCount 1)
                        (GC.CollectionCount 2)
                        Environment.CurrentManagedThreadId
                        tag
                        n

// --- Handshake ---------------------------------------------------------------------------------

/// The server's side of an accepted opening handshake.
type Handshake = { Accept: string; Deflate: bool }

module Handshake =
    /// A `permessage-deflate` offer we can answer with `DeflateResponse`: any parameters but a
    /// server window smaller than zlib's 15 bits (browsers don't ask for one).
    let private acceptableDeflateOffer (offer: string) : bool =
        let parts = offer.Split ';' |> Array.map (fun p -> p.Trim())
        if parts[0] <> "permessage-deflate" then
            false
        else
            parts
            |> Array.skip 1
            |> Array.forall (fun param ->
                let name, (value: string | null) =
                    match param.IndexOf '=' with
                    | -1 -> param, null
                    | eq -> param.Substring(0, eq).Trim(), param.Substring(eq + 1).Trim().Trim('"')
                match name with
                | "server_no_context_takeover"
                | "client_no_context_takeover" -> isNull value
                | "client_max_window_bits" ->
                    match value with
                    | null -> true
                    | value ->
                        match Byte.TryParse(value, Globalization.NumberStyles.AllowLeadingSign, Globalization.CultureInfo.InvariantCulture) with
                        | true, bits -> bits >= 8uy && bits <= 15uy
                        | _ -> false
                | "server_max_window_bits" -> value = "15"
                | _ -> false)

    /// Checks the client's handshake (version 13 and a key; the caller has checked the method and
    /// `Upgrade`/`Connection` headers) and picks compression if one of its offers suits.
    let accept (headers: IHeaderDictionary) : Handshake option =
        let version = headers["Sec-WebSocket-Version"]
        let key = headers["Sec-WebSocket-Key"]
        if version.Count = 0 || key.Count = 0 then
            None
        else
            let key = nonNull key[0]
            // The 16 random bytes, in canonical padded Base64 (the `base64` crate's STANDARD).
            let validKey =
                key.Length = 24
                && (let decoded = Array.zeroCreate<byte> 18
                    let mutable written = 0
                    Convert.TryFromBase64String(key, decoded, &written)
                    && written = 16
                    && Convert.ToBase64String(decoded, 0, 16) = key)
            if version[0] <> "13" || not validKey then
                None
            else
                let input = Encoding.ASCII.GetBytes(key + AcceptGuid)
                let accept = Convert.ToBase64String(SHA1.HashData input)
                let extensions = headers["Sec-WebSocket-Extensions"]
                let mutable deflate = false
                for line in extensions do
                    match line with
                    | null -> ()
                    | line ->
                        for offer in line.Split ',' do
                            if acceptableDeflateOffer offer then deflate <- true
                Some { Accept = accept; Deflate = deflate }

    /// The 101 response's WebSocket headers (the caller adds `Sec-WebSocket-Protocol`).
    let responseHeaders (handshake: Handshake) (headers: IHeaderDictionary) : unit =
        headers["Upgrade"] <- "websocket"
        headers["Connection"] <- "upgrade"
        headers["Sec-WebSocket-Accept"] <- handshake.Accept
        if handshake.Deflate then headers["Sec-WebSocket-Extensions"] <- DeflateResponse

// --- Reading -----------------------------------------------------------------------------------

/// What a client sent.
type Incoming =
    | Text of string
    | Binary
    | Ping of byte[]
    /// A pong, with its payload (onCrack: the connection's probe is answered by a pong echoing it).
    | Pong of byte[]
    /// A close frame, with its status code if it had one.
    | Close of code: uint16 option

/// Why a `Reader` stopped.
type ReadError =
    /// Reading the socket failed, or the client went away (`EndOfStreamException`).
    | Io of exn
    /// The client broke the protocol: the connection closes with `code`, the one websocket-driver
    /// (under Action Cable) closes with for the same failure.
    | ProtocolViolation of code: uint16

let private fail (code: uint16) : 'a = raise (ProtocolFailure code)

/// A compressed message's text. Invalid deflate data is a protocol error: Action Cable doesn't
/// negotiate compression, so there's no websocket-driver code to match.
let internal inflate (data: ReadOnlySpan<byte>) : byte[] =
    let input = Array.zeroCreate<byte> (data.Length + 4)
    data.CopyTo(Span input)
    Buffer.BlockCopy(deflateTail, 0, input, data.Length, 4)
    use source = new MemoryStream(input, false)
    use stream = new DeflateStream(source, CompressionMode.Decompress)
    let mutable out = ArrayPool<byte>.Shared.Rent(max 256 (data.Length * 4))
    let mutable length = 0
    try
        try
            let mutable reading = true
            while reading do
                if out.Length - length < 1024 then
                    let grown = ArrayPool<byte>.Shared.Rent(out.Length * 2)
                    Buffer.BlockCopy(out, 0, grown, 0, length)
                    ArrayPool<byte>.Shared.Return out
                    out <- grown
                match stream.Read(out, length, out.Length - length) with
                | 0 -> reading <- false
                | n ->
                    length <- length + n
                    if length > MaxMessage then fail TooLarge
            out.AsSpan(0, length).ToArray()
        with :? InvalidDataException -> fail ProtocolError
    finally
        ArrayPool<byte>.Shared.Return out

/// A close frame's status code (RFC 6455 section 5.5.1, section 7.4): no payload, or a code a peer may send
/// followed by a UTF-8 reason.
let private closeCode (buffer: byte[]) (length: int) : uint16 option =
    let payload = ReadOnlySpan(buffer, 0, length)
    if payload.Length = 0 then
        None
    elif payload.Length = 1 then
        fail ProtocolError
    else
        let code = (uint16 payload[0] <<< 8) ||| uint16 payload[1]
        let valid = (code >= 1000us && code <= 1003us) || (code >= 1007us && code <= 1014us) || (code >= 3000us && code <= 4999us)
        let utf8 = System.Text.Unicode.Utf8.IsValid(payload.Slice 2)
        if not valid || not utf8 then fail ProtocolError else Some code

let private strictUtf8 = UTF8Encoding(false, true)

/// XORs `buffer[0..length)` with the 4-byte `mask`, repeating.
let private unmask (buffer: byte[]) (length: int) (mask: byte[]) : unit =
    let mutable i = 0
    if Vector.IsHardwareAccelerated && length >= Vector<byte>.Count then
        let width = Vector<byte>.Count
        let repeated = Array.init width (fun j -> mask[j % 4])
        let key = Vector<byte>(repeated)
        while i + width <= length do
            (Vector<byte>(buffer, i) ^^^ key).CopyTo(buffer, i)
            i <- i + width
    while i < length do
        buffer[i] <- buffer[i] ^^^ mask[i % 4]
        i <- i + 1

/// A fragmented message so far.
[<Sealed>]
type private Partial(opcode: byte, compressed: bool, data: byte[], length: int) =
    member val Opcode = opcode
    member val Compressed = compressed
    member val Data = data with get, set
    member val Length = length with get, set

    /// Adds a continuation frame's payload.
    member this.Append(payload: byte[], payloadLength: int) : unit =
        if this.Data.Length - this.Length < payloadLength then
            let grown = ArrayPool<byte>.Shared.Rent(max (this.Data.Length * 2) (this.Length + payloadLength))
            Buffer.BlockCopy(this.Data, 0, grown, 0, this.Length)
            ArrayPool<byte>.Shared.Return this.Data
            this.Data <- grown
        Buffer.BlockCopy(payload, 0, this.Data, this.Length, payloadLength)
        this.Length <- this.Length + payloadLength

/// A complete message: inflated if it was compressed, and for text, decoded as strict UTF-8.
let private finishMessage (message: Partial) : Incoming =
    let data = ReadOnlySpan(message.Data, 0, message.Length)
    let inflated: byte[] | null = if message.Compressed then inflate data else null
    let bytes =
        match inflated with
        | null -> data
        | inflated -> ReadOnlySpan inflated
    match message.Opcode with
    | OpText ->
        try
            Text(strictUtf8.GetString bytes)
        with :? DecoderFallbackException ->
            fail EncodingError
    | _ -> Binary

/// Reads client frames. It keeps no buffer between messages: frames are read header first, then
/// exactly their payload, so an idle socket holds a few bytes.
[<Sealed>]
type Reader(io: Stream, deflate: bool) =
    let head = Array.zeroCreate<byte> 14
    let mask = Array.zeroCreate<byte> 4
    /// Kept across the control frames that may arrive between a message's fragments.
    let mutable partial: Partial | null = null

    let readExact (buffer: byte[]) (offset: int) (count: int) (ct: CancellationToken) : Task =
        task {
            let mutable got = 0
            while got < count do
                let! n = io.ReadAsync(Memory<byte>(buffer, offset + got, count - got), ct)
                if n = 0 then raise (EndOfStreamException())
                got <- got + n
        }

    /// A frame's payload, unmasked, in a pooled buffer. It's grown as bytes arrive rather than
    /// allocated from the header's claim, so a client can't make the server hold a megabyte per
    /// socket by announcing a frame it never sends.
    let readPayload (length: int) (ct: CancellationToken) : Task<struct (byte[] * int)> =
        task {
            let mutable buffer = ArrayPool<byte>.Shared.Rent(min length 65536)
            let mutable got = 0
            while got < length do
                if got = buffer.Length then
                    let grown = ArrayPool<byte>.Shared.Rent(min length (buffer.Length * 2))
                    Buffer.BlockCopy(buffer, 0, grown, 0, got)
                    ArrayPool<byte>.Shared.Return buffer
                    buffer <- grown
                let! n = io.ReadAsync(Memory<byte>(buffer, got, min (length - got) (buffer.Length - got)), ct)
                if n = 0 then raise (EndOfStreamException())
                got <- got + n
            unmask buffer length mask
            return struct (buffer, length)
        }

    /// A frame's header, checked in the order websocket-driver checks it (`Hybi#parse_opcode`,
    /// `#parse_length`, `#check_frame_length`), which decides the close code when a frame is wrong
    /// in more than one way. Returns (fin, compressed, opcode, length).
    let readHeader (ct: CancellationToken) : Task<struct (bool * bool * byte * int)> =
        task {
            do! readExact head 0 2 ct
            let fin = head[0] &&& 0x80uy <> 0uy
            let compressed = head[0] &&& 0x40uy <> 0uy
            let opcode = head[0] &&& 0x0fuy
            let control = opcode >= 0x8uy
            // RSV1 may only start a message, and only with compression negotiated.
            let reserved = head[0] &&& 0x30uy <> 0uy || (compressed && not (deflate && (opcode = OpText || opcode = OpBinary)))
            let known =
                opcode = OpContinuation || opcode = OpText || opcode = OpBinary || opcode = OpClose || opcode = OpPing || opcode = OpPong
            let interruptsAMessage = (opcode = OpText || opcode = OpBinary) && not (isNull partial)
            if reserved || not known || (control && not fin) || interruptsAMessage then fail ProtocolError
            if head[1] &&& 0x80uy = 0uy then fail Unacceptable
            let! length =
                task {
                    match head[1] &&& 0x7fuy with
                    | 126uy ->
                        do! readExact head 2 2 ct
                        return uint64 ((uint16 head[2] <<< 8) ||| uint16 head[3])
                    | 127uy ->
                        do! readExact head 2 8 ct
                        return Buffers.Binary.BinaryPrimitives.ReadUInt64BigEndian(ReadOnlySpan(head, 2, 8))
                    | n -> return uint64 n
                }
            if control && length > 125UL then fail ProtocolError
            let soFar =
                match partial with
                | null -> 0UL
                | p when not control -> uint64 p.Length
                | _ -> 0UL
            // `saturating_add`: a length near u64::MAX is still too large.
            if length > uint64 MaxMessage || soFar + length > uint64 MaxMessage then fail TooLarge
            do! readExact mask 0 4 ct
            return struct (fin, compressed, opcode, int length)
        }

    /// The next message or control frame, reassembling fragments and decompressing. Raises
    /// `ProtocolFailure` for a protocol error and an `IOException`, `EndOfStreamException` or
    /// `OperationCanceledException` for a failed read; `Next` turns them into a `ReadError`.
    member private _.Read(ct: CancellationToken) : Task<Incoming> =
        task {
            let mutable result = ValueNone
            while result.IsNone do
                let! struct (fin, compressed, opcode, length) = readHeader ct
                let! struct (payload, payloadLength) = readPayload length ct
                let mutable keep = false
                try
                    match opcode with
                    | OpClose -> result <- ValueSome(Close(closeCode payload payloadLength))
                    | OpPing -> result <- ValueSome(Ping(payload.AsSpan(0, payloadLength).ToArray()))
                    | OpPong -> result <- ValueSome(Pong(payload.AsSpan(0, payloadLength).ToArray()))
                    | OpText
                    | OpBinary ->
                        // The payload buffer becomes the message's, and is returned with it.
                        partial <- Partial(opcode, compressed, payload, payloadLength)
                        keep <- true
                    | _ ->
                        match partial with
                        | null -> fail ProtocolError // a continuation of nothing
                        | p -> p.Append(payload, payloadLength)
                finally
                    if not keep then ArrayPool<byte>.Shared.Return payload
                if result.IsNone && fin then
                    let message = nonNull partial
                    partial <- null
                    try
                        result <- ValueSome(finishMessage message)
                    finally
                        ArrayPool<byte>.Shared.Return message.Data
            return result.Value
        }

    /// The next message or control frame, or why the socket stopped.
    member this.Next(ct: CancellationToken) : Task<Result<Incoming, ReadError>> =
        task {
            try
                let! incoming = this.Read ct
                return Ok incoming
            with
            | ProtocolFailure code -> return Error(ProtocolViolation code)
            | e -> return Error(Io e)
        }

// --- Writing -----------------------------------------------------------------------------------

/// How long a write may wait for a client to read before it fails. A client that stops reading
/// doesn't hold its connection's task forever.
let WriteTimeout = TimeSpan.FromSeconds 30.0

/// A final frame's header: FIN, RSV1 when `compressed`, `opcode`, and the payload length. Returns
/// how many bytes of `dest` it used.
let private writeHeader (dest: Span<byte>) (opcode: byte) (compressed: bool) (length: int) : int =
    dest[0] <- 0x80uy ||| (if compressed then 0x40uy else 0uy) ||| opcode
    if length < 126 then
        dest[1] <- byte length
        2
    elif length <= int UInt16.MaxValue then
        dest[1] <- 126uy
        dest[2] <- byte (length >>> 8)
        dest[3] <- byte length
        4
    else
        dest[1] <- 127uy
        Buffers.Binary.BinaryPrimitives.WriteUInt64BigEndian(dest.Slice(2, 8), uint64 length)
        10

/// Per-thread scratch for gathered writes, reused by every write the thread makes: each frame's header and header length, its
/// payload array, the segment list for the managed fallback, and (Linux) native memory for the `msghdr` and its iovec table.
[<Sealed>]
type GatherScratch() =
    [<ThreadStatic; DefaultValue>]
    static val mutable private current: GatherScratch | null

    /// On the pinned object heap: the kernel is given addresses in it.
    member val Headers: byte[] = GC.AllocateArray<byte>(2560, true) with get, set
    member val HeaderLengths: int[] = Array.zeroCreate 256
    member val Payloads: byte[][] = Array.zeroCreate 256
    /// 56 bytes of `msghdr` (zeroed, the fields that change are set per call) and then 4 words per frame (header and payload:
    /// address and length each), 256 frames at most.
    member val Native: nativeint = 0n with get, set

    static member Get(frames: int) : GatherScratch =
        let scratch =
            match GatherScratch.current with
            | null ->
                let created = GatherScratch()
                GatherScratch.current <- created
                created
            | existing -> existing
        if scratch.Headers.Length < frames * 10 then scratch.Headers <- GC.AllocateArray<byte>(frames * 10, true)
        scratch

#nowarn "9" // `sendmsg` over pinned arrays and a native iovec table

/// `sendmsg` over the frames' own arrays (Linux, glibc's layout of `msghdr`: the same on aarch64 and x86-64). .NET's own gather send
/// creates a GC handle for every segment of every call (measured in unit R4.2: about 9% of a fan-out's CPU, as much as the copy it
/// replaced). Here each payload is pinned by a `fixed` local, eight to a stack frame (`pinFrom`), which costs nothing unless a collection
/// walks the stack during the call; the scratch headers are on the pinned object heap.
module private Sendmsg =
    open System.Runtime.CompilerServices
    open System.Runtime.InteropServices
    open Microsoft.FSharp.NativeInterop

    [<DllImport("libc.so.6", EntryPoint = "sendmsg", SetLastError = true)>]
    extern nativeint private sendmsg(int fd, nativeint msg, int flags)

    let available = OperatingSystem.IsLinux() && (RuntimeInformation.ProcessArchitecture = Architecture.Arm64 || RuntimeInformation.ProcessArchitecture = Architecture.X64)

    [<Literal>]
    let private MSG_DONTWAIT = 0x40
    [<Literal>]
    let private MSG_NOSIGNAL = 0x4000
    [<Literal>]
    let private EINTR = 4

    /// Tests only: runs between the iovec table's filling and the `sendmsg` (a forced compacting collection, so that an array that could
    /// move does move where the kernel is about to read it).
    let mutable internal beforeCall: (unit -> unit) | null = null

    let native (scratch: GatherScratch) : nativeint =
        if scratch.Native = 0n then
            let size = 56 + 256 * 32
            let block = NativeMemory.AllocZeroed(unativeint size) |> NativePtr.ofVoidPtr<byte> |> NativePtr.toNativeInt
            scratch.Native <- block
        scratch.Native

    [<Literal>]
    let private PerLevel = 8

    let private none: byte[] = [||]

    /// The call itself, every payload pinned by a caller.
    let private call (fd: int) (block: nativeint) : struct (int64 * int) =
        match beforeCall with
        | null -> ()
        | hook -> hook ()
        let mutable result = struct (0L, 0)
        let mutable again = true
        while again do
            let sent = sendmsg (fd, block, MSG_DONTWAIT ||| MSG_NOSIGNAL)
            if sent >= 0n then
                result <- struct (int64 sent, 0)
                again <- false
            else
                let errno = Marshal.GetLastPInvokeError()
                if errno <> EINTR then
                    result <- struct (0L, errno)
                    again <- false
        result

    /// Pins payloads `i` .. `i + 7` with `fixed` locals, puts their addresses in the iovec table, then pins the next eight (or makes the
    /// call). The recursive call is NOT in tail position: the check after it reads this level's payloads, so F# cannot turn the recursion
    /// into a loop (round 4's version was a tail call, which F# compiled to a loop with one pinned slot) and the JIT cannot drop this frame;
    /// every level's pinned locals stay on the stack until the call has returned.
    [<MethodImpl(MethodImplOptions.NoInlining)>]
    let rec private pinFrom (fd: int) (scratch: GatherScratch) (block: nativeint) (count: int) (i: int) : struct (int64 * int) =
        let payloads = scratch.Payloads
        let n = min PerLevel (count - i)
        use p0 = fixed (if n > 0 then payloads[i] else none)
        use p1 = fixed (if n > 1 then payloads[i + 1] else none)
        use p2 = fixed (if n > 2 then payloads[i + 2] else none)
        use p3 = fixed (if n > 3 then payloads[i + 3] else none)
        use p4 = fixed (if n > 4 then payloads[i + 4] else none)
        use p5 = fixed (if n > 5 then payloads[i + 5] else none)
        use p6 = fixed (if n > 6 then payloads[i + 6] else none)
        use p7 = fixed (if n > 7 then payloads[i + 7] else none)
        let table = NativePtr.ofNativeInt<nativeint> (block + 56n)
        let slot = 4 * i + 2
        if n > 0 then NativePtr.set table slot (NativePtr.toNativeInt p0)
        if n > 1 then NativePtr.set table (slot + 4) (NativePtr.toNativeInt p1)
        if n > 2 then NativePtr.set table (slot + 8) (NativePtr.toNativeInt p2)
        if n > 3 then NativePtr.set table (slot + 12) (NativePtr.toNativeInt p3)
        if n > 4 then NativePtr.set table (slot + 16) (NativePtr.toNativeInt p4)
        if n > 5 then NativePtr.set table (slot + 20) (NativePtr.toNativeInt p5)
        if n > 6 then NativePtr.set table (slot + 24) (NativePtr.toNativeInt p6)
        if n > 7 then NativePtr.set table (slot + 28) (NativePtr.toNativeInt p7)
        let result = if i + PerLevel < count then pinFrom fd scratch block count (i + PerLevel) else call fd block
        // Unit R5.1 (`CAMPFIRE_CABLE_VERIFY`): this level's payloads are still pinned here; the addresses the kernel was given are where they are.
        if CableVerify.Enabled then
            for j in i .. i + n - 1 do
                CableVerify.CheckAddress(payloads[j], NativePtr.get table (4 * j + 2), j)
        result

    /// One non-blocking `sendmsg` of the `count` header and payload pairs in `scratch`. Returns (bytes sent, errno; 0 when none).
    let send (socket: Net.Sockets.Socket) (scratch: GatherScratch) (count: int) : struct (int64 * int) =
        let block = native scratch
        let handle = socket.SafeHandle
        let mutable added = false
        handle.DangerousAddRef(&added)
        try
            // The headers are on the pinned object heap.
            let headers = NativePtr.toNativeInt (NativePtr.ofVoidPtr<byte> (Runtime.CompilerServices.Unsafe.AsPointer(&MemoryMarshal.GetArrayDataReference scratch.Headers)))
            let table = NativePtr.ofNativeInt<nativeint> (block + 56n)
            for i in 0 .. count - 1 do
                NativePtr.set table (4 * i) (headers + nativeint (i * 10))
                NativePtr.set table (4 * i + 1) (nativeint scratch.HeaderLengths[i])
                NativePtr.set table (4 * i + 3) (nativeint scratch.Payloads[i].Length)
            let msg = NativePtr.ofNativeInt<nativeint> block
            NativePtr.set msg 2 (block + 56n) // msg_iov
            NativePtr.set msg 3 (nativeint (count * 2)) // msg_iovlen
            let result = pinFrom (int (handle.DangerousGetHandle())) scratch block count 0
            GC.KeepAlive scratch.Headers
            result
        finally
            if added then handle.DangerousRelease()

/// Tests only: `hook` runs in every gathered write between the iovec table's filling and the `sendmsg` (null: none).
let internal SetBeforeSendmsg (hook: (unit -> unit) | null) : unit = Sendmsg.beforeCall <- hook

/// Whether this platform gathers writes (Linux; elsewhere `Writer` copies).
let GatherAvailable = Sendmsg.available

/// Unit R4.5: the bytes the peer of `socket` has acknowledged since it connected (Linux `TCP_INFO`'s `tcpi_bytes_acked`, at
/// offset 120 of `struct tcp_info`), or -1 where the kernel does not say. It moves while a peer takes data and stands still
/// once a peer that reads nothing has a full receive window.
let AckedBytes (socket: Net.Sockets.Socket) : int64 =
    if not (OperatingSystem.IsLinux()) then
        -1L
    else
        try
            let info: byte[] = Array.zeroCreate 256
            // IPPROTO_TCP = 6, TCP_INFO = 11
            let length = socket.GetRawSocketOption(6, 11, Span<byte>(info))
            if length >= 128 then BitConverter.ToInt64(info, 120) else -1L
        with _ ->
            -1L

/// How many gathered writes the socket did not take whole (tests check that they forced the partial path).
let mutable private partialGathers = 0L

/// A batch with more frames than this is copied (a gather list that long approaches the kernel's iovec limit).
let private MaxGatherFrames = 256

/// Gathered writes the socket took only in part, since the process started.
let PartialGathers () : int64 = Interlocked.Read(&partialGathers)

/// Writes server frames: unmasked, each as its header plus its (shared) payload, a batch to one
/// write. A write that hasn't completed after `timeout` fails: `abort` is called to cut the
/// connection and the write raises `TimeoutException`.
///
/// onCrack: `direct` is the connection's own socket, when writing to it is safe (plain TCP, Kestrel's socket transport). Once
/// `Detach` is called, writes go to it with one send each, instead of through Kestrel's upgraded stream, its output pipe and
/// its transport's send loop: no copy into the pipe's per-connection blocks, no hop to the transport's I/O thread, and the
/// kernel copies from a buffer the sending thread has just written (unit R2.1). The caller detaches only once nothing it wrote
/// through the stream can still be in Kestrel's pipe (`Connection.run`'s probe), so the bytes stay in order.
///
/// Unit R4.2: on a detached connection `Send` hands the kernel the frames' shared payloads where they are, one `sendmsg` (header,
/// payload, header, payload ...), instead of copying them into one buffer first (`gather`; `CAMPFIRE_CABLE_GATHER=off` copies).
[<Sealed>]
type Writer(io: Stream, deflate: bool, timeout: TimeSpan, abort: unit -> unit, direct: Net.Sockets.Socket | null, gather: bool) =
    let mutable detached = false

    /// Unit R5.1: the connection's trace (`CAMPFIRE_CABLE_TRACE`); null without the switch.
    member val internal Trace: ConnTrace | null = null with get, set

    /// Unit R5.1: what `CAMPFIRE_CABLE_VERIFY` says about this connection when a frame fails (its client's address).
    member val internal Tag = "" with get, set

    new(io: Stream, deflate: bool, timeout: TimeSpan, abort: unit -> unit, direct: Net.Sockets.Socket | null) =
        Writer(io, deflate, timeout, abort, direct, true)
    new(io: Stream, deflate: bool, timeout: TimeSpan, abort: unit -> unit) = Writer(io, deflate, timeout, abort, null, true)
    new(io: Stream, deflate: bool) = Writer(io, deflate, WriteTimeout, ignore, null, true)

    /// Whether writes can go to the socket itself (after `Detach`).
    member _.CanDetach = not (isNull direct)

    /// Whether writes go to the socket itself now.
    member _.Detached = detached

    /// From now on, writes go to the socket itself. Only once every byte written through the stream has left Kestrel's pipe.
    member _.Detach() : unit = if not (isNull direct) then detached <- true

    /// The rest of a send to the socket that didn't complete in place (the socket's buffer was full): waits for it, sending
    /// what is left, and cuts the connection when it makes no progress for `timeout`.
    ///
    /// Unit R4.5: progress, not the whole write: a peer that is reading, however slowly, is never cut. A send of megabytes to a
    /// reader at a few KB/s is one pending send, so the wait looks at the kernel's count of bytes the peer has acknowledged
    /// (Linux `TCP_INFO`, `AckedBytes`) every eighth of the timeout and gives it a new `timeout` whenever that moved.
    /// A peer that has stopped reading acknowledges nothing once its receive window is full. Where the count is not available
    /// (macOS), a send's completion is the only progress, as before.
    member private _.FinishSend(first: Task<int>, bytes: ReadOnlyMemory<byte>, pooled: byte[] | null) : Task =
        task {
            let socket = nonNull direct
            let tick = TimeSpan.FromTicks(max (timeout.Ticks / 8L) (TimeSpan.FromMilliseconds(20.0).Ticks))
            let ticks = int64 (timeout.TotalSeconds * float Diagnostics.Stopwatch.Frequency)
            let mutable deadline = Diagnostics.Stopwatch.GetTimestamp() + ticks
            let mutable acked = AckedBytes socket
            // `pending` is the send of `rest`'s start.
            let mutable rest = bytes
            let mutable pending: Task<int> | null = first
            while not (isNull pending) do
                let mutable waiting = true
                while waiting do
                    if (nonNull pending).IsCompleted then
                        waiting <- false
                    else
                        use gave = new CancellationTokenSource()
                        let! winner = Task.WhenAny(nonNull pending, Task.Delay(tick, gave.Token))
                        gave.Cancel()
                        if obj.ReferenceEquals(winner, pending) then
                            waiting <- false
                        else
                            let now = Diagnostics.Stopwatch.GetTimestamp()
                            let seen = AckedBytes socket
                            if seen > acked then
                                acked <- seen
                                deadline <- now + ticks
                            elif now >= deadline then
                                // The stalled send still holds its buffer, so that one isn't returned to the pool.
                                abort ()
                                raise (TimeoutException "a socket write timed out")
                let! n = nonNull pending
                if n <= 0 then raise (IOException "the socket took no bytes")
                rest <- rest.Slice n
                deadline <- Diagnostics.Stopwatch.GetTimestamp() + ticks
                pending <- if rest.IsEmpty then null else socket.SendAsync(rest, Net.Sockets.SocketFlags.None).AsTask()
            match pooled with
            | null -> ()
            | pooled -> ArrayPool<byte>.Shared.Return pooled
        }

    /// Writes `bytes` to the socket itself: one send, which completes in place when the socket's buffer takes it all.
    member private this.Send(bytes: ReadOnlyMemory<byte>, pooled: byte[] | null) : ValueTask =
        let socket = nonNull direct
        let send =
            try
                socket.SendAsync(bytes, Net.Sockets.SocketFlags.None)
            with _ ->
                (match pooled with
                 | null -> ()
                 | pooled -> ArrayPool<byte>.Shared.Return pooled)
                reraise ()
        if send.IsCompletedSuccessfully && send.Result = bytes.Length then
            match pooled with
            | null -> ()
            | pooled -> ArrayPool<byte>.Shared.Return pooled
            ValueTask()
        elif send.IsCompletedSuccessfully then
            let rest = bytes.Slice send.Result
            ValueTask(this.FinishSend(socket.SendAsync(rest, Net.Sockets.SocketFlags.None).AsTask(), rest, pooled))
        else
            ValueTask(this.FinishSend(send.AsTask(), bytes, pooled))

    /// A write that didn't complete in place: waits for it, and cuts it after the timeout.
    member private _.Finish(write: ValueTask, pooled: byte[] | null) : Task =
        task {
            use gave = new CancellationTokenSource()
            let pending = write.AsTask()
            let! first = Task.WhenAny(pending, Task.Delay(timeout, gave.Token))
            if obj.ReferenceEquals(first, pending) then
                gave.Cancel()
                do! pending
                match pooled with
                | null -> ()
                | pooled -> ArrayPool<byte>.Shared.Return pooled
            else
                // The stalled write still holds its buffer, so that one isn't returned to the pool.
                abort ()
                raise (TimeoutException "a socket write timed out")
        }

    /// Writes `bytes` (all of `pooled`'s used part, when it is given, which goes back to the pool
    /// afterwards). A write the socket takes at once completes without a task.
    member private this.Write(bytes: ReadOnlyMemory<byte>, pooled: byte[] | null) : ValueTask =
        if detached then this.Send(bytes, pooled) else this.WriteStream(bytes, pooled)

    member private this.WriteStream(bytes: ReadOnlyMemory<byte>, pooled: byte[] | null) : ValueTask =
        let write =
            try
                io.WriteAsync bytes
            with _ ->
                (match pooled with
                 | null -> ()
                 | pooled -> ArrayPool<byte>.Shared.Return pooled)
                reraise ()
        if write.IsCompleted then
            write.GetAwaiter().GetResult()
            match pooled with
            | null -> ()
            | pooled -> ArrayPool<byte>.Shared.Return pooled
            ValueTask()
        else
            ValueTask(this.Finish(write, pooled))

    /// The payload a frame goes out with: its deflated form on a compressed socket when that is worth it.
    member private _.Payload(frame: Frame) : byte[] =
        if deflate then
            match frame.Deflated with
            | null -> frame.Bytes
            | deflated -> deflated
        else
            frame.Bytes

    /// Writes `frames` as text messages, in order, in one write.
    member this.Send(frames: IReadOnlyList<Frame>) : ValueTask =
        match this.Trace with
        | null -> ()
        | trace ->
            trace.BeginBatch detached
            for i in 0 .. frames.Count - 1 do
                let frame = frames[i]
                trace.Frame(frame.Seq, (this.Payload frame).Length)
            trace.EndBatch()
        if detached && gather && Sendmsg.available && frames.Count > 0 && frames.Count <= MaxGatherFrames then
            this.SendGather frames
        else
            this.SendCopy frames

    /// Unit R4.2: one non-blocking `sendmsg` of header and payload pairs, the payloads being the frames' own arrays. What the socket
    /// does not take at once (its buffer is full) is copied into a pooled buffer and finished like any other send, with the
    /// write timeout. The scratch headers are thread-static and the call returns before anyone else could use them.
    member private this.SendGather(frames: IReadOnlyList<Frame>) : ValueTask =
        (match this.Trace with
         | null -> ()
         | trace -> trace.Gather())
        let socket = nonNull direct
        let scratch = GatherScratch.Get frames.Count
        let count = frames.Count
        let mutable total = 0
        for i in 0 .. count - 1 do
            let frame = frames[i]
            let payload = this.Payload frame
            if CableVerify.Enabled then CableVerify.Check(frame, payload, "before sendmsg", this.Tag)
            let compressed = deflate && not (obj.ReferenceEquals(payload, frame.Bytes))
            let used = writeHeader (Span(scratch.Headers, i * 10, 10)) OpText compressed payload.Length
            scratch.HeaderLengths[i] <- used
            scratch.Payloads[i] <- payload
            total <- total + used + payload.Length
        let mutable sent = 0
        let mutable failure: exn | null = null
        try
            let struct (n, e) = Sendmsg.send socket scratch count
            if CableVerify.Enabled then
                for i in 0 .. count - 1 do
                    CableVerify.Check(frames[i], scratch.Payloads[i], "after sendmsg", this.Tag)
            sent <- int n
            // EAGAIN (11 on Linux): the socket's buffer is full, so the rest waits for room.
            if e <> 0 && e <> 11 then failure <- IOException $"sendmsg failed: errno {e}"
        finally
            // Nothing in a thread's scratch keeps a frame alive.
            if sent = total || not (isNull failure) then Array.Clear(scratch.Payloads, 0, count)
        match failure with
        | null -> ()
        | e -> raise e
        if sent = total then
            ValueTask()
        else
            Interlocked.Increment(&partialGathers) |> ignore
            (match this.Trace with
             | null -> ()
             | trace -> trace.Partial(sent, total))
            // The rest, from the header or payload that `sent` ends in.
            let buffer = ArrayPool<byte>.Shared.Rent(total - sent)
            let mutable skip = sent
            let mutable at = 0
            let take (source: byte[]) (offset: int) (length: int) =
                if skip >= length then
                    skip <- skip - length
                else
                    Buffer.BlockCopy(source, offset + skip, buffer, at, length - skip)
                    at <- at + length - skip
                    skip <- 0
            for i in 0 .. count - 1 do
                take scratch.Headers (i * 10) scratch.HeaderLengths[i]
                take scratch.Payloads[i] 0 scratch.Payloads[i].Length
            Array.Clear(scratch.Payloads, 0, count)
            let rest = ReadOnlyMemory(buffer, 0, at)
            let first =
                try
                    socket.SendAsync(rest, Net.Sockets.SocketFlags.None).AsTask()
                with _ ->
                    ArrayPool<byte>.Shared.Return buffer
                    reraise ()
            ValueTask(this.FinishSend(first, rest, buffer))

    member private this.SendCopy(frames: IReadOnlyList<Frame>) : ValueTask =
        (match this.Trace with
         | null -> ()
         | trace -> trace.Copy())
        let mutable total = 0
        for i in 0 .. frames.Count - 1 do
            if CableVerify.Enabled then CableVerify.Check(frames[i], this.Payload(frames[i]), "before the copy", this.Tag)
            total <- total + 10 + this.Payload(frames[i]).Length
        let buffer = ArrayPool<byte>.Shared.Rent total
        let mutable at = 0
        for i in 0 .. frames.Count - 1 do
            let frame = frames[i]
            let payload = this.Payload frame
            let compressed = deflate && not (obj.ReferenceEquals(payload, frame.Bytes))
            at <- at + writeHeader (Span(buffer, at, 10)) OpText compressed payload.Length
            Buffer.BlockCopy(payload, 0, buffer, at, payload.Length)
            at <- at + payload.Length
        this.Write(ReadOnlyMemory(buffer, 0, at), buffer)

    member private this.Control(opcode: byte, payload: byte[]) : Task =
        (match this.Trace with
         | null -> ()
         | trace -> trace.Control(opcode, payload.Length))
        let buffer = Array.zeroCreate<byte> (10 + payload.Length)
        let used = writeHeader (Span buffer) opcode false payload.Length
        Buffer.BlockCopy(payload, 0, buffer, used, payload.Length)
        this.Write(ReadOnlyMemory(buffer, 0, used + payload.Length), null).AsTask()

    member this.Pong(payload: byte[]) : Task = this.Control(OpPong, payload)

    /// A ping with `payload`, which a client answers with a pong echoing it (RFC 6455 section 5.5.2).
    member this.Ping(payload: byte[]) : Task = this.Control(OpPing, payload)

    /// A close frame with `code` and no reason.
    member this.Close(code: uint16) : Task = this.Control(OpClose, [| byte (code >>> 8); byte code |])

    /// The reply to a client's close frame, echoing its code (none if it sent none), which
    /// completes the closing handshake.
    member this.CloseReply(code: uint16 option) : Task =
        match code with
        | Some code -> this.Close code
        | None -> this.Control(OpClose, [||])
