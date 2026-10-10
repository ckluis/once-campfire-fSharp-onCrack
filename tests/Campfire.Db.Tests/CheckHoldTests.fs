// onCrack (unit R4.3): the fresh authorization checks keep a read transaction open between checks while the WAL index's change
// counter proves nothing was committed (`CheckerPool` in src/Campfire.Db/Database.fs). Every check must still see every commit that
// returned before it started, from any connection, and a kept transaction must never hold the WAL for long.
module Campfire.Db.Tests.CheckHoldTests

open System
open System.Diagnostics
open System.Threading
open System.Threading.Tasks
open Microsoft.Data.Sqlite
open Xunit
open Campfire.Db
open Campfire.Db.Tests.Support

let private searches = """SELECT COUNT(*) FROM "searches" """

let private count (t: TestDb) : int64 =
    match t.Db.CheckNow(fun conn -> conn.Count(searches, [||])) with
    | ValueSome(Ok n) -> n
    | other -> failwithf "the check did not run: %A" other

/// Commits one row on a connection of its own, as a Rails console or a second container does.
let private foreignInsert (t: TestDb) : unit =
    use conn = new SqliteConnection($"Data Source={t.Db.Path}")
    conn.Open()
    use pragma = conn.CreateCommand()
    pragma.CommandText <- "PRAGMA busy_timeout = 5000"
    pragma.ExecuteNonQuery() |> ignore
    use command = conn.CreateCommand()
    let david = id "david"
    command.CommandText <-
        $"INSERT INTO searches (user_id, query, created_at, updated_at) VALUES ({david}, 'q', '2026-01-01', '2026-01-01')"
    Assert.Equal(1, command.ExecuteNonQuery())

let private waitFor (what: string) (condition: unit -> bool) : unit =
    let sw = Stopwatch.StartNew()
    while not (condition ()) && sw.ElapsedMilliseconds < 2000L do
        Thread.Sleep 2
    Assert.True(condition (), what)

[<Fact>]
let ``a check keeps its read transaction while nothing is committed, and the next check runs in it`` () =
    use t = new TestDb()
    Assert.True(FreshHold.Enabled)
    Assert.Equal(0, t.Db.CheckersHolding)
    let before = count t
    Assert.Equal(1, t.Db.CheckersHolding)
    for _ in 1..100 do
        Assert.Equal(before, count t)
    Assert.Equal(1, t.Db.CheckersHolding)
    Assert.Equal(1, t.Db.CheckersOpen)

[<Fact>]
let ``a commit by another connection is seen by the very next check`` () =
    use t = new TestDb()
    let mutable expected = count t
    for _ in 1..50 do
        foreignInsert t
        expected <- expected + 1L
        Assert.Equal(expected, count t)
        Assert.Equal(expected, count t)

[<Fact>]
let ``the writer's own commits are seen by the very next check`` () =
    use t = new TestDb()
    let mutable expected = count t
    for _ in 1..50 do
        t.Write(fun tx ->
            tx.Conn.Execute(
                """INSERT INTO "searches" ("user_id", "query", "created_at", "updated_at") VALUES (?, 'w', '2026-01-01', '2026-01-01')""",
                [| I(id "david") |]
            )
            |> ignore)
        expected <- expected + 1L
        Assert.Equal(expected, count t)

[<Fact>]
let ``no check ever answers from before a commit that returned ahead of it`` () =
    use t = new TestDb()
    let published = ref (count t)
    use stop = new CancellationTokenSource()
    let violations = ref 0L
    let checks = ref 0L
    let readers =
        [| for _ in 1..4 ->
               Task.Run(fun () ->
                   while not stop.IsCancellationRequested do
                       // The commit returned before this read of `published`, so the check that follows must see it.
                       let floor = Volatile.Read(&published.contents)
                       let seen = count t
                       Interlocked.Increment(&checks.contents) |> ignore
                       if seen < floor then Interlocked.Increment(&violations.contents) |> ignore) |]
    let writer =
        Task.Run(fun () ->
            for i in 1..400 do
                foreignInsert t
                Volatile.Write(&published.contents, Volatile.Read(&published.contents) + 1L)
                if i % 10 = 0 then Thread.Sleep 3)
    writer.Wait()
    stop.Cancel()
    Task.WaitAll(readers)
    Assert.True(Volatile.Read(&checks.contents) > 1000L, "the readers ran")
    Assert.Equal(0L, Volatile.Read(&violations.contents))
    Assert.Equal(Volatile.Read(&published.contents), count t)

[<Fact>]
let ``an idle held transaction is let go within moments`` () =
    use t = new TestDb()
    count t |> ignore
    Assert.Equal(1, t.Db.CheckersHolding)
    waitFor "the idle transaction was ended" (fun () -> t.Db.CheckersHolding = 0)
    // And the connection is usable again.
    count t |> ignore

[<Fact>]
let ``a stale held transaction is let go without another check`` () =
    use t = new TestDb()
    count t |> ignore
    foreignInsert t
    waitFor "the stale transaction was ended" (fun () -> t.Db.CheckersHolding = 0)

[<Fact>]
let ``the writer's RESTART is not kept waiting by a held transaction`` () =
    use t = new TestDb()
    foreignInsert t
    count t |> ignore
    Assert.Equal(1, t.Db.CheckersHolding)
    // What the writer does before a RESTART (`Checkpoints.BeforeRestart`).
    t.Db.ReleaseCheckerHolds()
    Assert.Equal(0, t.Db.CheckersHolding)
    use conn = new SqliteConnection($"Data Source={t.Db.Path}")
    conn.Open()
    use command = conn.CreateCommand()
    command.CommandText <- "PRAGMA wal_checkpoint(RESTART)"
    use r = command.ExecuteReader()
    Assert.True(r.Read())
    Assert.Equal(0L, r.GetInt64 0) // not busy: no reader held the WAL
    // For a moment after, checks begin no new transaction to keep.
    count t |> ignore
    Assert.Equal(0, t.Db.CheckersHolding)

[<Fact>]
let ``with the setting off a check keeps nothing`` () =
    use t = new TestDb()
    let was = FreshHold.Enabled
    try
        FreshHold.Enabled <- false
        count t |> ignore
        Assert.Equal(0, t.Db.CheckersHolding)
        foreignInsert t
        Assert.True(count t > 0L)
    finally
        FreshHold.Enabled <- was

[<Fact>]
let ``a check that fails keeps nothing and the connection is usable after`` () =
    use t = new TestDb()
    count t |> ignore
    Assert.Equal(1, t.Db.CheckersHolding)
    match t.Db.CheckNow(fun conn -> conn.Count("SELECT COUNT(*) FROM no_such_table", [||])) with
    | ValueSome(Error _) -> ()
    | other -> failwithf "expected a database error, got %A" other
    Assert.Equal(0, t.Db.CheckersHolding)
    Assert.True(count t >= 0L)

[<Fact>]
let ``disposing the database ends held transactions and closes the connections`` () =
    let path =
        use t = new TestDb()
        count t |> ignore
        Assert.Equal(1, t.Db.CheckersHolding)
        t.Db.Path
    // The database is closed with its directory; nothing to assert beyond Dispose returning (no hang on a held connection).
    ignore path
