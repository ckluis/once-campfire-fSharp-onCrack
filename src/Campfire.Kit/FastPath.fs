// onCrack (unit R2.3): what an action leaves for the front server's fast path (no Rust counterpart).
//
// An action that served a page it may serve again unchanged (the read cache's hit) says so with a `FastCandidate`: the check that
// everything the answer depends on is unchanged (its version counters, the session's), and the time until which its authentication
// stays as it decided (the session's next activity refresh, the read cookies' expiry). The adapter adds the body it sent and the
// cookie jar's verdict; the front server (`FastStore` in `Front/Handler.fs`) keeps the finished response under every byte of the
// request it answered and replays it, before the proxy headers, routing, the kit adapter and the cookie parsing, while the check
// holds. A replay never decides anything: it repeats an answer whose every input is the same request bytes and unchanged state.
namespace Campfire.Kit

open System

[<Sealed>]
type FastCandidate(valid: Func<bool>, notAfterTicks: int64, clock: Campfire.RailsCompat.Clock.Clock) =
    /// Whether every version counter the answer was made under still has its value.
    member _.Valid = valid

    /// The answer may be replayed while `Clock.Now()` is at most this (UTC ticks).
    member val NotAfterTicks = notAfterTicks with get, set

    member _.Clock = clock

    /// The body the adapter sent (the frozen page's gzip member or plain bytes), empty when it wasn't one it can name.
    member val Body = ReadOnlyMemory<byte>.Empty with get, set

    /// The expiry dates, as `Set-Cookie` writes them, of the permanent cookies the answer set (see `CookieJar.PermanentExpiries`).
    member val PermanentExpiries: string[] = Array.empty with get, set

    /// The final headers, a line to each value, taken as they went out (`FrontResponse.Starting`); null until then.
    member val Headers: struct (string * string)[] | null = null with get, set

/// onCrack (round 2 verifier): the budgets of the two response caches, the app's read cache (`Campfire.App.ReadCache`) and the
/// front server's fast path (`FastStore`), in bytes, where 0 turns that cache off. `CAMPFIRE_READ_CACHE_MB` and
/// `CAMPFIRE_FAST_PATH_MB` set each one; upstream's `CAMPFIRE_RESPONSE_CACHE_MB` (one response cache there) sets both when they
/// are not given: 0 turns both off, and N splits N MB as the defaults do (a fifth to the read cache, the rest to the fast path:
/// 80 is 16 and 64). A value that isn't a whole number of MB, or is negative, is ignored. Until this round 0 fell back to the
/// default, so an operator following upstream's guide still had every cache.
module ResponseCacheBudgets =
    [<Literal>]
    let private MB = 1048576L

    let DefaultReadCache = 16L * MB
    let DefaultFastPath = 64L * MB

    /// The read cache's and the fast path's budgets from `setting` (an environment variable's value, or null).
    let resolve (setting: string -> string | null) : struct (int64 * int64) =
        let megabytes (name: string) : int64 voption =
            match setting name with
            | null -> ValueNone
            | value ->
                match Int64.TryParse(value.Trim()) with
                | true, mb when mb >= 0L && mb <= 2047L -> ValueSome(mb * MB)
                | _ -> ValueNone
        let alias = megabytes "CAMPFIRE_RESPONSE_CACHE_MB"
        let read =
            match megabytes "CAMPFIRE_READ_CACHE_MB", alias with
            | ValueSome bytes, _ -> bytes
            | ValueNone, ValueSome total -> total / 5L
            | ValueNone, ValueNone -> DefaultReadCache
        let fast =
            match megabytes "CAMPFIRE_FAST_PATH_MB", alias with
            | ValueSome bytes, _ -> bytes
            | ValueNone, ValueSome total -> total - total / 5L
            | ValueNone, ValueNone -> DefaultFastPath
        struct (read, fast)

    let private fromEnvironment = resolve Environment.GetEnvironmentVariable

    /// The read cache's budget in bytes; 0 is off.
    let readCache: int64 = let struct (read, _) = fromEnvironment in read

    /// The fast path's budget in bytes; 0 is off.
    let fastPath: int64 = let struct (_, fast) = fromEnvironment in fast

module FastCandidate =
    /// The fast path's switch: `CAMPFIRE_FAST_PATH=off` turns it off (on by default), and so does a budget of 0
    /// (`ResponseCacheBudgets`).
    let enabled: bool =
        ResponseCacheBudgets.fastPath > 0L
        && match Environment.GetEnvironmentVariable "CAMPFIRE_FAST_PATH" with
           | null -> true
           | v -> not (v = "0" || v.Equals("off", StringComparison.OrdinalIgnoreCase) || v.Equals("false", StringComparison.OrdinalIgnoreCase))
