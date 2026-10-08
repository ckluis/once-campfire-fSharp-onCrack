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

module FastCandidate =
    /// The fast path's switch: `CAMPFIRE_FAST_PATH=off` turns it off (on by default).
    let enabled: bool =
        match Environment.GetEnvironmentVariable "CAMPFIRE_FAST_PATH" with
        | null -> true
        | v -> not (v = "0" || v.Equals("off", StringComparison.OrdinalIgnoreCase) || v.Equals("false", StringComparison.OrdinalIgnoreCase))
