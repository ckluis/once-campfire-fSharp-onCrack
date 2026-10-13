// onCrack: tests for the round 2 verifier's findings in the kit. Each would have caught its finding.
module Campfire.Kit.Tests.VerifierRound2Tests

open System
open Xunit
open Campfire.Kit

[<Fact>]
let ``an upper case Q refuses an encoding as a lower case one does`` () =
    // RFC 9110: parameter names are case-insensitive. Thruster, Rack 3 and Rust ccece30 read `gzip;Q=0` as q=1.
    let front = FrontCompression.selectEncoding "GET"
    Assert.Equal(Encoding.NoEncoding, front "gzip;Q=0")
    Assert.Equal(Encoding.NoEncoding, front "gzip;q=0")
    Assert.Equal(Encoding.Gzip, front "gzip;Q=0.5")
    Assert.Equal(Encoding.Gzip, front "zstd;Q=0, gzip")
    let rack (header: string) = Deflater.selectBestEncoding [ "gzip"; "identity" ] (Deflater.parseAcceptEncoding header)
    Assert.Equal(ValueSome "identity", rack "gzip;Q=0")
    Assert.Equal(ValueSome "identity", rack "gzip;q=0")
    Assert.Equal(ValueSome "gzip", rack "gzip;Q=1")
    Assert.Equal<(string * float) list>([ "gzip", 0.0; "identity", 0.5 ], Deflater.parseAcceptEncoding "gzip;Q=0, identity;Q=0.5")

[<Fact>]
let ``a response cache budget of 0 turns that cache off and upstream's setting is an alias`` () =
    let mb = 1048576L
    let resolve (settings: (string * string) list) =
        ResponseCacheBudgets.resolve (fun name ->
            match List.tryFind (fun (n, _) -> n = name) settings with
            | Some(_, v) -> v
            | None -> null)
    let pair (settings: (string * string) list) =
        let struct (read, fast) = resolve settings
        read, fast
    Assert.Equal((16L * mb, 64L * mb), pair [])
    Assert.Equal((0L, 64L * mb), pair [ "CAMPFIRE_READ_CACHE_MB", "0" ])
    Assert.Equal((16L * mb, 0L), pair [ "CAMPFIRE_FAST_PATH_MB", "0" ])
    Assert.Equal((0L, 0L), pair [ "CAMPFIRE_RESPONSE_CACHE_MB", "0" ])
    Assert.Equal((16L * mb, 64L * mb), pair [ "CAMPFIRE_RESPONSE_CACHE_MB", "80" ])
    Assert.Equal((2L * mb, 8L * mb), pair [ "CAMPFIRE_RESPONSE_CACHE_MB", "10" ])
    // The specific settings win over the alias.
    Assert.Equal((16L * mb, 10L * mb), pair [ "CAMPFIRE_RESPONSE_CACHE_MB", "80"; "CAMPFIRE_FAST_PATH_MB", "10" ])
    Assert.Equal((0L, 0L), pair [ "CAMPFIRE_RESPONSE_CACHE_MB", "80"; "CAMPFIRE_READ_CACHE_MB", "0"; "CAMPFIRE_FAST_PATH_MB", "0" ])
    // Nonsense is ignored, as before.
    Assert.Equal((16L * mb, 64L * mb), pair [ "CAMPFIRE_READ_CACHE_MB", "lots"; "CAMPFIRE_FAST_PATH_MB", "-1" ])

/// Marks `n` distinct long targets and returns weak references to them (made here, so nothing on the caller's stack keeps them).
[<System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)>]
let private flood (store: FastStore) (pad: string) (n: int) : WeakReference[] =
    [| for i in 1..n ->
           let target = String.Concat("/rooms/486777696?i=", string i, "&pad=", pad)
           store.Mark target
           WeakReference(target) |]

[<Fact>]
let ``a flood of distinct long targets does not grow the fast path's memory`` () =
    // One signed-in user, every URL distinct and near Kestrel's 8 KB request line: the set of offered targets kept each one
    // as a string (about 14 KB a URL, 1.4 GB by its 100,000 bound). Now it keeps none of them, whatever their length.
    let store = FastStore(64 * 1024 * 1024)
    let pad = String('x', 7000)
    let targets = flood store pad 20_000
    GC.Collect()
    GC.WaitForPendingFinalizers()
    GC.Collect()
    let alive = targets |> Array.filter (fun t -> t.IsAlive) |> Array.length
    Assert.Equal(0, alive)
    // 32-bit hashes: two of 20,000 targets share one about one run in twenty (it only costs the second a key built for nothing).
    Assert.InRange(store.MarkedTargets, 19_990, 20_000)
    Assert.True(store.Knows(String.Concat("/rooms/486777696?i=", "17", "&pad=", pad)))
    Assert.False(store.Knows(String.Concat("/rooms/486777696?i=", "0", "&pad=", pad)))
