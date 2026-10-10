// onCrack (round 2 verifier, critical and major): commits by another connection to the same database (a Rails console or a
// rollback to Rails, a second container during a deploy, an admin script, the sqlite3 shell). None of them fires the writer's
// triggers, so before the watch (`Versions.Sync`, src/Campfire.Db/Versions.fs) a revoked session, a removed membership, a
// renamed room or an edited message stayed served from the read cache, the authentication maps, the fast path and the fragment
// store. Each test warms what it attacks until it is served from a cache, edits the database through a second
// `Microsoft.Data.Sqlite` connection, and checks the next request, in process and behind the front server. They mirror upstream
// Rust's `revoked_sessions_and_changed_tokens_cannot_reuse_private_responses`,
// `changed_users_and_room_permissions_are_checked_before_cache_hits`, `foreign_and_local_writers_change_cached_room_content` and
// `timestamp_free_foreign_edits_invalidate_nested_fragments_and_validators`.
module Campfire.App.Tests.ForeignWriteTests

open System
open System.Threading
open System.Threading.Tasks
open Microsoft.Data.Sqlite
open Xunit
open Campfire.App
open Campfire.App.Tests.Support
open Campfire.Db
open Campfire.Kit

let private unwrap (result: Result<'T, DbError>) : 'T =
    match result with
    | Ok value -> value
    | Error e -> failwith (DbError.display e)

let private read (test: Test) (f: Conn -> 'T) : 'T = test.App.Db.ReadBlocking f |> unwrap

/// Runs `sql` on a connection of its own (with `args` as `$1`, `$2`, ...), which commits it.
let private foreign (test: Test) (sql: string) (args: objnull list) : unit =
    use conn = new SqliteConnection($"Data Source={test.App.Db.Path}")
    conn.Open()
    use pragma = conn.CreateCommand()
    pragma.CommandText <- "PRAGMA busy_timeout = 5000"
    pragma.ExecuteNonQuery() |> ignore
    use command = conn.CreateCommand()
    command.CommandText <- sql
    args |> List.iteri (fun i value -> command.Parameters.AddWithValue($"${i + 1}", value) |> ignore)
    command.ExecuteNonQuery() |> ignore

/// A timestamp as Active Record writes one.
let private now () = DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm:ss.ffffff")

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

/// Gets `path` until a cache answers it, and checks one did (so a test can't pass because nothing was cached).
let private warm (browser: Browser) (path: string) : Task<Reply> =
    task {
        let test = browser.Test
        for _ in 1..4 do
            let! _ = browser.Get path
            ()
        let before = served test
        let! last = browser.Get path
        Assert.True((last.Status = 200), $"{path}: {last.Status} {last.Location} {last.Text}")
        Assert.True(served test > before, $"{path} was answered from a cache")
        return last
    }

/// Each test runs in process and behind the front server (whose fast path replays before the app), with fresh authorization
/// (R3.2, the default) and with the cached decision (`CAMPFIRE_FRESH_AUTH=0`).
let private both (body: Test -> Task) : Task =
    task {
        for fresh in [ "1"; "0" ] do
            for fronted in [ false; true ] do
                use! test = bootSeededWith fronted [ "CAMPFIRE_FRESH_AUTH", fresh ] "default"
                do! body test
    }

let private lastMessage (test: Test) (roomId: int64) : Message =
    read test (fun conn -> Message.forRoom conn roomId |> List.sortBy (fun m -> m.CreatedAt.Microsecond, m.Id) |> List.last)

[<Fact>]
let ``revoked sessions and changed tokens cannot reuse private responses`` () =
    both (fun test ->
        task {
            let david = david test
            let room = $"/rooms/{ALL_TALK}"
            let messages = $"/rooms/{ALL_TALK}/messages"
            let! _ = warm david room
            let! _ = warm david messages
            foreign test "DELETE FROM sessions WHERE user_id = $1" [ box DAVID ]
            for path in [ room; messages ] do
                let! reply = david.Get path
                Assert.Equal(302, reply.Status)
                Assert.Contains("/session/new", reply.Location |> Option.defaultValue "")

            let jason = browser test "198.51.100.61"
            do! jason.SignIn "jason@37signals.com"
            let! _ = warm jason room
            foreign test "UPDATE sessions SET token = 'rotated-by-another-connection' WHERE user_id = $1" [ box JASON ]
            let! reply = jason.Get room
            Assert.Equal(302, reply.Status)
        })

[<Fact>]
let ``changed users and room permissions are checked before cache hits`` () =
    both (fun test ->
        task {
            let david = david test
            let room = $"/rooms/{ALL_TALK}"
            let messages = $"/rooms/{ALL_TALK}/messages"
            let creator = (lastMessage test ALL_TALK).CreatorId
            let! _ = warm david room
            foreign test "UPDATE users SET name = 'Renamed Elsewhere' WHERE id = $1" [ box creator ]
            let! page = david.Get room
            Assert.Contains("Renamed Elsewhere", page.Text)

            let! _ = warm david room
            let! _ = warm david messages
            foreign test "DELETE FROM memberships WHERE user_id = $1 AND room_id = $2" [ box DAVID; box ALL_TALK ]
            let! page = david.Get room
            Assert.Equal(302, page.Status)
            let! listed = david.Get messages
            Assert.Equal(404, listed.Status)
        })

[<Fact>]
let ``foreign and local writers change cached room content`` () =
    both (fun test ->
        task {
            let david = david test
            let room = $"/rooms/{ALL_TALK}"
            let! _ = warm david room
            let! _ = warm david "/users/me/sidebar"
            foreign test "UPDATE rooms SET name = 'Lounge Elsewhere' WHERE id = $1" [ box ALL_TALK ]
            let! page = david.Get room
            Assert.Contains("Lounge Elsewhere", page.Text)
            let! sidebar = david.Get "/users/me/sidebar"
            Assert.Contains("Lounge Elsewhere", sidebar.Text)

            // A message written the way a second app process writes one, timestamps and all.
            let! _ = warm david room
            let at = now ()
            use conn = new SqliteConnection($"Data Source={test.App.Db.Path}")
            conn.Open()
            use tx = conn.BeginTransaction()
            let exec (sql: string) (args: objnull list) =
                use command = conn.CreateCommand()
                command.Transaction <- tx
                command.CommandText <- sql
                args |> List.iteri (fun i value -> command.Parameters.AddWithValue($"${i + 1}", value) |> ignore)
                command.ExecuteScalar()
            let id =
                exec
                    "INSERT INTO messages (client_message_id, created_at, creator_id, room_id, updated_at) VALUES ('elsewhere-1', $1, $2, $3, $1) RETURNING id"
                    [ box at; box JASON; box ALL_TALK ]
            exec
                "INSERT INTO action_text_rich_texts (name, body, record_type, record_id, created_at, updated_at) VALUES ('body', '<div>posted elsewhere</div>', 'Message', $1, $2, $2)"
                [ id; box at ]
            |> ignore
            exec "UPDATE rooms SET updated_at = $1 WHERE id = $2" [ box at; box ALL_TALK ] |> ignore
            tx.Commit()
            let! page = david.Get room
            Assert.Contains("posted elsewhere", page.Text)

            // And the app's own writer after it.
            let! _ = warm david room
            let! posted =
                david.Write(
                    ((request "POST" $"/rooms/{ALL_TALK}/messages").With("accept", "text/vnd.turbo-stream.html, text/html, application/xhtml+xml"))
                        .Form(formBody [ "message[body]", "posted here" ])
                )
            Assert.Equal(200, posted.Status)
            let! page = david.Get room
            Assert.Contains("posted elsewhere", page.Text)
            Assert.Contains("posted here", page.Text)
        })

[<Fact>]
let ``timestamp free foreign edits invalidate nested fragments and validators`` () =
    both (fun test ->
        task {
            let david = david test
            let room = $"/rooms/{ALL_TALK}"
            let messages = $"/rooms/{ALL_TALK}/messages"
            let last = lastMessage test ALL_TALK
            let body (text: string) =
                foreign test "UPDATE action_text_rich_texts SET body = $1 WHERE record_type = 'Message' AND record_id = $2" [ box text; box last.Id ]

            let! _ = warm david room
            let! before = warm david messages
            let etag = (before.Header "etag").Value
            body "<div>edited elsewhere</div>"
            let! page = david.Get room
            Assert.Contains("edited elsewhere", page.Text)
            // The old validator no longer matches: the page is sent again, with the edit.
            let! conditional = david.Send((get messages).With("if-none-match", etag))
            Assert.Equal(200, conditional.Status)
            Assert.Contains("edited elsewhere", conditional.Text)

            let! _ = warm david room
            foreign test "UPDATE messages SET creator_id = $1 WHERE id = $2" [ box KEVIN; box last.Id ]
            let kevin = read test (fun conn -> User.find conn KEVIN)
            let! page = david.Get room
            let at = page.Text.IndexOf("edited elsewhere", StringComparison.Ordinal)
            Assert.True(at > 0)
            let start = page.Text.LastIndexOf("<div class=\"message ", at, StringComparison.Ordinal)
            Assert.Contains(kevin.Name, page.Text.Substring(start, at - start))

            let! _ = warm david room
            let at = now ()
            foreign
                test
                "INSERT INTO boosts (booster_id, content, created_at, message_id, updated_at) VALUES ($1, 'boosted elsewhere', $2, $3, $2)"
                [ box JASON; box at; box last.Id ]
            let! page = david.Get room
            Assert.Contains("boosted elsewhere", page.Text)
            let! _ = warm david room
            foreign test "UPDATE boosts SET content = 'reboosted elsewhere' WHERE message_id = $1" [ box last.Id ]
            let! page = david.Get room
            Assert.Contains("reboosted elsewhere", page.Text)

            // Search shows the body as it is now (the index still finds the message by its old words, as in Rails).
            let word =
                read test (fun conn -> conn.QueryRow("SELECT body FROM message_search_index WHERE rowid = ?", [| I last.Id |], fun r -> r.Text 0))
                |> fun text -> text.Split([| ' '; '\n'; '.'; ','; '!'; '?' |], StringSplitOptions.RemoveEmptyEntries)
                |> Array.find (fun w -> w.Length >= 4 && w |> Seq.forall Char.IsAsciiLetter)
            let search = $"/searches?q={word}"
            let! _ = warm david search
            body $"<div>{word} searched elsewhere</div>"
            let! found = david.Get search
            Assert.Contains("searched elsewhere", found.Text)
        })

[<Fact>]
let ``a session revoked by another connection cannot write`` () =
    both (fun test ->
        task {
            let david = david test
            let room = $"/rooms/{ALL_TALK}"
            let! _ = warm david room
            foreign test "DELETE FROM sessions WHERE user_id = $1" [ box DAVID ]
            let! posted =
                david.Write(
                    ((request "POST" $"/rooms/{ALL_TALK}/messages").With("accept", "text/vnd.turbo-stream.html, text/html, application/xhtml+xml"))
                        .Form(formBody [ "message[body]", "written after revocation" ])
                )
            Assert.Equal(302, posted.Status)
            let written =
                read test (fun conn ->
                    conn.QueryRow(
                        "SELECT count(*) FROM action_text_rich_texts WHERE body LIKE '%written after revocation%'",
                        [||],
                        fun r -> r.Int64 0
                    ))
            Assert.Equal(0L, written)
        })

[<Fact>]
let ``the app's own writes never count as another connection's`` () =
    // Each would empty every cache: correct, but the read cache would be worth nothing under writes.
    task {
        use! test = bootSeeded "default"
        let versions = test.App.Db.Versions
        Assert.True(versions.Watching)
        let david = david test
        let! _ = warm david $"/rooms/{ALL_TALK}"
        let epoch = versions.Sync()
        for n in 1..5 do
            let! posted =
                david.Write(
                    ((request "POST" $"/rooms/{ALL_TALK}/messages").With("accept", "text/vnd.turbo-stream.html, text/html, application/xhtml+xml"))
                        .Form(formBody [ "message[body]", $"own post {n}" ])
                )
            Assert.Equal(200, posted.Status)
        let jason = browser test "198.51.100.62"
        do! jason.SignIn "jason@37signals.com"
        let! _ = jason.Form("delete", "/session", [])
        let! _ = warm david $"/rooms/{ALL_TALK}"
        Assert.Equal(epoch, versions.Sync())
    }

/// Round 4 verifier: the commits above come from another connection in this process; Rails is another process (POSIX locks, its own
/// mapping of `-shm`). The sqlite3 shell, a process of its own, revokes and restores David's session (its token) and his membership of
/// All Talk, each right after a cached hit while Jason reads without pause (so the checks' transactions are held), thirty times: every
/// request after a revocation is refused and every request after a restore is served, in both authorization modes, in process and
/// fronted. What makes this hold is `Versions.Sync` (a foreign commit drops every cache, so the next request is a miss), not R4.3's held
/// check transactions: with the hold never renewed (`Prepare` comparing "held at all" instead of the stamp) this test still passes,
/// while `CheckHoldTests` fail; the held checks only answer hits, and a foreign commit leaves none.
[<Fact>]
let ``revocations committed by another process are seen by the next request, every time`` () =
    let shell = [ "/usr/bin/sqlite3"; "/usr/local/bin/sqlite3"; "/opt/homebrew/opt/sqlite/bin/sqlite3" ] |> List.tryFind IO.File.Exists
    match shell with
    | None ->
        Assert.Skip "no sqlite3 shell"
        Task.CompletedTask
    | Some shell ->
    let run (test: Test) (sql: string) =
        let info = Diagnostics.ProcessStartInfo(shell, RedirectStandardError = true, RedirectStandardOutput = true)
        info.ArgumentList.Add "-cmd"
        info.ArgumentList.Add ".timeout 5000"
        info.ArgumentList.Add test.App.Db.Path
        info.ArgumentList.Add sql
        use p = nonNull (Diagnostics.Process.Start info)
        p.WaitForExit()
        Assert.True((p.ExitCode = 0), $"sqlite3: {p.StandardError.ReadToEnd()}")
    both (fun test ->
        task {
            let david = david test
            let room = $"/rooms/{ALL_TALK}"
            let messages = $"/rooms/{ALL_TALK}/messages"
            let! _ = warm david room
            // Jason reads his page without pause, so the checks' connections keep their transactions (a held one is let go after 5 ms idle).
            let jason = browser test "198.51.100.62"
            do! jason.SignIn "jason@37signals.com"
            use stop = new CancellationTokenSource()
            let background =
                Task.Run(fun () ->
                    task {
                        while not stop.IsCancellationRequested do
                            let! _ = jason.Get room
                            ()
                    }
                    :> Task)
            for round in 1..30 do
                let path = if round % 2 = 0 then room else messages
                let! hit = david.Get path
                Assert.Equal(200, hit.Status)
                if round % 3 = 0 then
                    run test $"UPDATE memberships SET room_id = -room_id WHERE user_id = {DAVID} AND room_id = {ALL_TALK}"
                    let! gone = david.Get path
                    Assert.True((gone.Status <> 200), $"round {round}: {path} served after the membership went ({gone.Status})")
                    run test $"UPDATE memberships SET room_id = -room_id WHERE user_id = {DAVID} AND room_id = -{ALL_TALK}"
                else
                    run test $"UPDATE sessions SET token = token || 'x' WHERE user_id = {DAVID}"
                    let! gone = david.Get path
                    Assert.True((gone.Status = 302), $"round {round}: {path} after the session's token changed: {gone.Status}")
                    run test $"UPDATE sessions SET token = substr(token, 1, length(token) - 1) WHERE user_id = {DAVID}"
                let! back = david.Get path
                Assert.True((back.Status = 200), $"round {round}: {path} after the restore: {back.Status} {back.Location}")
            stop.Cancel()
            do! background
        })
