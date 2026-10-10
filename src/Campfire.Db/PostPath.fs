// onCrack (unit R2.2): the post path's runtime switches. Each is read where it applies, so `bench/post-micro` can alternate
// variants in one warm process; the server takes them from the environment once, at start-up (`fromEnv`). Every default is the
// shipped behaviour; none of them weakens durability.
namespace Campfire.Db

open System

[<AbstractClass; Sealed>]
type PostPath private () =
    static let env (name: string) (fallback: bool) =
        match Environment.GetEnvironmentVariable name with
        | null -> fallback
        | v -> not (v.Equals("off", StringComparison.OrdinalIgnoreCase) || v = "0" || v.Equals("false", StringComparison.OrdinalIgnoreCase))

    /// Sets the switches from `spec` (`name=on|off`, comma-separated) over their environment defaults; "" restores the defaults.
    static member Apply(spec: string) : unit =
        PostPath.Reset()
        for part in spec.Split(',', StringSplitOptions.RemoveEmptyEntries ||| StringSplitOptions.TrimEntries) do
            match part.Split('=', 2) with
            | [| "group_window_us"; value |] -> PostPath.GroupWindowUs <- int value
            | [| name; value |] ->
                let on = not (value = "off" || value = "0" || value = "false")
                if not (PostPath.Set(name, on)) then failwithf "unknown post path switch %s" name
            | _ -> failwithf "bad post path switch %s" part

    /// `CAMPFIRE_POST_UNREAD_SKIP`: a post into a room that isn't a direct one marks unread only the memberships that
    /// aren't unread yet (`Room.receive`), instead of rewriting every member's row (`Membership.unread?` is all that
    /// reads `unread_at`; a direct room's rows are still all rewritten, for the sidebar fragment keyed by them).
    static member val UnreadSkip = env "CAMPFIRE_POST_UNREAD_SKIP" true with get, set

    /// `CAMPFIRE_POST_ON_COMMIT`: a post's search-index row and unread marks (Rails' `after_create_commit`) commit with
    /// the post, in a savepoint at the end of its transaction (`Tx.OnCommit`), instead of in a transaction of their own
    /// after it: one commit per post (per group under load) instead of two or three.
    static member val OnCommit = env "CAMPFIRE_POST_ON_COMMIT" true with get, set

    /// `CAMPFIRE_WRITE_INLINE`: a write that finds the writer idle with nothing queued runs on the calling thread
    /// (`Database.Write`), instead of a hand-off to the writer thread and another back to the thread pool.
    static member val InlineWrites = env "CAMPFIRE_WRITE_INLINE" true with get, set

    /// `CAMPFIRE_POST_PLAIN_TEXT_EARLY`: a post's search-index text is worked out before the write, in the read that
    /// canonicalizes its body, not by the writer after it.
    static member val PlainTextEarly = env "CAMPFIRE_POST_PLAIN_TEXT_EARLY" true with get, set

    /// `CAMPFIRE_PUSH_INLINE`: the push job's read runs on the job's thread when a reader connection is free (`Database.Read`)
    /// instead of always on a reader thread.
    static member val PushInline = env "CAMPFIRE_PUSH_INLINE" true with get, set

    /// `CAMPFIRE_WAL_DEFER` (onCrack, unit R3.4; off by default): past the WAL's limit the writer restarts it only when that is
    /// cheap (no checkpoint running, a short tail, the disk syncing quickly) and keeps writing otherwise, up to
    /// `Pragmas.WalCeilingPages`; off, it waits for any running checkpoint and restarts at the limit (R2.2). Measured, no gain
    /// that held up at the 160 MB ceiling (`bench/results/oncrack-r3-wal.md`), so it stays an opt-in.
    static member val WalDefer = env "CAMPFIRE_WAL_DEFER" false with get, set

    /// Unit R4.4 (bench switch): the group window in microseconds, over `Config.GroupWindowUs`; -1 keeps the configured one.
    static member val GroupWindowUs = -1 with get, set

    static member Reset() : unit =
        PostPath.GroupWindowUs <- -1
        PostPath.WalDefer <- env "CAMPFIRE_WAL_DEFER" false
        PostPath.PushInline <- env "CAMPFIRE_PUSH_INLINE" true
        PostPath.PlainTextEarly <- env "CAMPFIRE_POST_PLAIN_TEXT_EARLY" true
        PostPath.InlineWrites <- env "CAMPFIRE_WRITE_INLINE" true
        PostPath.UnreadSkip <- env "CAMPFIRE_POST_UNREAD_SKIP" true
        PostPath.OnCommit <- env "CAMPFIRE_POST_ON_COMMIT" true

    static member Set(name: string, on: bool) : bool =
        match name with
        | "unread_skip" -> PostPath.UnreadSkip <- on; true
        | "on_commit" -> PostPath.OnCommit <- on; true
        | "inline_writes" -> PostPath.InlineWrites <- on; true
        | "plain_text_early" -> PostPath.PlainTextEarly <- on; true
        | "push_inline" -> PostPath.PushInline <- on; true
        | "wal_defer" -> PostPath.WalDefer <- on; true
        | _ -> false

/// onCrack (unit R2.2): requests in flight that may write (any method but GET and HEAD), counted by the app's dispatch.
/// `Database.Write` runs a write on its caller's thread only while it is the one such request: under concurrent writers a
/// write that holds the writer connection on a request's thread made the writes queued behind it wait for the writer thread
/// to wake (c=16 posts: 15.6k against 9.8k a second, with 1.8 of 4 cores idle).
[<Sealed>]
type WriteLoad private () =
    [<DefaultValue>]
    val mutable private inFlight: int

    static member val private Counter = WriteLoad()

    static member Enter() : unit = System.Threading.Interlocked.Increment(&WriteLoad.Counter.inFlight) |> ignore

    static member Leave() : unit = System.Threading.Interlocked.Decrement(&WriteLoad.Counter.inFlight) |> ignore

    static member InFlight : int = System.Threading.Volatile.Read(&WriteLoad.Counter.inFlight)
