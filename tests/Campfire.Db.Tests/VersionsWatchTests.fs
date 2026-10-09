// onCrack (round 2 verifier, critical): the versions' watch for commits by other connections (`Versions.Sync`,
// `Versions.Committing`, `WalChangeCounter` in src/Campfire.Db/Versions.fs). A foreign connection here is a second
// `Microsoft.Data.Sqlite` connection to the same file, as a Rails console, a second container or the sqlite3 shell is.
module Campfire.Db.Tests.VersionsWatchTests

open System
open Microsoft.Data.Sqlite
open Xunit
open Campfire.RailsCompat.Clock
open Campfire.Db
open Campfire.Db.Tests.Support

/// Runs `sql` on a connection of its own, which commits it.
let private foreign (t: TestDb) (sql: string) : unit =
    use conn = new SqliteConnection($"Data Source={t.Db.Path}")
    conn.Open()
    use pragma = conn.CreateCommand()
    pragma.CommandText <- "PRAGMA busy_timeout = 5000"
    pragma.ExecuteNonQuery() |> ignore
    use command = conn.CreateCommand()
    command.CommandText <- sql
    Assert.Equal(1, command.ExecuteNonQuery())

let private counter (t: TestDb) : WalChangeCounter =
    match WalChangeCounter.Open t.Db.Path with
    | null -> failwith "no WAL index"
    | c -> c

[<Fact>]
let ``the wal index counter moves once per commit that writes and for nothing else`` () =
    use t = new TestDb()
    use c = counter t
    use conn = new SqliteConnection($"Data Source={t.Db.Path}")
    conn.Open()
    let run (sql: string) =
        use command = conn.CreateCommand()
        command.CommandText <- sql
        command.ExecuteNonQuery() |> ignore
    let david = id "david"
    let start = c.Read()
    run $"INSERT INTO searches (user_id, query, created_at, updated_at) VALUES ({david}, 'a', '2026-01-01', '2026-01-01')"
    Assert.Equal(start + 1u, c.Read())
    run "BEGIN IMMEDIATE; COMMIT"
    Assert.Equal(start + 1u, c.Read())
    run "BEGIN IMMEDIATE; DELETE FROM searches; ROLLBACK"
    Assert.Equal(start + 1u, c.Read())
    run "PRAGMA wal_checkpoint(PASSIVE)"
    run "PRAGMA wal_checkpoint(RESTART)"
    Assert.Equal(start + 1u, c.Read())
    run "CREATE TEMP TABLE scratch (x); INSERT INTO scratch VALUES (1)"
    Assert.Equal(start + 1u, c.Read())
    run $"BEGIN IMMEDIATE; DELETE FROM searches; INSERT INTO searches (user_id, query, created_at, updated_at) VALUES ({david}, 'b', '2026-01-01', '2026-01-01'); COMMIT"
    Assert.Equal(start + 2u, c.Read())

[<Fact>]
let ``the writer's own commits never count as another connection's`` () =
    use t = new TestDb()
    let v = t.Db.Versions
    Assert.True(v.Watching)
    let epoch = v.Sync()
    for n in 1..5 do
        t.Write(fun tx -> Search.record tx (id "david") $"q{n}" |> ignore)
    t.Write(fun tx -> Message.create tx { NewMessage.create (id "hq") (id "david") with Body = Some "<div>own</div>" } |> ignore)
    t.Write(fun _ -> ())
    Assert.Equal(epoch, v.Sync())

[<Fact>]
let ``a commit by another connection moves every counter and the epoch, keeping their parity`` () =
    use t = new TestDb()
    let v = t.Db.Versions
    let cells = [ v.Global; v.Sessions; v.Room(id "hq"); v.User(id "david") ]
    let epoch = v.Sync()
    let before = cells |> List.map (fun c -> c.Read())
    let hq = id "hq"
    foreign t $"UPDATE rooms SET name = 'Elsewhere' WHERE id = {hq}"
    Assert.Equal(epoch + 1L, v.Sync())
    let after = cells |> List.map (fun c -> c.Read())
    for b, a in List.zip before after do
        Assert.Equal(b + 2L, a)
    // Accounted for once: no second move without another commit.
    Assert.Equal(epoch + 1L, v.Sync())
    Assert.Equal<int64 list>(after, cells |> List.map (fun c -> c.Read()))

[<Fact>]
let ``a commit by another connection between two of the writer's is never absorbed by the second`` () =
    // Nobody syncs between the foreign commit and the writer's next one: the writer must see it itself (its connection's
    // data_version), or it would make the counter's value after its own commit the accepted one and hide the foreign one.
    use t = new TestDb()
    let v = t.Db.Versions
    let epoch = v.Sync()
    t.Write(fun tx -> Search.record tx (id "david") "before" |> ignore)
    let jason = id "jason"
    foreign t $"UPDATE users SET name = 'Elsewhere' WHERE id = {jason}"
    t.Write(fun tx -> Search.record tx (id "david") "after" |> ignore)
    Assert.Equal(epoch + 1L, v.Sync())

[<Fact>]
let ``a database with no wal index to watch is never cached`` () =
    use conn = Conn.OpenInMemory()
    Schema.prepare conn "test" (SystemClock()) |> ignore
    let v = Versions()
    Versions.install conn v
    Assert.False(v.Watching)
    Assert.False(v.Complete)
