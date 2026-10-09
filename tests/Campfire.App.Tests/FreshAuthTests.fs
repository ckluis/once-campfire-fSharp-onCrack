// onCrack R3.2: fresh authorization (`CAMPFIRE_FRESH_AUTH`, `FreshAuth` in src/Campfire.Db/Session.fs, `ReadCache.fs`). Upstream's
// contract re-reads the session and the room membership on every cache hit; onCrack's own design keeps the decision its miss made, under
// the version counters. Both must refuse at once what the database no longer allows. The attacks here go through the app, as a
// person would: a session signed out elsewhere whose cookie is replayed, a membership an administrator removes, a user an administrator
// bans. Each warms the pages it attacks until a cache answers them (the read cache in process, the fast path behind the front server),
// revokes, and checks the very next request, in both modes and both ways of serving. Commits by other connections are
// `ForeignWriteTests`' (which run in both modes too).
module Campfire.App.Tests.FreshAuthTests

open System.Threading
open System.Threading.Tasks
open Xunit
open Campfire.App
open Campfire.App.Tests.Support
open Campfire.Db

let private unwrap (result: Result<'T, DbError>) : 'T =
    match result with
    | Ok value -> value
    | Error e -> failwith (DbError.display e)

let private read (test: Test) (f: Conn -> 'T) : 'T = test.App.Db.ReadBlocking f |> unwrap

/// What served a request from a cache so far: read cache hits and fast path replays.
let private served (test: Test) : int64 =
    let hits, _, _ = ReadCache.stats test.App.Db.Versions
    let replays =
        match test.Host.Front with
        | null -> 0L
        | front ->
            match front.Fast with
            | null -> 0L
            | fast -> Volatile.Read(&fast.Hits)
    hits + replays

/// Gets `path` until a cache answers it, and checks one did (so no test passes because nothing was cached). With fresh authorization,
/// also checks that the answer from a cache ran a fresh check (the count is the process's, so other tests can only add to it).
let private warm (browser: Browser) (path: string) : Task<Reply> =
    task {
        let test = browser.Test
        for _ in 1..4 do
            let! _ = browser.Get path
            ()
        let before = served test
        let checks = Volatile.Read(&FreshAuth.checks.contents)
        let! last = browser.Get path
        Assert.True((last.Status = 200), $"{path}: {last.Status} {last.Location} {last.Text}")
        Assert.True(served test > before, $"{path} was answered from a cache")
        let room = path.StartsWith "/rooms/"
        if test.App.Config.FreshAuth && (room || not (isNull test.Host.Front)) then
            Assert.True(Volatile.Read(&FreshAuth.checks.contents) > checks, $"{path}: the hit ran a fresh check")
        return last
    }

/// Every combination of the two modes and the two ways of serving (in process; behind the front server, whose fast path replays).
let private modes (body: Test -> Task) : Task =
    task {
        for fresh in [ false; true ] do
            for fronted in [ false; true ] do
                use! test = bootSeededWith fronted [ "CAMPFIRE_FRESH_AUTH", (if fresh then "1" else "0") ] "default"
                Assert.Equal(fresh, test.App.Config.FreshAuth)
                do! body test
    }

let private signedOut (reply: Reply) =
    Assert.Equal(302, reply.Status)
    Assert.Contains("/session/new", reply.Location |> Option.defaultValue "")

let private pages = [ $"/rooms/{ALL_TALK}"; $"/rooms/{ALL_TALK}/messages"; "/users/me/sidebar"; "/searches?q=quokka" ]

[<Fact>]
let ``a session signed out elsewhere is refused on the next request, cookie replayed or not`` () =
    modes (fun test ->
        task {
            // Two browsers holding the same session cookie: one keeps reading, the other signs out.
            let reader = david test
            let other = david test
            for path in pages do
                let! _ = warm reader path
                ()
            let sessions = read test (fun conn -> Session.countForUser conn DAVID)
            let! out = other.Form("delete", "/session", [])
            Assert.Equal(302, out.Status)
            Assert.Equal(sessions - 1L, read test (fun conn -> Session.countForUser conn DAVID))
            for path in pages do
                let! reply = reader.Get path
                signedOut reply
        })

[<Fact>]
let ``a membership an administrator removes is refused on the next request`` () =
    modes (fun test ->
        task {
            let jason = browser test "198.51.100.71"
            do! jason.SignIn "jason@37signals.com"
            let room = $"/rooms/{ALL_TALK}"
            let messages = $"/rooms/{ALL_TALK}/messages"
            let! _ = warm jason room
            let! _ = warm jason messages
            let! sidebar = warm jason "/users/me/sidebar"
            Assert.Contains($"/rooms/{ALL_TALK}", sidebar.Text)
            let! updated =
                (david test)
                    .Write(
                        (request "PATCH" $"/rooms/closeds/{ALL_TALK}")
                            .Form(formBody [ "room[name]", "All Talk"; "user_ids[]", string DAVID; "user_ids[]", string BENDER ])
                    )
            Assert.Equal(302, updated.Status)
            Assert.False(read test (fun conn -> FreshAuth.membership conn ALL_TALK JASON))
            let! page = jason.Get room
            Assert.Equal(302, page.Status)
            Assert.DoesNotContain("/session/new", page.Location |> Option.defaultValue "")
            let! listed = jason.Get messages
            Assert.Equal(404, listed.Status)
            let! sidebar = jason.Get "/users/me/sidebar"
            Assert.Equal(200, sidebar.Status)
            Assert.DoesNotContain($"/rooms/{ALL_TALK}\"", sidebar.Text)
        })

[<Fact>]
let ``a user an administrator bans is refused on the next request`` () =
    modes (fun test ->
        task {
            let jason = browser test "198.51.100.72"
            do! jason.SignIn "jason@37signals.com"
            for path in pages do
                let! _ = warm jason path
                ()
            let! banned = (david test).Form("post", $"/users/{JASON}/ban", [])
            Assert.True(banned.Status < 400, $"ban: {banned.Status} {banned.Text}")
            Assert.Equal(Status.Banned, (read test (fun conn -> User.find conn JASON)).Status)
            for path in pages do
                let! reply = jason.Get path
                signedOut reply
        })

[<Fact>]
let ``the fresh check refuses on its own what the database no longer allows`` () =
    // The queries a hit runs, apart from the counters: every revocation makes them false even where a counter would not move.
    task {
        use! test = bootSeeded "default"
        let session = read test (fun conn -> Session.forUser conn DAVID |> List.head)
        let replay token id user room = read test (fun conn -> FreshAuth.replay conn token id user room)
        Assert.True(replay session.Token session.Id DAVID ValueNone)
        Assert.True(replay session.Token session.Id DAVID (ValueSome ALL_TALK))
        Assert.False(replay "not-a-token" session.Id DAVID ValueNone)
        Assert.False(replay session.Token (session.Id + 1L) DAVID ValueNone)
        Assert.False(replay session.Token session.Id JASON ValueNone)
        Assert.False(replay session.Token session.Id DAVID (ValueSome DIRECT_KEVIN_BENDER))
        Assert.True(read test (fun conn -> FreshAuth.membership conn ALL_TALK DAVID))
        Assert.False(read test (fun conn -> FreshAuth.membership conn DIRECT_KEVIN_BENDER DAVID))
        let write (f: Tx -> unit) = test.App.Db.WriteBlocking f |> unwrap
        write (fun tx -> tx.Conn.Execute("""DELETE FROM "rooms" WHERE "id" = ?""", [| I QUIET_CORNER |]) |> ignore)
        Assert.False(read test (fun conn -> FreshAuth.membership conn QUIET_CORNER DAVID))
        write (fun tx -> tx.Conn.Execute("""DELETE FROM "memberships" WHERE "room_id" = ? AND "user_id" = ?""", [| I ALL_TALK; I DAVID |]) |> ignore)
        Assert.False(replay session.Token session.Id DAVID (ValueSome ALL_TALK))
        Assert.True(replay session.Token session.Id DAVID ValueNone)
        write (fun tx -> tx.Conn.Execute("""DELETE FROM "sessions" WHERE "id" = ?""", [| I session.Id |]) |> ignore)
        Assert.False(replay session.Token session.Id DAVID ValueNone)
    }

[<Fact>]
let ``fresh authorization is on by default and off only when asked`` () =
    let config (value: string option) =
        let vars = [ "SECRET_KEY_BASE", "x" ] @ (value |> Option.map (fun v -> [ "CAMPFIRE_FRESH_AUTH", v ]) |> Option.defaultValue [])
        match AppConfig.fromLookup (fun name -> vars |> List.tryFind (fun (k, _) -> k = name) |> Option.map snd |> Option.toObj) with
        | Ok config -> config.FreshAuth
        | Error e -> failwith e
    Assert.True(config None)
    Assert.True(config (Some "1"))
    Assert.True(config (Some "on"))
    Assert.True(config (Some ""))
    Assert.False(config (Some "0"))
    Assert.False(config (Some "off"))
    Assert.False(config (Some " OFF "))
    Assert.False(config (Some "false"))
