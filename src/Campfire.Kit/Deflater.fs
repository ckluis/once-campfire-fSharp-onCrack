// Port of rust/crates/kit/src/deflater.rs
//
// `Rack::Deflater` (rack 3.2), which the reference installs around the whole app in `config.ru`:
// it gzips every response with a body when the client accepts gzip, whatever its size or type,
// and adds `Accept-Encoding` to `Vary`. A gzipped body has no `Content-Length`, so it goes out
// chunked (and the front server's compression leaves it alone).
//
// The pieces of the response cache this needs (`deflater/splice.rs`: page parts and their gzip
// pieces) sit behind `IPageParts`; the kit's adapter applies this to each response it writes.
namespace Campfire.Kit

open System
open System.Buffers
open System.Buffers.Binary
open System.IO
open System.IO.Compression
open System.Runtime.InteropServices
open System.Threading.Tasks
open Microsoft.FSharp.NativeInterop
open Campfire.Kit

#nowarn "9"

/// What `Rack::Deflater` decided for a response.
type Deflated =
    /// Not gzipped: sent as it is (the `Vary` header may have changed).
    | Unchanged
    /// Gzipped with this modification time: the headers already say so, and the body goes out as a
    /// gzip member without a length.
    | Gzip of mtime: uint32
    /// The client accepts nothing the app can send: a 406 (`Deflater.notAcceptable`) replaces the response.
    | NotAcceptable

module Deflater =
    /// A bound on the bytes of kept gzip members (a sidebar's is ~6 KB).
    [<Literal>]
    let MaxGzippedBytes = 16777216

    /// `/\bword\b/`
    let internal hasWord (haystack: string) (word: string) : bool =
        let isWord (c: char) = Char.IsAsciiLetterOrDigit c || c = '_'
        let mutable found = false
        let mutable from = 0
        while not found && from <= haystack.Length - word.Length do
            match haystack.IndexOf(word, from, StringComparison.Ordinal) with
            | -1 -> from <- haystack.Length
            | i ->
                let beforeOk = i = 0 || not (isWord haystack[i - 1])
                let afterOk = i + word.Length >= haystack.Length || not (isWord haystack[i + word.Length])
                if beforeOk && afterOk then found <- true
                from <- i + 1
        found

    /// `Rack::Request#accept_encoding` (`parse_http_accept_header`).
    let internal parseAcceptEncoding (header: string) : (string * float) list =
        [ for part in header.Split ',' do
              let part = part.Trim()
              if part <> "" then
                  let attribute, (parameters: string | null) =
                      match part.IndexOf ';' with
                      | -1 -> part, null
                      | semi -> part.Substring(0, semi).Trim(), part.Substring(semi + 1).Trim()
                  // `/\Aq=([\d.]+)/ =~ parameters`, else 1.0.
                  let quality =
                      match parameters with
                      | null -> 1.0
                      | parameters when parameters.StartsWith("q=", StringComparison.Ordinal) ->
                          let q = parameters.Substring 2
                          let mutable stop = 0
                          while stop < q.Length && (Char.IsAsciiDigit q[stop] || q[stop] = '.') do
                              stop <- stop + 1
                          if stop = 0 then 1.0 else Campfire.Ruby.Ruby.toF (q.Substring(0, stop))
                      | _ -> 1.0
                  attribute, quality ]

    /// `Rack::Utils.select_best_encoding`
    let internal selectBestEncoding (available: string list) (accept: (string * float) list) : string voption =
        let accept = List.truncate 16 accept
        let expanded = ResizeArray<string * float * int>()
        let mutable wildcardSeen = false
        for (m, q) in accept do
            let preference =
                match List.tryFindIndex (fun a -> a = m) available with
                | Some i -> i
                | None -> available.Length
            if m = "*" then
                if not wildcardSeen then
                    for m2 in available |> List.filter (fun a -> not (accept |> List.exists (fun (m, _) -> m = a))) do
                        expanded.Add((m2, q, preference))
                    wildcardSeen <- true
            else
                expanded.Add((m, q, preference))
        let sorted =
            expanded
            |> List.ofSeq
            |> List.sortWith (fun (_, q1, p1) (_, q2, p2) ->
                let byQ = compare q2 q1
                if byQ <> 0 then byQ else compare p1 p2)
        let candidates = ResizeArray<string>(sorted |> List.map (fun (m, _, _) -> m))
        if not (candidates.Contains "identity") then candidates.Add "identity"
        for (m, q, _) in expanded do
            if q = 0.0 then candidates.RemoveAll(fun c -> c = m) |> ignore
        candidates |> Seq.tryPick (fun c -> available |> List.tryFind (fun a -> a = c)) |> ValueOption.ofOption

    /// `should_deflate?` (rack 3.2.6; the reference passes no `:include` or `:if`): not for statuses
    /// without a body (1xx, 204, 304), `no-transform`, non-identity `Content-Encoding`, or a
    /// `Content-Length: 0` the app set (static files and error pages; an app response's length is
    /// otherwise the server's doing, after this middleware, so empty rendered bodies are gzipped).
    let internal shouldDeflate (response: Response) (appSetLength: bool) : bool =
        if Status.hasNoBody response.Status then
            false
        else
            let get name = response.GetHeader name
            let noTransform =
                match get Hdr.CacheControl with
                | null -> false
                | cc -> hasWord cc "no-transform"
            let encoded =
                match get Hdr.ContentEncoding with
                | null -> false
                | ce -> not (hasWord ce "identity")
            if noTransform || encoded then
                false
            else
                let appSet = response.StaticFile || appSetLength
                not (appSet && get Hdr.ContentLength = "0")

    // --- gzip -----------------------------------------------------------------------------------

    let private slicingTables: uint32[][] =
        let tables = Array.init 8 (fun _ -> Array.zeroCreate<uint32> 256)
        for n in 0..255 do
            let mutable c = uint32 n
            for _ in 0..7 do
                c <- if c &&& 1u <> 0u then 0xEDB88320u ^^^ (c >>> 1) else c >>> 1
            tables[0][n] <- c
        for n in 0..255 do
            let mutable c = tables[0][n]
            for k in 1..7 do
                c <- tables[0][int (c &&& 0xFFu)] ^^^ (c >>> 8)
                tables[k][n] <- c
        tables

    /// The running CRC-32 (IEEE, as zlib's `crc32`) of `data` after what `crc` covers, by slicing-by-8
    /// tables: what runs where the CPU has no CRC instruction (and what the tests check the other against).
    let internal crc32Software (crc: uint32) (data: ReadOnlySpan<byte>) : uint32 =
        let t = slicingTables
        let mutable c = ~~~crc
        let mutable i = 0
        while i + 8 <= data.Length do
            let lo = BinaryPrimitives.ReadUInt32LittleEndian(data.Slice i) ^^^ c
            let hi = BinaryPrimitives.ReadUInt32LittleEndian(data.Slice(i + 4))
            c <-
                t[7][int (lo &&& 0xFFu)]
                ^^^ t[6][int ((lo >>> 8) &&& 0xFFu)]
                ^^^ t[5][int ((lo >>> 16) &&& 0xFFu)]
                ^^^ t[4][int (lo >>> 24)]
                ^^^ t[3][int (hi &&& 0xFFu)]
                ^^^ t[2][int ((hi >>> 8) &&& 0xFFu)]
                ^^^ t[1][int ((hi >>> 16) &&& 0xFFu)]
                ^^^ t[0][int (hi >>> 24)]
            i <- i + 8
        while i < data.Length do
            c <- t[0][int ((c ^^^ uint32 data[i]) &&& 0xFFu)] ^^^ (c >>> 8)
            i <- i + 1
        ~~~c

    /// The same by the ARM CRC-32 instructions.
    let private crc32Arm (crc: uint32) (data: ReadOnlySpan<byte>) : uint32 =
        let mutable c = ~~~crc
        let mutable i = 0
        while i + 8 <= data.Length do
            c <- System.Runtime.Intrinsics.Arm.Crc32.Arm64.ComputeCrc32(c, BinaryPrimitives.ReadUInt64LittleEndian(data.Slice i))
            i <- i + 8
        while i < data.Length do
            c <- System.Runtime.Intrinsics.Arm.Crc32.ComputeCrc32(c, data[i])
            i <- i + 1
        ~~~c

    /// The running CRC-32 (IEEE, as zlib's `crc32`) of `data` after what `crc` covers.
    let internal crc32Update (crc: uint32) (data: ReadOnlySpan<byte>) : uint32 =
        if System.Runtime.Intrinsics.Arm.Crc32.Arm64.IsSupported then crc32Arm crc data else crc32Software crc data

    /// `Zlib::GzipWriter` writes the header with the given mtime and the Unix OS code.
    let private header (mtime: uint32) : byte[] =
        let h = Array.zeroCreate<byte> 10
        h[0] <- 0x1fuy
        h[1] <- 0x8buy
        h[2] <- 8uy
        BinaryPrimitives.WriteUInt32LittleEndian(Span<byte>(h, 4, 4), mtime)
        h[9] <- 3uy
        h

    /// What zlib writes for a stream that had no input: one empty block, marked final.
    let private emptyDeflate: byte[] = [| 3uy; 0uy |]

    let private trailer (crc: uint32) (size: uint32) : byte[] =
        let t = Array.zeroCreate<byte> 8
        BinaryPrimitives.WriteUInt32LittleEndian(Span<byte>(t, 0, 4), crc)
        BinaryPrimitives.WriteUInt32LittleEndian(Span<byte>(t, 4, 4), size)
        t

    /// What `GzipStream` with `sync: true` sends for a single-buffer body (zlib through the runtime).
    let private zlibMember (body: ReadOnlySpan<byte>) (mtime: uint32) : byte[] =
        use output = new MemoryStream(body.Length / 3 + 64)
        output.Write(header mtime)
        if body.Length = 0 then
            // .NET's `DeflateStream` writes nothing at all for no input; zlib writes one empty final block.
            output.Write(emptyDeflate)
        else
            use deflate = new DeflateStream(output, CompressionLevel.Optimal, true)
            deflate.Write body
            deflate.Flush()
            deflate.Dispose()
        output.Write(trailer (crc32Update 0u body) (uint32 body.Length))
        output.ToArray()

    /// onCrack (unit R2.2): a whole body deflated by libdeflate (the runtime image has it, for libvips), with a compressor
    /// kept per thread: zlib's `deflateInit2` allocates and clears its 256 KB of state for every response, and with the
    /// compression itself that was 30 us of a post's 217 us at c=16. The bytes differ from zlib's (libdeflate parses
    /// differently at the same level, 6, zlib's default and `Rack::Deflater`'s); they inflate to the same body. Off with
    /// `CAMPFIRE_GZIP_LIBDEFLATE=off`, or where the library isn't found.
    [<Sealed; AbstractClass>]
    type private LibDeflate private () =
        static let library: nativeint =
            match Environment.GetEnvironmentVariable "CAMPFIRE_GZIP_LIBDEFLATE" with
            | "off" | "0" | "false" -> 0n
            | _ ->
                let names =
                    if OperatingSystem.IsMacOS() then [ "/opt/homebrew/lib/libdeflate.0.dylib"; "libdeflate.0.dylib" ]
                    else [ "libdeflate.so.0" ]
                names
                |> List.tryPick (fun name ->
                    match NativeLibrary.TryLoad name with
                    | true, handle -> Some handle
                    | _ -> None)
                |> Option.defaultValue 0n

        static let export (name: string) : nativeint =
            if library = 0n then 0n
            else
                match NativeLibrary.TryGetExport(library, name) with
                | true, address -> address
                | _ -> 0n

        static let allocCompressor =
            match export "libdeflate_alloc_compressor" with
            | 0n -> null
            | f -> Marshal.GetDelegateForFunctionPointer<AllocCompressor> f

        static let compress =
            match export "libdeflate_deflate_compress" with
            | 0n -> null
            | f -> Marshal.GetDelegateForFunctionPointer<DeflateCompress> f

        static let bound =
            match export "libdeflate_deflate_compress_bound" with
            | 0n -> null
            | f -> Marshal.GetDelegateForFunctionPointer<CompressBound> f

        [<ThreadStatic; DefaultValue>]
        static val mutable private compressor: nativeint

        static member Available : bool = not (isNull allocCompressor || isNull compress || isNull bound)

        /// `body` deflated (raw, final block) after `headerLength` bytes of room, with `trailerLength` more at the end;
        /// the length written, or none when the bound was wrong.
        static member Deflate(body: ReadOnlySpan<byte>, headerLength: int, trailerLength: int) : struct (byte[] * int) =
            if LibDeflate.compressor = 0n then LibDeflate.compressor <- allocCompressor.Invoke 6
            let c = LibDeflate.compressor
            let room = int (bound.Invoke(c, unativeint body.Length))
            let out = Array.zeroCreate<byte> (headerLength + room + trailerLength)
            use input = fixed body
            use output = fixed &out[headerLength]
            let written = int (compress.Invoke(c, NativePtr.toNativeInt input, unativeint body.Length, NativePtr.toNativeInt output, unativeint room))
            struct (out, written)

    and private AllocCompressor = delegate of int -> nativeint

    and private DeflateCompress = delegate of nativeint * nativeint * unativeint * nativeint * unativeint -> unativeint

    and private CompressBound = delegate of nativeint * unativeint -> unativeint

    /// What `GzipStream` with `sync: true` sends for a single-buffer body, in one piece: a header,
    /// the body deflated and flushed, and the CRC and size. onCrack: deflated by libdeflate where it is (`LibDeflate`).
    let gzipMember (body: ReadOnlySpan<byte>) (mtime: uint32) : byte[] =
        if body.Length > 0 && LibDeflate.Available then
            let struct (out, written) = LibDeflate.Deflate(body, 10, 8)
            if written > 0 then
                let total = 10 + written + 8
                header(mtime).CopyTo(out, 0)
                trailer (crc32Update 0u body) (uint32 body.Length) |> fun t -> t.CopyTo(out, 10 + written)
                if total = out.Length then out else out[0 .. total - 1]
            else
                zlibMember body mtime
        else
            zlibMember body mtime

    /// Gzips a body as it arrives, writing each piece to `output` and flushing it (`GzipStream` with
    /// `sync: true`).
    [<Sealed>]
    type GzipWriter(output: Stream, mtime: uint32) =
        let deflate = new DeflateStream(output, CompressionLevel.Optimal, true)
        let mutable crc = 0u
        let mutable size = 0u
        let mutable started = false
        let mutable wrote = false

        member private _.Start() : Task =
            if started then
                Task.CompletedTask
            else
                started <- true
                output.WriteAsync(header mtime).AsTask()

        member this.Write(chunk: ReadOnlyMemory<byte>) : Task =
            task {
                do! this.Start()
                if chunk.Length > 0 then
                    wrote <- true
                    crc <- crc32Update crc chunk.Span
                    size <- size + uint32 chunk.Length
                    do! deflate.WriteAsync chunk
                    do! deflate.FlushAsync()
            }

        member this.Finish() : Task =
            task {
                do! this.Start()
                if wrote then
                    do! deflate.DisposeAsync().AsTask()
                else
                    do! output.WriteAsync(emptyDeflate).AsTask()
                do! output.WriteAsync(trailer crc size).AsTask()
            }

        interface IAsyncDisposable with
            member _.DisposeAsync() = deflate.DisposeAsync()

    /// Gzip members by body digest and gzip mtime, for the bodies that repeat.
    let private gzipped =
        Generations<struct (BodyDigest * uint32), ReadOnlyMemory<byte>>(
            MaxGzippedBytes,
            (fun _ member' -> member'.Length + CacheCosts.EntryOverhead)
        )

    let private gzippedGate = obj ()

    /// The gzip member kept for a body with this digest and mtime, if there is one.
    let internal keptGzip (digest: BodyDigest) (mtime: uint32) : ReadOnlyMemory<byte> voption =
        lock gzippedGate (fun () -> gzipped.Get(struct (digest, mtime), id))

    /// A body `Rack::ETag` digested (always a single buffer), gzipped once while it keeps repeating.
    let gzipDigested (body: ReadOnlyMemory<byte>) (digest: BodyDigest) (mtime: uint32) : ReadOnlyMemory<byte> =
        match keptGzip digest mtime with
        | ValueSome member' -> member'
        | ValueNone ->
            let member' = ReadOnlyMemory<byte>(gzipMember body.Span mtime)
            // One huge body mustn't push out everything else.
            if member'.Length <= MaxGzippedBytes / 4 then
                lock gzippedGate (fun () -> gzipped.Insert(struct (digest, mtime), member'))
            member'

    // --- the middleware ----------------------------------------------------------------------------

    /// The encodings a client has asked for, as `select_best_encoding` picks among them. Clients send a
    /// handful of distinct `Accept-Encoding` values, so each is worked out once (up to a bound, so that a
    /// client inventing values can't grow it).
    let private choices = System.Collections.Concurrent.ConcurrentDictionary<string, string voption>(StringComparer.Ordinal)

    let private chosenEncoding (acceptEncoding: string | null) : string voption =
        let choose (accept: string) = selectBestEncoding [ "gzip"; "identity" ] (parseAcceptEncoding accept)
        match acceptEncoding with
        | null
        | "" -> ValueSome "identity"
        | accept ->
            match choices.TryGetValue accept with
            | true, choice -> choice
            | _ ->
                let choice = choose accept
                if choices.Count < 512 then choices.TryAdd(accept, choice) |> ignore
                choice

    /// The 406 `Rack::Deflater` answers with for the request to `path` (its path and query).
    let notAcceptable (path: string) : Response =
        let message = $"An acceptable encoding for the requested resource {path} could not be found."
        let replacement = Response(Status.NotAcceptable).ContentType("text/plain").SetBody message
        replacement.Headers.Insert(Hdr.ContentLength, string message.Length)
        replacement

    /// `Rack::Deflater`: decide what to do with `response` for a request with this
    /// `Accept-Encoding`, updating its headers. `appSetLength` is whether the app itself set
    /// `Content-Length` (see `shouldDeflate`).
    let apply (acceptEncoding: string | null) (response: Response) (appSetLength: bool) : Deflated =
        if not (shouldDeflate response appSetLength) then
            Unchanged
        else
            let encoding = chosenEncoding acceptEncoding
            if not (response.Headers.Contains Hdr.Vary) then
                response.Headers.Append(Hdr.Vary, "Accept-Encoding")
            else
                let varyValues =
                    response.Headers.GetAll Hdr.Vary
                    |> List.collect (fun v -> v.Split ',' |> Array.map (fun t -> t.Trim()) |> List.ofArray)
                if not (varyValues |> List.exists (fun v -> v = "*" || v.Equals("accept-encoding", StringComparison.OrdinalIgnoreCase))) then
                    response.Headers.Insert(Hdr.Vary, String.Join(",", varyValues @ [ "Accept-Encoding" ]))
            match encoding with
            | ValueSome "gzip" ->
                let mtime =
                    match response.GetHeader Hdr.LastModified with
                    | null -> 0u
                    | lm ->
                        match KitClock.parseHttpdate lm with
                        | Some t -> uint32 (t.ToUnixTimeSeconds())
                        | None -> 0u
                response.Headers.Insert(Hdr.ContentEncoding, "gzip")
                response.Headers.Remove Hdr.ContentLength
                Gzip mtime
            | ValueSome _ -> Unchanged
            | ValueNone -> NotAcceptable
