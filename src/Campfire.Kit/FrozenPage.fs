// onCrack: a finished page body the read cache keeps between requests (no Rust counterpart).
//
// It answers exactly as the body it froze would: a page in parts (`PageParts`) gets the parts' ETag and
// gzip member, a page in one buffer gets `Rack::ETag`'s SHA-256 of it and the same gzip member the
// adapter would make (`Deflater.gzipMember`). What changes is that each is worked out once: the ETag
// string, and the gzip member for the mtime last asked for (pages without `Last-Modified` always ask
// for 0), so a request for a cached page costs a copy of the stored member and nothing else.
namespace Campfire.Kit

open System
open System.Buffers
open System.Buffers.Binary
open System.Security.Cryptography

[<Sealed; AllowNullLiteral>]
type private GzipMemo(mtime: uint32, bytes: byte[]) =
    member _.Mtime = mtime
    member _.Bytes = bytes

[<Sealed>]
type FrozenPage private (parts: PageParts | null, whole: ReadOnlyMemory<byte>) =
    let length = match parts with null -> whole.Length | parts -> parts.BodyLength
    let mutable etag: string | null = null
    let mutable plain: byte[] | null = null
    let mutable gzip: GzipMemo = null

    /// A page of cached fragments, in parts.
    static member OfParts(parts: PageParts) : FrozenPage = FrozenPage(parts, ReadOnlyMemory<byte>.Empty)

    /// A page in one buffer, which the frozen page owns from now on.
    static member OfBytes(body: ReadOnlyMemory<byte>) : FrozenPage = FrozenPage(null, body)

    member _.BodyLength = length

    /// What the page holds on to: its body, plus the gzip member and plain copy made from it.
    member _.HeldBytes : int =
        length
        + (match gzip with null -> 0 | g -> g.Bytes.Length)
        + (match plain with null -> 0 | p -> p.Length)

    member _.Etag() : string =
        match etag with
        | null ->
            let made =
                match parts with
                | null ->
                    let hash = Array.zeroCreate<byte> 32
                    SHA256.HashData(whole.Span, Span<byte>(hash)) |> ignore
                    Convert.ToHexStringLower(ReadOnlySpan<byte>(hash, 0, 16))
                | parts -> parts.Etag()
            etag <- made
            made
        | known -> known

    member private _.Member(mtime: uint32) : byte[] =
        match gzip with
        | null ->
            let made =
                match parts with
                | null -> Deflater.gzipMember whole.Span mtime
                | parts -> parts.Gzip mtime
            gzip <- GzipMemo(mtime, made)
            made
        | memo when memo.Mtime = mtime -> memo.Bytes
        | memo ->
            // Only the header's mtime differs.
            let copy = Array.copy memo.Bytes
            BinaryPrimitives.WriteUInt32LittleEndian(Span<byte>(copy, 4, 4), mtime)
            gzip <- GzipMemo(mtime, copy)
            copy

    member this.WritePlain(writer: IBufferWriter<byte>) : unit =
        match parts with
        | null -> writer.Write whole.Span
        | parts ->
            match plain with
            | null ->
                let buffer = ArrayBufferWriter<byte>(length)
                parts.WritePlain buffer
                let made = buffer.WrittenSpan.ToArray()
                plain <- made
                writer.Write(ReadOnlySpan<byte> made)
            | made -> writer.Write(ReadOnlySpan<byte> made)

    interface IPageParts with
        member this.BodyLength = this.BodyLength
        member this.Etag() = this.Etag()
        member this.WritePlain writer = this.WritePlain writer
        member this.Gzip mtime = ReadOnlyMemory<byte>(this.Member mtime)
        member this.WriteGzip(writer, mtime) = writer.Write(ReadOnlySpan<byte>(this.Member mtime))
