// onCrack: group commit (`Writer` in `src/Campfire.Db/Database.fs`). Writes queued behind one another run in
// one transaction, each in its own savepoint, with one COMMIT, then their after-commit work in one more
// transaction. These tests hold the writer on a blocking write so that the writes queued behind it form one
// group, then try to break what each caller is promised: its own value or its own error, rows that are its
// alone, its after-commit work and events in order and only after the commit, a commit before it hears back,
// and the same database as when every write runs alone.
module Campfire.Db.Tests.GroupCommitTests

open System
open System.Threading
open System.Threading.Tasks
open Xunit
open Campfire.RailsCompat.Clock
open Campfire.Db
open Campfire.Db.Tests.Support

let private await (task: Task<'T>) : 'T =
    if not (task.Wait(TimeSpan.FromSeconds 20.0)) then failwith "timed out after 20 s"
    task.Result

/// Holds the writer on a write until the returned event is set, so that what is queued meanwhile is one group.
let private holdWriter (db: Database) : ManualResetEventSlim * Task<Result<unit, DbError>> =
    let started = new ManualResetEventSlim(false)
    let release = new ManualResetEventSlim(false)
    // On a thread of its own: a write that finds the writer idle runs on its caller's thread (`InlineWrites`).
    let blocker =
        Task.Run<Result<unit, DbError>>(fun () ->
            db.Write(fun _ ->
                started.Set()
                release.Wait()))
    if not (started.Wait(TimeSpan.FromSeconds 10.0)) then failwith "the writer never started the blocking write"
    release, blocker

/// Queues `writes` behind a held writer and lets them go as one group; their results, in order.
let private asOneGroup (db: Database) (writes: (Tx -> 'T) list) : Result<'T, DbError> list =
    let release, blocker = holdWriter db
    let tasks = writes |> List.map db.Write
    release.Set()
    await blocker |> unwrap
    let results = tasks |> List.map await
    Assert.True(db.WriterStats.Largest >= writes.Length, "the writes ran as one group")
    results

let private scratch (t: TestDb) : unit =
    t.Write(fun tx -> tx.Conn.ExecuteBatch "CREATE TABLE scratch (id INTEGER PRIMARY KEY, v TEXT NOT NULL UNIQUE)")

let private insert (tx: Tx) (v: string) : unit =
    tx.Conn.Execute("INSERT INTO scratch (v) VALUES (?)", [| S v |]) |> ignore

let private values (t: TestDb) : string list =
    t.Read(fun c -> c.QueryAll("SELECT v FROM scratch ORDER BY id", [||], fun r -> r.Text 0))

[<Fact>]
let ``queued writes commit as one group, in order, each seeing the ones before it`` () =
    use t = new TestDb(false)
    scratch t
    let groupsBefore = t.Db.WriterStats.Groups
    let results =
        asOneGroup t.Db [ for i in 1..20 -> fun tx -> insert tx $"v{i}"; tx.Conn.Count("SELECT COUNT(*) FROM scratch", [||]) ]
    Assert.Equal<int64 list>([ 1L .. 20L ], results |> List.map unwrap)
    Assert.Equal<string list>([ for i in 1..20 -> $"v{i}" ], values t)
    // The blocking write, then one group of 20.
    Assert.Equal(groupsBefore + 2L, t.Db.WriterStats.Groups)
    Assert.Equal(20, t.Db.WriterStats.Largest)

[<Fact>]
let ``a write that fails in a group rolls back alone and its caller alone gets the error`` () =
    use t = new TestDb(false)
    scratch t
    let results =
        asOneGroup
            t.Db
            [ fun tx -> insert tx "a"
              fun tx ->
                  insert tx "b"
                  insert tx "a" // UNIQUE: fails, and "b" goes with it
              fun tx -> insert tx "c"
              fun tx ->
                  insert tx "d"
                  Err.fail (RecordNotFound "Thing")
              fun tx -> insert tx "e" ]
    match results with
    | [ Ok(); Error(Sqlite _); Ok(); Error(RecordNotFound "Thing"); Ok() ] -> ()
    | other -> failwithf "unexpected results: %A" other
    Assert.Equal<string list>([ "a"; "c"; "e" ], values t)

[<Fact>]
let ``a write that raises a bug gets its exception, and the rest of the group commits`` () =
    use t = new TestDb(false)
    scratch t
    let release, blocker = holdWriter t.Db
    let a = t.Db.Write(fun tx -> insert tx "a")
    let bug =
        t.Db.Write(fun tx ->
            insert tx "bug"
            invalidOp "a bug in the closure")
    let c = t.Db.Write(fun tx -> insert tx "c")
    release.Set()
    await blocker |> unwrap
    await a |> unwrap
    await c |> unwrap
    let e = Assert.Throws<AggregateException>(fun () -> bug.Wait(TimeSpan.FromSeconds 10.0) |> ignore)
    Assert.IsType<InvalidOperationException>(e.InnerException) |> ignore
    Assert.Equal<string list>([ "a"; "c" ], values t)

[<Fact>]
let ``a write that breaks the group's transaction makes the group run again write by write`` () =
    use t = new TestDb(false)
    scratch t
    let groupsBefore = t.Db.WriterStats.Groups
    let runs = ref 0
    let results =
        asOneGroup
            t.Db
            [ fun tx ->
                  Interlocked.Increment runs |> ignore
                  insert tx "a"
              // Ends the transaction under the writer's feet: nothing of the group is committed, so every write runs
              // again alone, and this one fails alone (COMMIT with no transaction).
              fun tx -> tx.Conn.ExecuteBatch "ROLLBACK"
              fun tx -> insert tx "c" ]
    match results with
    | [ Ok(); Error(Sqlite _); Ok() ] -> ()
    | other -> failwithf "unexpected results: %A" other
    // Each committed exactly once, though the first ran twice.
    Assert.Equal<string list>([ "a"; "c" ], values t)
    Assert.Equal(2, runs.Value)
    Assert.Equal(groupsBefore + 2L, t.Db.WriterStats.Groups)

[<Fact>]
let ``after-commit work runs once the group committed, in the writes' order, and its events follow it`` () =
    use t = new TestDb(false)
    scratch t
    t.Write(fun tx -> tx.Conn.ExecuteBatch "CREATE TABLE hooks (id INTEGER PRIMARY KEY, v TEXT NOT NULL)")
    t.Sink.Take() |> ignore
    let path = t.Db.Path
    // What a fresh connection sees from inside each hook: every row of the group is committed by then.
    let seen = Collections.Concurrent.ConcurrentQueue<int64>()
    let write (i: int64) (tx: Tx) =
        insert tx $"v{i}"
        tx.EmitAfterCommit(PushMessage(0L, i))
        tx.AfterCommit(fun tx ->
            use outside = Conn.Open(path, 4)
            seen.Enqueue(outside.Count("SELECT COUNT(*) FROM scratch", [||]))
            tx.Conn.Execute("INSERT INTO hooks (v) VALUES (?)", [| S $"h{i}" |]) |> ignore
            tx.EmitAfterCommit(DeliverWebhook(i, i)))
    let results = asOneGroup t.Db [ for i in 1L..8L -> write i ]
    results |> List.iter unwrap
    Assert.Equal<int64 list>([ for _ in 1..8 -> 8L ], List.ofSeq seen)
    Assert.Equal<string list>(
        [ for i in 1..8 -> $"h{i}" ],
        t.Read(fun c -> c.QueryAll("SELECT v FROM hooks ORDER BY id", [||], fun r -> r.Text 0))
    )
    // Each write's own events in its order: its `EmitAfterCommit`, then what its hook emitted.
    Assert.Equal<Event list>([ for i in 1L..8L do yield PushMessage(0L, i); yield DeliverWebhook(i, i) ], t.Sink.Take())

[<Fact>]
let ``a failing after-commit hook reaches its own caller, after its write committed`` () =
    use t = new TestDb(false)
    scratch t
    let results =
        asOneGroup
            t.Db
            [ fun tx -> insert tx "a"
              fun tx ->
                  insert tx "b"
                  tx.AfterCommit(fun _ -> Err.fail (RecordNotFound "Hook"))
              fun tx -> insert tx "c" ]
    match results with
    | [ Ok(); Error(RecordNotFound "Hook"); Ok() ] -> ()
    | other -> failwithf "unexpected results: %A" other
    // Rails raises the hook's error from the save that committed.
    Assert.Equal<string list>([ "a"; "b"; "c" ], values t)

[<Fact>]
let ``every write is committed before its caller hears back, under concurrent writers`` () =
    use t = new TestDb(false)
    scratch t
    let path = t.Db.Path
    let missing = ref 0
    let writers =
        [ for w in 1..16 ->
              Task.Run(fun () ->
                  task {
                      use outside = Conn.Open(path, 4)
                      for i in 1..40 do
                          let v = $"w{w}-{i}"
                          match! t.Db.Write(fun tx -> insert tx v) with
                          | Ok() ->
                              if outside.Count("SELECT COUNT(*) FROM scratch WHERE v = ?", [| S v |]) <> 1L then
                                  Interlocked.Increment missing |> ignore
                          | Error e -> failwithf "write failed: %A" e
                  }
                  :> Task) ]
    Task.WaitAll(writers |> Array.ofList, TimeSpan.FromSeconds 60.0) |> ignore
    Assert.Equal(0, missing.Value)
    Assert.Equal(640L, t.Read(fun c -> c.Count("SELECT COUNT(*) FROM scratch", [||])))

[<Fact>]
let ``versions marked by a group are even, and moved, when its callers hear back`` () =
    use t = new TestDb()
    let designers = t.Db.Versions.Room(id "designers")
    let pets = t.Db.Versions.Room(id "pets")
    let before = designers.Read(), pets.Read()
    let post (room: string) (tx: Tx) =
        Message.create tx { NewMessage.create (id room) (id "david") with Body = Some "hi" } |> ignore
        designers.Read(), pets.Read()
    let release, blocker = holdWriter t.Db
    let a = t.Db.Write(post "designers")
    let b = t.Db.Write(post "pets")
    release.Set()
    await blocker |> unwrap
    let inA = await a |> unwrap
    let afterA = designers.Read(), pets.Read()
    let _ = await b |> unwrap
    // Odd while in flight (inside the group), even and past the old values once answered.
    Assert.True(fst inA % 2L = 1L)
    Assert.True(fst afterA % 2L = 0L && snd afterA % 2L = 0L)
    Assert.True(fst afterA > fst before && snd afterA > snd before)

/// Everything a post writes or changes, as text, to compare two databases.
let private dump (t: TestDb) : string list =
    t.Read(fun c ->
        [ yield!
              c.QueryAll(
                  "SELECT id, room_id, creator_id, client_message_id, created_at, updated_at FROM messages ORDER BY id",
                  [||],
                  fun r -> $"message {r.Int64 0} {r.Int64 1} {r.Int64 2} {r.Text 3} {r.Text 4} {r.Text 5}"
              )
          yield!
              c.QueryAll(
                  "SELECT id, record_type, record_id, name, body FROM action_text_rich_texts ORDER BY id",
                  [||],
                  fun r -> $"rich {r.Int64 0} {r.Text 1} {r.Int64 2} {r.Text 3} {r.Text 4}"
              )
          yield!
              c.QueryAll(
                  "SELECT id, room_id, user_id, coalesce(unread_at, ''), updated_at FROM memberships ORDER BY id",
                  [||],
                  fun r -> $"membership {r.Int64 0} {r.Int64 1} {r.Int64 2} {r.Text 3} {r.Text 4}"
              )
          yield! c.QueryAll("SELECT id, updated_at FROM rooms ORDER BY id", [||], fun r -> $"room {r.Int64 0} {r.Text 1}")
          yield!
              c.QueryAll("SELECT rowid, body FROM message_search_index ORDER BY rowid", [||], fun r -> $"index {r.Int64 0} {r.Text 1}") ])

[<Fact>]
let ``posts in one group leave the database exactly as posts run one by one`` () =
    let at = (Timestamp.ParseDb "2026-09-26 12:34:56.123456").Value.ToDateTimeOffset()
    let posts =
        [ for i in 1..24 ->
              let room = [| "designers"; "pets"; "watercooler" |][i % 3]
              let creator = [| "david"; "jason"; "jz" |][i % 3]
              { NewMessage.create (id room) (id creator) with
                  ClientMessageId = Some $"client-{i}"
                  Body = Some $"<div>post {i} about coffee {i % 5}</div>" } ]
    let run (groupMax: int) (grouped: bool) =
        let t = new TestDb(false, groupMax)
        t.Clock.TravelTo at
        t.Write(fun tx -> Fixtures.load tx.Conn (Fixtures.referenceDir ()) { Now = tx.Now(); BcryptCost = 4 } |> ignore)
        t.Sink.Take() |> ignore
        let writes = posts |> List.map (fun attributes -> fun tx -> Message.create tx attributes)
        let messages =
            if grouped then
                asOneGroup t.Db writes |> List.map unwrap
            else
                writes |> List.map t.Write
        t, messages
    let alone, aloneMessages = run 1 false
    use alone = alone
    let group, groupMessages = run Config.DefaultGroupMax true
    use group = group
    Assert.Equal<Message list>(aloneMessages, groupMessages)
    let a, g = dump alone, dump group
    let differ = List.zip a g |> List.filter (fun (x, y) -> x <> y) |> List.truncate 6
    Assert.True(differ.IsEmpty && a.Length = g.Length, sprintf "the databases differ: %A" differ)
    Assert.Equal<Event list>(alone.Sink.Take(), group.Sink.Take())
    Assert.Equal(1, alone.Db.WriterStats.Largest)
    Assert.Equal(24, group.Db.WriterStats.Largest)
