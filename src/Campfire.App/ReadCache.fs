// onCrack: the versioned read cache (no Rust counterpart; `plans/oncrack.md`, unit C1).
//
// Whole page bodies (the frozen parts with their ETag and gzip member) kept per request shape and per
// user, and served while the versions they were read under (`Campfire.Db.Versions`) are unchanged.
//
// The rule, for every entry:
//
// - **What it depends on** is a list of version counters with the values they had *before* the request
//   that made it ran its first query: the global counter, the user's, and the rooms it read (one for a
//   room or messages page; every room of the user's for the sidebar and search, listed after the
//   user's counter was taken, so a membership added later moves that counter). The first query is
//   authentication's: the page renders the signed-in user as authentication read it (name, avatar,
//   role), so the global counter's value is the one that user was read under (`UserReadAt`), not one
//   taken when the action starts; a page whose user was read any other way is never stored.
// - **It is stored** only if every one of those values was even (no write to them in flight) and still
//   is once the page is finished, and only for a 200 rendered with no flash.
// - **It is served** only while every counter still has its stored value. A write marks its counters
//   odd before it changes a row and even again (one past) after its commit and after-commit work, and
//   before the writer's caller hears back; so a page is never served across a committed change, a
//   writer reads its own write, and a page read during a write is never stored under values a later
//   request can match.
// - **Per user**: the key starts with the signed-in user's id, so a page is never served to anyone else;
//   then everything the page's render reads from the request: the route, the full URL (path and query),
//   scheme, host and port, Turbo-Frame, Referer, User-Agent (the platform) and the `last_room` cookie.
//   Anything else a request differs in, it either doesn't render (headers like X-Request-Id are added on
//   the way out) or answers before the cache is asked (authentication, forgery protection, format).
//
// Bounded: the bodies' bytes (plus their gzip members) in two generations of at most half of
// `CAMPFIRE_READ_CACHE_MB` each (64 MB by default). `CAMPFIRE_READ_CACHE=off` turns it off.
namespace Campfire.App

open System
open System.Threading
open System.Threading.Tasks
open Campfire.Db
open Campfire.Kit

/// A version counter and the value it had when a cached page was read.
[<Struct>]
type Dep = { Cell: VersionCell; Value: int64 }

module Deps =
    /// The counters' values now, or nothing if a write to any of them is in flight.
    let take (cells: VersionCell[]) : Dep[] voption =
        let deps = Array.zeroCreate<Dep> cells.Length
        let mutable even = true
        for i in 0 .. cells.Length - 1 do
            let value = cells[i].Read()
            if value &&& 1L <> 0L then even <- false
            deps[i] <- { Cell = cells[i]; Value = value }
        if even then ValueSome deps else ValueNone

    /// Whether nothing they cover has changed since they were taken.
    let valid (deps: Dep[]) : bool =
        let mutable ok = true
        let mutable i = 0
        while ok && i < deps.Length do
            if deps[i].Cell.Read() <> deps[i].Value then ok <- false
            i <- i + 1
        ok

/// The global counter's value the signed-in user was read under (`ReadCache.user`, during
/// authentication): users are global, so a change to the user committed after this and before the page
/// takes its other counters moved it, and the page must not be kept under the later value.
[<Sealed; AllowNullLiteral>]
type UserReadAt(dep: Dep) =
    member _.Dep = dep

/// What a cache miss's render left behind for the cache to keep: set while the request runs, read when
/// it returns.
[<Sealed; AllowNullLiteral>]
type PageCapture() =
    member val Page: FrozenPage | null = null with get, set
    member val Status = 0 with get, set
    member val Template = Format.Html with get, set
    /// Set when one request rendered more than one body: nothing is kept then.
    member val Spoiled = false with get, set
    /// `fresh_when`'s validators, for a page that sets them (the messages page).
    member val Freshness: Freshness voption = ValueNone with get, set

type CachedPage =
    { Deps: Dep[]
      Page: FrozenPage
      Status: int
      Template: Format
      /// The `Link` header the layout set, if it did.
      Link: string | null
      Freshness: Freshness voption }

module ReadCache =
    let private setting (name: string) : string | null = Environment.GetEnvironmentVariable name

    let enabled: bool =
        match setting "CAMPFIRE_READ_CACHE" with
        | null -> true
        | value -> not (value = "0" || value.Equals("off", StringComparison.OrdinalIgnoreCase) || value.Equals("false", StringComparison.OrdinalIgnoreCase))

    let private budget: int =
        match setting "CAMPFIRE_READ_CACHE_MB" with
        | null -> 64 * 1024 * 1024
        | value ->
            match Int32.TryParse value with
            | true, mb when mb > 0 -> mb * 1024 * 1024
            | _ -> 64 * 1024 * 1024

    /// What an entry costs: its key, its body and what the body will make (a gzip member, a plain copy).
    let private cost (key: string) (entry: CachedPage) : int =
        key.Length * 2 + entry.Page.BodyLength * 2 + entry.Deps.Length * 16 + CacheCosts.EntryOverhead

    /// One app's pages (one per database: tests boot several apps in one process, whose keys are alike).
    [<Sealed>]
    type Store() =
        let gate = obj ()
        let fresh () = Generations<string, CachedPage>(budget, cost, StringComparer.Ordinal)
        let mutable pages = fresh ()
        [<DefaultValue>]
        val mutable Hits: int64
        [<DefaultValue>]
        val mutable Misses: int64
        [<DefaultValue>]
        val mutable Stored: int64

        member _.Lookup(key: string) : CachedPage voption =
            let found = lock gate (fun () -> pages.Get(key, id))
            match found with
            | ValueSome entry when Deps.valid entry.Deps -> found
            | _ -> ValueNone

        member this.Keep(key: string, entry: CachedPage) : unit =
            // A page whose counters moved while it rendered is already out of date: don't let it push out
            // a fresher one a concurrent request kept under the same key.
            if Deps.valid entry.Deps then
                lock gate (fun () -> pages.Insert(key, entry))
                Interlocked.Increment(&this.Stored) |> ignore

        member _.Clear() : unit = lock gate (fun () -> pages <- fresh ())

        /// Sessions by token, under the sessions counter, and users by id, under the global one: what
        /// authentication reads on every request.
        member val Sessions = System.Collections.Concurrent.ConcurrentDictionary<string, struct (Dep[] * Campfire.Db.Session option)>(StringComparer.Ordinal)
        member val Users = System.Collections.Concurrent.ConcurrentDictionary<int64, struct (Dep[] * User option)>()

    let private stores = System.Runtime.CompilerServices.ConditionalWeakTable<Versions, Store>()

    let storeOf (versions: Versions) : Store = stores.GetValue(versions, fun _ -> Store())

    /// Hits, misses and stores of a database's pages since it opened, for tests and logs.
    let stats (versions: Versions) : int64 * int64 * int64 =
        let store = storeOf versions
        Volatile.Read(&store.Hits), Volatile.Read(&store.Misses), Volatile.Read(&store.Stored)

    /// The key: the user first, then everything the page's render reads from the request.
    let requestKey (c: Ctx) (route: string) (userId: int64) : string =
        let request = c.Request
        let nullable (value: string | null) = match value with null -> "" | value -> value
        String.Join(
            '\u0001',
            [| string userId
               route
               (if c.IsTurboFrameRequest then "frame" else "page")
               c.UrlFor ""
               request.Url
               nullable request.Referer
               nullable request.UserAgent
               nullable (c.Cookies.Get "last_room") |]
        )

    /// The versions this database's writer keeps, when they cover every table.
    let versions (c: Ctx) : Versions | null =
        let versions = c.App.Db.Versions
        if enabled && versions.Complete then versions else null

    /// Serves a kept page the way the miss that kept it answered: `fresh_when`'s 304 or validators, the
    /// format check, the layout's `Link` header, then the frozen body.
    let private serve (c: Ctx) (entry: CachedPage) : Result<Response, Error> =
        let fresh =
            match entry.Freshness with
            | ValueSome freshness -> c.FreshWhen freshness
            | ValueNone -> ValueNone
        match fresh with
        | ValueSome notModified -> Ok notModified
        | ValueNone ->
            match c.RespondTo [ entry.Template ] with
            | Error e -> Error e
            | Ok _ ->
                match entry.Link with
                | null -> ()
                | link -> c.SetHeader("link", link)
                Ok(c.RenderParts(entry.Status, entry.Template, entry.Page))

    /// A page through the cache. `missDeps` takes the counters the page depends on, before any of its
    /// queries; `onHit` does what the action does besides rendering (a cookie); `render` is the action.
    let page
        (c: Ctx)
        (route: string)
        (userId: int64)
        (missDeps: unit -> Task<Result<Dep[] voption, Error>>)
        (onHit: unit -> unit)
        (render: unit -> Task<Result<Response, Error>>)
        : Task<Result<Response, Error>> =
        let flash = c.Flash()
        if isNull (versions c) || not (isNull flash.Notice) || not (isNull flash.Alert) then
            render ()
        else
            let key = requestKey c route userId
            let store = storeOf c.App.Db.Versions
            match store.Lookup key with
            | ValueSome entry ->
                Interlocked.Increment(&store.Hits) |> ignore
                onHit ()
                Task.FromResult(serve c entry)
            | ValueNone ->
                Interlocked.Increment(&store.Misses) |> ignore
                task {
                    match! missDeps () with
                    | Error e -> return Error e
                    | Ok deps ->
                        let capture = PageCapture()
                        c.SetCurrent capture
                        let! result = render ()
                        c.TakeCurrent<PageCapture>() |> ignore
                        match result, deps with
                        | Ok response, ValueSome deps when response.Status = 200 && capture.Status = 200 && not capture.Spoiled ->
                            match capture.Page with
                            | null -> ()
                            | frozen ->
                                store.Keep(
                                    key,
                                    { Deps = deps
                                      Page = frozen
                                      Status = capture.Status
                                      Template = capture.Template
                                      Link = c.Headers.Get "link"
                                      Freshness = capture.Freshness }
                                )
                        | _ -> ()
                        return result
                }

    /// `cells`' values now after the global counter's value when authentication read the signed-in user,
    /// or nothing (render, don't keep) when it wasn't read through `user` or a write was in flight.
    let private afterUser (c: Ctx) (cells: VersionCell[]) : Dep[] voption =
        match c.Current<UserReadAt>() with
        | ValueNone -> ValueNone
        | ValueSome at ->
            match Deps.take cells with
            | ValueNone -> ValueNone
            | ValueSome rest ->
                let deps = Array.zeroCreate<Dep> (rest.Length + 1)
                deps[0] <- at.Dep
                Array.blit rest 0 deps 1 rest.Length
                ValueSome deps

    /// The counters of a page about one room: the global one (as the user was read under), the user's and
    /// the room's.
    let roomDeps (c: Ctx) (userId: int64) (roomId: int64) : unit -> Task<Result<Dep[] voption, Error>> =
        fun () ->
            let v = c.App.Db.Versions
            Task.FromResult(Ok(afterUser c [| v.User userId; v.Room roomId |]))

    /// The counters of a page about all of a user's rooms: the global one (as the user was read under) and
    /// the user's, taken first, then the rooms the user is a member of now (a membership added after that
    /// moves the user's).
    let userRoomsDeps (c: Ctx) (userId: int64) : unit -> Task<Result<Dep[] voption, Error>> =
        fun () ->
            task {
                let v = c.App.Db.Versions
                match afterUser c [| v.User userId |] with
                | ValueNone -> return Ok ValueNone
                | ValueSome first ->
                    match!
                        c.App.Read(fun conn ->
                            conn.QueryAll(
                                """SELECT "memberships"."room_id" FROM "memberships" WHERE "memberships"."user_id" = ?""",
                                [| I userId |],
                                fun r -> r.Int64 0
                            ))
                    with
                    | Error e -> return Error e
                    | Ok roomIds ->
                        match Deps.take (roomIds |> List.map v.Room |> Array.ofList) with
                        | ValueNone -> return Ok ValueNone
                        | ValueSome rooms -> return Ok(ValueSome(Array.append first rooms))
            }

    /// Bound on the sessions and users kept for authentication: past it, they start again.
    [<Literal>]
    let private MaxAuthEntries = 50_000

    /// A read through one of the authentication maps: served while its counter is unchanged, read and kept
    /// (when the counter was even before the read) otherwise. `readAt` hears the counter's value the value
    /// served is as of (none for a read during a write).
    let private through
        (map: System.Collections.Concurrent.ConcurrentDictionary<'K, struct (Dep[] * 'V)>)
        (key: 'K)
        (cell: VersionCell)
        (readAt: Dep -> unit)
        (load: unit -> Task<Result<'V, Error>>)
        : Task<Result<'V, Error>> =
        match map.TryGetValue key with
        | true, struct (deps, value) when Deps.valid deps ->
            readAt deps[0]
            Task.FromResult(Ok value)
        | _ ->
            task {
                let deps = Deps.take [| cell |]
                let! result = load ()
                match result, deps with
                | Ok value, ValueSome deps when Deps.valid deps ->
                    readAt deps[0]
                    if map.Count >= MaxAuthEntries then map.Clear()
                    map[key] <- struct (deps, value)
                | _ -> ()
                return result
            }

    /// `Session.find_by(token:)`, through the cache (the sessions counter covers every session row).
    let session (c: Ctx) (token: string) (load: unit -> Task<Result<Campfire.Db.Session option, Error>>) : Task<Result<Campfire.Db.Session option, Error>> =
        match versions c with
        | null -> load ()
        | v -> through (storeOf v).Sessions token v.Sessions ignore load

    /// `User.find_by(id:)`, through the cache (users are global). The request remembers the global counter's
    /// value the user is as of (`UserReadAt`), which the pages it renders depend on.
    let user (c: Ctx) (id: int64) (load: unit -> Task<Result<User option, Error>>) : Task<Result<User option, Error>> =
        match versions c with
        | null -> load ()
        | v -> through (storeOf v).Users id v.Global (fun dep -> c.SetCurrent(UserReadAt dep)) load
