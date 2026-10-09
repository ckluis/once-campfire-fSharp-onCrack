// Port of rust/crates/db/src/database.rs
//
// One writer thread that owns the write connection and takes a bounded queue of work, plus
// reader threads that take reads from one queue, each with a free reader connection. Each write
// runs in `BEGIN IMMEDIATE` (`default_transaction_mode: immediate` in
// `reference/config/database.yml`), then its after-commit work runs in order, outside the
// transaction, the way Active Record runs `after_commit` callbacks.
//
// Reads run on their own threads rather than the thread pool, where a read that found every
// connection busy would park a pool thread until one came free. Here a waiting read costs a
// queue entry, reads leave the queue in the order they were queued (with several readers, two
// reads taken one after the other may still start in either order), and a reader that finishes
// a read takes the next one without a hand-off to another thread.
//
// A read that finds a connection free, with no read queued ahead of it, skips the queue and runs
// on the calling task's thread instead (see `Database.Read`).
//
// WAL checkpoints run on a checkpointer thread with a connection of its own, not on the writer.
// Rails keeps SQLite's auto-checkpoint: once a commit leaves the WAL at 1,000 pages or more,
// that commit checkpoints (PASSIVE) before returning, fsyncing the WAL and then the database
// (with the WAL header's fsync when the next write restarts the WAL, ~12 ms here, every ~64
// message posts), and every write queued behind it waits. Here the writer's commits only note
// the WAL's size, and every 1,000 pages it grows wake the checkpointer, which runs the same
// PASSIVE checkpoint while writes carry on appending to the WAL. (Rust notes the size in
// `sqlite3_wal_hook`, which the .NET bindings don't expose. The writer connection has SQLite's
// auto-checkpoint turned off, and the writer asks `PRAGMA wal_checkpoint(NOOP)`, which does no
// checkpointing and takes no locks, for the size after each commit.)
//
// Durability is the same as Rails': `journal_mode=wal` with `synchronous=normal`, so a commit
// doesn't fsync, and what was committed since the WAL was last synced can be lost to a power
// failure (never to a crash of the process); every checkpoint syncs the WAL, and one runs for
// every 1,000 pages written, as in Rails.
//
// The trade-off is WAL size. SQLite only restarts the WAL from its beginning once a checkpoint
// has caught up with it entirely, which a background checkpoint never does while writes keep
// coming. So the WAL grows past 1,000 pages under sustained writes (it restarts in the first
// lull), and at `WalLimitPages` (~40 MB) the writer checkpoints it itself with RESTART,
// stalling writes as Rails' commits do, but once per 10,000 pages instead of per 1,000.
//
// Errors: a model raises `DbException` (or SQLite raises `SqliteException`) where Rust returns
// `Err` (a stored value a `Row` accessor can't read, such as a NULL or a datetime that doesn't parse,
// raises `DbException` too, as rusqlite's `row.get` returns `Err` for it), and the `Database` methods return it as a `Result` at the boundary. Any other exception
// is a bug in the closure: the write rolls back, and the exception reaches the caller.
namespace Campfire.Db

open System
open System.Collections.Generic
open System.Runtime.ExceptionServices
open System.Threading
open System.Threading.Tasks
open Campfire.RailsCompat.Clock

/// Everything models need besides the connection: the clock, where side effects go, and
/// the Action Text adapter.
type Env =
    { Clock: SharedClock
      Sink: EventSink
      RichText: RichText
      /// BCrypt cost for `has_secure_password`. Rails uses `BCrypt::Engine.cost` (12), or
      /// `MIN_COST` (4) in the test environment.
      BcryptCost: int }

    /// `Time.current`, at the microseconds a `datetime(6)` column keeps.
    member this.Now() : Timestamp = Timestamp.FromDateTimeOffset(this.Clock.Now())

module internal Log =
    let error (message: string) : unit = eprintfn "ERROR campfire_db: %s" message
    let warn (message: string) : unit = eprintfn "WARN campfire_db: %s" message

/// A write in progress: the writer connection inside a transaction (or, while after-commit
/// work runs, outside one), the environment, and the queued after-commit work.
[<NoComparison; NoEquality>]
type Tx internal (conn: Conn, env: Env, inTransaction: bool, deferred: ResizeArray<Event> option) =
    let queue = ResizeArray<AfterCommitItem>()
    let onCommit = ResizeArray<Tx -> unit>(0)

    internal new(conn: Conn, env: Env, inTransaction: bool) = Tx(conn, env, inTransaction, None)

    member _.Conn : Conn = conn

    member _.Env : Env = env

    /// `Time.current`
    member _.Now() : Timestamp = env.Now()

    member _.RichText : RichText = env.RichText

    /// Emits an event right away, even though the transaction may still roll back, for the
    /// side effects Rails performs mid-transaction.
    member _.EmitNow(event: Event) : unit = env.Sink.Emit event

    /// Emits an event once the transaction commits (`after_commit`), or right away when
    /// already running after commit.
    /// onCrack: after-commit work of a group commit runs in one transaction after the group's, and its
    /// events wait for that transaction's commit (`deferred`), so a job they start reads what they follow.
    member _.EmitAfterCommit(event: Event) : unit =
        if inTransaction then
            queue.Add(AfterCommitItem.Emit event)
        else
            match deferred with
            | Some events -> events.Add event
            | None -> env.Sink.Emit event

    /// Queues database work to run after commit, in its own implicit transaction.
    member this.AfterCommit(hook: Tx -> unit) : unit =
        if inTransaction then
            queue.Add(AfterCommitItem.Hook hook)
        else
            let tx = Tx(conn, env, false, deferred)
            try
                hook tx
            with e ->
                Log.error $"after_commit hook failed: {e.Message}"

    /// onCrack (unit R2.2): an effect outside the database (no SQL) once the transaction commits, in order with
    /// the after-commit hooks and events; right away when already running after commit. A group whose after-commit
    /// work is only effects and events runs it without opening a transaction for it.
    member _.AfterCommitEffect(effect: unit -> unit) : unit =
        if inTransaction then
            queue.Add(AfterCommitItem.Effect effect)
        else
            try
                effect ()
            with e ->
                Log.error $"after_commit hook failed: {e.Message}"

    /// onCrack (unit R2.2): database work that Rails runs in an `after_commit` callback, run here at the end of the
    /// write's own transaction instead (after the write's statements; in a group, after every write of the group, in
    /// their order), so that the write and its after-commit work commit once (`PostPath.OnCommit`; otherwise, and
    /// outside a transaction, it is `AfterCommit`). A statement of it that fails rolls back alone, as Rails' autocommitted
    /// one would, and its error reaches the caller after the write committed, as Rails raises it from the save that
    /// committed. Its events and after-commit work still wait for the commit. Only for hooks that do database work
    /// alone: they may run again if their group's transaction breaks.
    member this.OnCommit(hook: Tx -> unit) : unit =
        if inTransaction && PostPath.OnCommit then
            onCommit.Add hook
        else
            this.AfterCommit hook

    member _.InTransaction : bool = inTransaction

    /// Runs the `OnCommit` hooks (and any they add) in the transaction, before its commit; `failed` hears each one's
    /// error. No savepoint: a statement that fails rolls back alone, as an autocommitted one would (and a savepoint makes
    /// the FTS5 index flush its pending rows into a segment of their own, one per post). An error that took the
    /// transaction with it is raised: the write fails (its group runs again write by write).
    member internal this.RunOnCommit(failed: exn -> unit) : unit =
        let mutable i = 0
        while i < onCommit.Count do
            let hook = onCommit[i]
            i <- i + 1
            try
                hook this
            with e ->
                if conn.IsAutocommit then reraise ()
                Log.error $"after_commit hook failed: {e.Message}"
                failed e
        onCommit.Clear()

    member internal _.TakeAfterCommit() : AfterCommitItem list =
        let items = List.ofSeq queue
        queue.Clear()
        items

/// What a write leaves to run after its commit.
and [<NoComparison; NoEquality>] internal AfterCommitItem =
    | Hook of (Tx -> unit)
    | Effect of (unit -> unit)
    | Emit of Event

module DbRun =
    /// What a read or write may raise on purpose, as a `Result`: the `DbError` it stands for. Any other
    /// exception is a bug in the closure and goes on.
    let internal attempt (f: unit -> 'T) : Result<'T, DbError> =
        try
            Ok(f ())
        with
        | DbException e -> Error e
        | :? Microsoft.Data.Sqlite.SqliteException as e -> Error(Sqlite e)

    /// onCrack: runs `f`, which may commit (a `COMMIT`, or autocommitted statements), through the versions' watch for other
    /// connections' commits (`Versions.Committing`), so that the read cache tells the writer's commits from theirs.
    let committing (conn: Conn) (f: unit -> unit) : unit =
        match conn.Marks with
        | null -> f ()
        | marks -> marks.Committing f

    /// Runs `f` in `BEGIN IMMEDIATE`, commits, then runs the after-commit queue. An error from
    /// `f`, an exception in it, or a failed commit rolls back and discards the queue. An error from
    /// an after-commit hook is raised after the rest of the queue has run (Rails raises it from the
    /// save that committed).
    let runWrite (conn: Conn) (env: Env) (f: Tx -> 'T) : 'T =
        conn.Execute("BEGIN IMMEDIATE", [||]) |> ignore
        let tx = Tx(conn, env, true)
        let mutable onCommitError: exn option = None
        let value =
            try
                let value = f tx
                tx.RunOnCommit(fun e -> if onCommitError.IsNone then onCommitError <- Some e)
                committing conn (fun () -> conn.Execute("COMMIT", [||]) |> ignore)
                value
            with _ ->
                if not conn.IsAutocommit then
                    try
                        conn.Execute("ROLLBACK", [||]) |> ignore
                    with _ ->
                        ()
                reraise ()

        let after = Tx(conn, env, false)
        let mutable firstError: exn option = onCommitError
        for item in tx.TakeAfterCommit() do
            match item with
            | AfterCommitItem.Emit event -> env.Sink.Emit event
            | AfterCommitItem.Effect effect ->
                try
                    effect ()
                with e ->
                    Log.error $"after_commit hook failed: {e.Message}"
                    if firstError.IsNone then firstError <- Some e
            | AfterCommitItem.Hook hook ->
                try
                    committing conn (fun () -> hook after)
                with e ->
                    Log.error $"after_commit hook failed: {e.Message}"
                    if firstError.IsNone then firstError <- Some e
        match firstError with
        | Some e -> ExceptionDispatchInfo.Capture(e).Throw()
        | None -> ()
        value

type Config =
    { Path: string
      Readers: int
      /// Bound on queued writes; senders wait when it's full.
      WriteQueue: int
      /// Load the schema into an empty database (`db:prepare`).
      Prepare: bool
      /// `ar_internal_metadata.environment` when preparing.
      Environment: string
      /// onCrack, group commit: the most writes the writer runs in one transaction (`Writer.runGroup`);
      /// 1 runs every write alone, as the port does.
      GroupMax: int
      /// onCrack: how long (microseconds) the writer waits for more writes to join a group that isn't full.
      /// 0 (the default) never waits: a group is what was already queued.
      GroupWindowUs: int
      /// onCrack (unit R2.2): a write that finds the writer idle and nothing queued runs on the calling thread
      /// (`Database.Write`), with no hand-off to the writer thread and back (`PostPath.InlineWrites` too).
      InlineWrites: bool }

module Config =
    [<Literal>]
    let DefaultGroupMax = 64

    let create (path: string) : Config =
        { Path = path
          Readers = 8
          WriteQueue = 256
          Prepare = true
          Environment = "production"
          GroupMax = DefaultGroupMax
          GroupWindowUs = 0
          InlineWrites = true }

module internal Pragmas =
    /// Prepared statements each connection keeps. A page like the room show runs more than 16.
    [<Literal>]
    let StatementCacheCapacity = 256

    /// SQLite's default `wal_autocheckpoint`, which Rails keeps: a checkpoint per 1,000 WAL pages.
    [<Literal>]
    let AutocheckpointPages = 1000

    /// The WAL size at which the writer checkpoints and restarts the WAL itself, because writes never
    /// paused long enough for a background checkpoint to catch up. Below `journal_size_limit`.
    [<Literal>]
    let WalLimitPages = 10_000

    let openConnection (path: string) (reader: bool) : Conn =
        let conn = Conn.Open(path, StatementCacheCapacity)
        try
            Schema.configureConnection conn
            if reader then conn.ExecuteBatch "PRAGMA query_only = ON"
            conn
        with _ ->
            (conn :> IDisposable).Dispose()
            reraise ()

/// `PRAGMA wal_checkpoint`, which reports a checkpoint it couldn't finish (another checkpoint
/// running, or readers still on old frames past the busy timeout) in its `busy` column, not as an
/// error.
module internal Checkpoint =
    let run (conn: Conn) (mode: string) : unit =
        try
            match conn.QueryRow($"PRAGMA wal_checkpoint({mode})", [||], fun r -> r.Int64 0) with
            | 0L -> ()
            | _ -> Log.warn $"WAL checkpoint couldn't finish ({mode})"
        with e ->
            Log.warn $"WAL checkpoint failed ({mode}): {e.Message}"

    /// The WAL's size in frames: what `sqlite3_wal_hook` reports after a commit. NOOP mode checkpoints
    /// nothing and takes no locks (SQLite 3.51+).
    let walPages (conn: Conn) : int = int (conn.QueryRow("PRAGMA wal_checkpoint(NOOP)", [||], fun r -> r.Int64 1))

/// The writer's side of the checkpointer thread, which runs a PASSIVE checkpoint on its own
/// connection each time it's woken.
type internal Checkpoints(path: string) =
    let conn = Pragmas.openConnection path false
    let wake = new SemaphoreSlim(0, 1)
    let running = obj ()
    let mutable stopped = false
    /// The WAL's size in pages when the checkpointer was last woken.
    let mutable wokenAt = 0

    let thread =
        Thread(
            (fun () ->
                while (wake.Wait(); not stopped) do
                    // Held while the checkpointer runs, so the writer's RESTART waits for it rather
                    // than being refused (SQLite runs one checkpoint at a time) and letting the WAL
                    // grow past its limit.
                    lock running (fun () -> Checkpoint.run conn "PASSIVE")),
            Name = "campfire-db-checkpointer",
            IsBackground = true
        )

    do thread.Start()

    member _.Thread : Thread = thread

    /// Wakes the checkpointer for every `AutocheckpointPages` the WAL grows.
    member _.WalGrewTo(pages: int) : unit =
        if pages < wokenAt then wokenAt <- 0 // the WAL restarted
        // While a checkpoint is still due (it hasn't taken the last wake), the next commit tries again.
        if pages - wokenAt >= Pragmas.AutocheckpointPages && wake.CurrentCount = 0 then
            try
                wake.Release() |> ignore
                wokenAt <- pages
            with :? SemaphoreFullException ->
                ()

    /// A RESTART checkpoint on the writer connection, between writes: it copies what the
    /// checkpointer hasn't, and waits for readers so that the next write restarts the WAL. It waits
    /// for a running PASSIVE checkpoint first, which would otherwise make SQLite refuse it.
    member _.RestartWal(writer: Conn) : unit = lock running (fun () -> Checkpoint.run writer "RESTART")

    member _.Stop() : unit =
        stopped <- true
        try
            wake.Release() |> ignore
        with :? SemaphoreFullException ->
            ()
        thread.Join()
        (conn :> IDisposable).Dispose()

/// The reads waiting for a reader thread, in order, and the reader connections not in use.
type internal ReadQueue() =
    let gate = obj ()
    let reads = Queue<Conn -> unit>()
    let connections = Stack<Conn>()
    /// Reader threads waiting for a read and a connection to run it on.
    let mutable idle = 0
    let mutable closed = false

    /// Wakes a reader thread when one is waiting and there's a read and a connection for it. Called
    /// with the lock held.
    let wakeAReader () =
        if idle > 0 && reads.Count > 0 && connections.Count > 0 then Monitor.Pulse gate

    member _.Push(read: Conn -> unit) : unit =
        lock gate (fun () ->
            reads.Enqueue read
            wakeAReader ())

    /// A connection for a read on the calling thread, unless none is free or reads are queued
    /// (they go first).
    member _.TakeConnection() : Conn option =
        lock gate (fun () -> if reads.Count = 0 && connections.Count > 0 then Some(connections.Pop()) else None)

    /// Adds a connection (at start-up), or returns one taken by `TakeConnection`.
    member _.GiveBack(conn: Conn) : unit =
        lock gate (fun () ->
            connections.Push conn
            wakeAReader ())

    /// For a reader thread, which gives back the connection of the read it `finished`: the next
    /// read and a connection to run it on, once there are both; `None` once the queue is closed
    /// and empty.
    member _.Next(finished: Conn option) : ((Conn -> unit) * Conn) option =
        lock gate (fun () ->
            finished |> Option.iter connections.Push
            let mutable result = None
            let mutable exit = false
            while result.IsNone && not exit do
                if reads.Count > 0 && connections.Count > 0 then
                    result <- Some(reads.Dequeue(), connections.Pop())
                elif closed && reads.Count = 0 then
                    exit <- true
                else
                    idle <- idle + 1
                    Monitor.Wait gate |> ignore
                    idle <- idle - 1
            result)

    member _.Close() : unit =
        lock gate (fun () ->
            closed <- true
            Monitor.PulseAll gate)

    member _.Queued : int = lock gate (fun () -> reads.Count)

    member _.DisposeConnections() : unit =
        lock gate (fun () ->
            while connections.Count > 0 do
                (connections.Pop() :> IDisposable).Dispose())

/// A write for the writer thread (onCrack: a class, so that the writer can run several in one transaction).
[<AbstractClass>]
type internal WriteJob() =
    /// Runs the write's closure in `tx`, keeping its value; raises what the closure raises.
    abstract Run: Tx -> unit
    /// The closure (or its transaction) failed and rolled back: what the caller gets.
    abstract Failed: exn -> unit
    /// An after-commit hook failed: the first such error reaches the caller once the rest have run, as
    /// `DbRun.runWrite` raises it.
    abstract HookFailed: exn -> unit
    /// Forgets a run, for a group that is run again write by write.
    abstract Reset: unit -> unit
    /// The closure ran and nothing failed it.
    abstract Succeeded: bool
    /// Answers the caller. The writer calls it after the versions the group marked are released.
    abstract Reply: unit -> unit

[<Sealed>]
type internal WriteJob<'T>(f: Tx -> 'T, complete: Result<Result<'T, DbError>, exn> -> unit) =
    inherit WriteJob()
    let mutable value = Unchecked.defaultof<'T>
    let mutable ran = false
    let mutable failure: exn option = None
    let mutable hookFailure: exn option = None

    /// What `DbRun.attempt` makes of an exception: a `DbError` for the caller, or the exception itself.
    static let outcome (e: exn) : Result<Result<'T, DbError>, exn> =
        match e with
        | DbException error -> Ok(Error error)
        | :? Microsoft.Data.Sqlite.SqliteException as e -> Ok(Error(Sqlite e))
        | e -> Error e

    override _.Run(tx: Tx) =
        value <- f tx
        ran <- true

    override _.Failed(e: exn) = failure <- Some e

    override _.HookFailed(e: exn) = if hookFailure.IsNone then hookFailure <- Some e

    override _.Reset() =
        value <- Unchecked.defaultof<'T>
        ran <- false
        failure <- None
        hookFailure <- None

    override _.Succeeded = ran && failure.IsNone

    override _.Reply() =
        match failure, hookFailure with
        | Some e, _
        | None, Some e -> complete (outcome e)
        | None, None -> complete (Ok(Ok value))

/// The bounded queue of work for the writer thread.
type internal WriteQueue(capacity: int) =
    let gate = obj ()
    let items = Queue<WriteJob>()
    let slots = new SemaphoreSlim(capacity, capacity)
    let mutable closed = false
    /// Who has the writer connection: 0 nobody, 1 the writer thread, 2 a write running on its caller's thread.
    let mutable owner = 0

    let enqueue (job: WriteJob) : bool =
        lock gate (fun () ->
            if closed then
                slots.Release() |> ignore
                false
            else
                items.Enqueue job
                Monitor.Pulse gate
                true)

    let dequeueInto (group: ResizeArray<WriteJob>) (limit: int) : unit =
        while items.Count > 0 && group.Count < limit do
            group.Add(items.Dequeue())
            slots.Release() |> ignore

    /// Waits for room in the queue without holding a thread.
    member _.EnqueueAsync(job: WriteJob) : Task<bool> =
        task {
            do! slots.WaitAsync()
            return enqueue job
        }

    member _.Enqueue(job: WriteJob) : bool =
        slots.Wait()
        enqueue job

    /// For the writer thread: the next jobs, up to `limit` of what is queued (once one is), waiting up to
    /// `windowUs` microseconds for more while fewer than `limit`; empty once closed and drained.
    member _.TakeGroup(limit: int, windowUs: int) : ResizeArray<WriteJob> =
        let group = ResizeArray<WriteJob>()
        lock gate (fun () ->
            while owner <> 0 || (items.Count = 0 && not closed) do
                Monitor.Wait gate |> ignore
            dequeueInto group limit
            if group.Count > 0 then owner <- 1
            if windowUs > 0 && group.Count > 0 && group.Count < limit && not closed then
                let deadline = Diagnostics.Stopwatch.GetTimestamp() + int64 windowUs * Diagnostics.Stopwatch.Frequency / 1_000_000L
                let mutable waiting = true
                while waiting do
                    let left = deadline - Diagnostics.Stopwatch.GetTimestamp()
                    if left <= 0L || closed then
                        waiting <- false
                    else
                        Monitor.Wait(gate, TimeSpan.FromTicks(max 1L (left * TimeSpan.TicksPerSecond / Diagnostics.Stopwatch.Frequency))) |> ignore
                        dequeueInto group limit
                        if group.Count >= limit then waiting <- false)
        group

    /// For the writer thread, once its group is answered.
    member _.Finished() : unit =
        lock gate (fun () ->
            owner <- 0
            Monitor.PulseAll gate)

    /// onCrack (unit R2.2): the writer connection for a write on the calling thread, when nobody has it and no
    /// write is queued (they go first, in order).
    member _.TryTakeInline() : bool =
        lock gate (fun () ->
            if owner = 0 && items.Count = 0 && not closed then
                owner <- 2
                true
            else
                false)

    /// Gives the connection back after a write on the calling thread, waking the writer thread for what queued meanwhile.
    member _.ReleaseInline() : unit =
        lock gate (fun () ->
            owner <- 0
            Monitor.PulseAll gate)

    member _.Close() : unit =
        lock gate (fun () ->
            closed <- true
            Monitor.PulseAll gate)

/// onCrack: group commit. The writer takes every write already queued (up to `Config.GroupMax`) and runs
/// them in one `BEGIN IMMEDIATE` transaction, each in a savepoint of its own, so a write that fails rolls
/// back alone and the others commit. One COMMIT for the group, then the group's after-commit work, in the
/// writes' order, in one more transaction, then their events, then (once the versions are released) the
/// answers, in order. So every write is committed (the same `synchronous=normal` WAL commit as Rails')
/// before its caller hears back: durability is unchanged, and a write's rows and after-commit work are
/// what they would be alone, since each write in the group sees everything before it, as it would have
/// committed (one connection, one order).
///
/// What differs from writes run alone, by design: the after-commit work of the group commits together
/// (Rails autocommits each hook's statements; a statement that fails still rolls back alone, as SQLite
/// rolls back a failed statement and not its transaction), and its events go out after that commit rather
/// than between hooks. If anything breaks the group's transaction itself (a commit or a savepoint that
/// fails, an error that makes SQLite roll back the whole transaction), nothing of it committed, and the
/// group runs again write by write, exactly as before. Write closures do database work only (a non-database
/// effect belongs in an after-commit hook), which is what makes running one again safe.
module internal Writer =
    let private exec (conn: Conn) (sql: string) : unit = conn.Execute(sql, [||]) |> ignore

    let private committing = DbRun.committing

    let private commit (conn: Conn) : unit = committing conn (fun () -> exec conn "COMMIT")

    let private rollbackIfOpen (conn: Conn) : unit =
        if not conn.IsAutocommit then
            try
                exec conn "ROLLBACK"
            with _ ->
                ()

    /// Runs after-commit items outside a transaction, as `DbRun.runWrite` does; events go out as they come.
    let private afterCommitAlone (conn: Conn) (env: Env) (job: WriteJob) (items: AfterCommitItem list) : unit =
        let after = Tx(conn, env, false)
        for item in items do
            match item with
            | AfterCommitItem.Emit event -> env.Sink.Emit event
            | AfterCommitItem.Effect effect ->
                try
                    effect ()
                with e ->
                    Log.error $"after_commit hook failed: {e.Message}"
                    job.HookFailed e
            | AfterCommitItem.Hook hook ->
                try
                    // Outside a transaction: its statements autocommit.
                    committing conn (fun () -> hook after)
                with e ->
                    Log.error $"after_commit hook failed: {e.Message}"
                    job.HookFailed e

    /// One write in its own transaction, as the port runs every write. True when it committed.
    let runAlone (conn: Conn) (env: Env) (job: WriteJob) : bool =
        let tx = Tx(conn, env, true)
        let committed =
            try
                exec conn "BEGIN IMMEDIATE"
                job.Run tx
                tx.RunOnCommit job.HookFailed
                commit conn
                true
            with e ->
                rollbackIfOpen conn
                job.Failed e
                false
        if committed then afterCommitAlone conn env job (tx.TakeAfterCommit())
        committed

    /// The group's after-commit work in one transaction; its events once that commits. False (and nothing of
    /// it committed) when the transaction broke, for the caller to run it the way `runAlone` does.
    let private afterCommitGrouped (conn: Conn) (env: Env) (work: (WriteJob * AfterCommitItem list) list) : bool =
        let events = ResizeArray<Event>()
        let failures = ResizeArray<WriteJob * exn>()
        let after = Tx(conn, env, false, Some events)
        let ok =
            try
                exec conn "BEGIN IMMEDIATE"
                let mutable intact = true
                for job, items in work do
                    for item in items do
                        if intact then
                            match item with
                            | AfterCommitItem.Emit event -> events.Add event
                            // Effects run in the transaction's place in line; they touch no table.
                            | AfterCommitItem.Effect effect ->
                                try
                                    effect ()
                                with e ->
                                    failures.Add((job, e))
                            | AfterCommitItem.Hook hook ->
                                try
                                    hook after
                                with e ->
                                    // A failed statement rolled back alone; one that took the transaction with it
                                    // leaves nothing of the group's after-commit work, which then runs again alone.
                                    if conn.IsAutocommit then intact <- false else failures.Add((job, e))
                if intact then
                    commit conn
                    true
                else
                    false
            with _ ->
                false
        if ok then
            for job, e in failures do
                Log.error $"after_commit hook failed: {e.Message}"
                job.HookFailed e
            for event in events do
                env.Sink.Emit event
        else
            rollbackIfOpen conn
        ok

    /// Runs `jobs` (in queue order) as one group; true when any committed.
    let runGroup (conn: Conn) (env: Env) (jobs: ResizeArray<WriteJob>) : bool =
        if jobs.Count = 1 then
            runAlone conn env jobs[0]
        else
            let work = ResizeArray<WriteJob * AfterCommitItem list>()
            let committing = ResizeArray<WriteJob * Tx>()
            let grouped =
                try
                    exec conn "BEGIN IMMEDIATE"
                    let mutable intact = true
                    let mutable i = 0
                    while intact && i < jobs.Count do
                        let job = jobs[i]
                        exec conn "SAVEPOINT campfire_write"
                        let tx = Tx(conn, env, true)
                        try
                            job.Run tx
                            exec conn "RELEASE campfire_write"
                            committing.Add((job, tx))
                        with e ->
                            if conn.IsAutocommit then
                                intact <- false
                            else
                                try
                                    exec conn "ROLLBACK TO campfire_write"
                                    exec conn "RELEASE campfire_write"
                                    job.Failed e
                                with _ ->
                                    intact <- false
                        i <- i + 1
                    // The writes' `OnCommit` work, in their order, after every write of the group (as the after-commit
                    // work of a group runs), in the group's transaction.
                    let mutable k = 0
                    while intact && k < committing.Count do
                        let job, tx = committing[k]
                        tx.RunOnCommit job.HookFailed
                        work.Add((job, tx.TakeAfterCommit()))
                        k <- k + 1
                    if intact then
                        commit conn
                        true
                    else
                        false
                with _ ->
                    false
            if not grouped then
                rollbackIfOpen conn
                let mutable any = false
                for job in jobs do
                    job.Reset()
                    if runAlone conn env job then any <- true
                any
            else
                let work = List.ofSeq work
                let hooks = work |> List.exists (fun (_, items) -> items |> List.exists (function AfterCommitItem.Hook _ -> true | _ -> false))
                if hooks then
                    if not (afterCommitGrouped conn env work) then
                        for job, items in work do
                            afterCommitAlone conn env job items
                else
                    // Only effects and events: nothing to commit, so no transaction for them (onCrack, unit R2.2).
                    for job, items in work do
                        afterCommitAlone conn env job items
                not work.IsEmpty

/// onCrack: what the writer has done, for tests and diagnostics.
[<Sealed>]
type WriterStats() =
    [<DefaultValue>]
    val mutable Groups: int64

    [<DefaultValue>]
    val mutable Writes: int64

    [<DefaultValue>]
    val mutable Largest: int

    /// onCrack (unit R2.2): writes run on their caller's thread (`InlineWrites`), counted in `Groups` and `Writes` too.
    [<DefaultValue>]
    val mutable Inline: int64

    /// Every database's restarts together (for the in-process harness, which has no handle on the app's database).
    static member val All = WriterStats() with get

    /// onCrack (unit R2.2): the writer's own WAL restarts (`WalLimitPages`), and the longest, in microseconds.
    [<DefaultValue>]
    val mutable Restarts: int64

    [<DefaultValue>]
    val mutable LongestRestartUs: int64

    member internal this.Restarted(took: TimeSpan) : unit =
        Interlocked.Increment(&this.Restarts) |> ignore
        Interlocked.Increment(&WriterStats.All.Restarts) |> ignore
        let us = int64 took.TotalMicroseconds
        if us > Volatile.Read(&this.LongestRestartUs) then Volatile.Write(&this.LongestRestartUs, us)
        if us > Volatile.Read(&WriterStats.All.LongestRestartUs) then Volatile.Write(&WriterStats.All.LongestRestartUs, us)
        if took.TotalMilliseconds > 100.0 then Log.warn $"WAL restart took {int took.TotalMilliseconds} ms"

    /// On the writer thread, per group taken.
    member internal this.Record(size: int) : unit =
        Interlocked.Increment(&this.Groups) |> ignore
        Interlocked.Add(&this.Writes, int64 size) |> ignore
        if size > Volatile.Read(&this.Largest) then Volatile.Write(&this.Largest, size)

/// The database handle: dispose it to stop its threads and close its connections.
[<NoComparison; NoEquality>]
type Database
    private
    (
        env: Env,
        path: string,
        writeQueue: WriteQueue,
        readers: ReadQueue,
        readerThreads: Thread list,
        checkpoints: Checkpoints,
        writerThread: Thread,
        writer: Conn,
        versions: Versions,
        stats: WriterStats,
        inlineWrites: bool,
        processInline: ResizeArray<WriteJob> -> unit
    ) =
    // Not a `Monitor`, which the thread already holding it could enter again: a `ReadBlocking` inside
    // another gets a connection of its own.
    let blockingGate = new SemaphoreSlim(1, 1)
    let mutable blockingReader: Conn option = None
    let mutable disposed = false

    /// Opens (and with `Config.Prepare` prepares) the database at `config.Path`, and starts its writer,
    /// checkpointer and reader threads.
    static member Open(config: Config, env: Env) : Database =
        Database.OpenWith(config, env, (fun path -> Pragmas.openConnection path true), ignore)

    /// `Open` with the way reader connections are opened, and a call for every thread started, as the
    /// tests' seam for a failure partway through.
    static member internal OpenWith
        (
            config: Config,
            env: Env,
            openReader: string -> Conn,
            started: Thread -> unit
        ) : Database =
        let conn = Pragmas.openConnection config.Path false
        let versions = Versions()
        let stats = WriterStats()
        let readerThreads = ResizeArray<Thread>()
        let queue = WriteQueue(max config.WriteQueue 1)
        let readers = ReadQueue()
        let mutable checkpoints: Checkpoints option = None
        let mutable writerThread: Thread option = None
        let mutable processInline: ResizeArray<WriteJob> -> unit = ignore
        try
            if config.Prepare then Schema.prepare conn config.Environment env.Clock |> ignore
            let cp = Checkpoints config.Path
            checkpoints <- Some cp
            started cp.Thread
            // In place of the auto-checkpoint, which the writer's commits note the WAL size for instead
            // (Rust installs `sqlite3_wal_hook`, which the .NET bindings don't expose).
            conn.ExecuteBatch "PRAGMA wal_autocheckpoint = 0"
            // onCrack: every change the writer makes marks the read cache's versions (`Versions.fs`).
            Versions.install conn versions
            if not versions.Watching then
                Log.warn "read cache off: the database has no WAL index to watch for other connections' commits"

            // A group's run, its answers and the WAL's check: on the writer thread, or (one write that found the
            // writer idle) on its caller's thread.
            let processGroup (jobs: ResizeArray<WriteJob>) (onWriter: bool) : unit =
                stats.Record jobs.Count
                // A write that raises must not take the writer down with it: `Writer` hands the
                // closure's exception to its caller and rolls back; this is the backstop for
                // anything else.
                let committed =
                    try
                        try
                            Writer.runGroup conn env jobs
                        with e ->
                            if not conn.IsAutocommit then
                                try
                                    conn.ExecuteBatch "ROLLBACK TRANSACTION"
                                with _ ->
                                    ()
                            for job in jobs do
                                if not job.Succeeded then job.Failed e
                            false
                    finally
                        // The group's transactions and after-commit work are over (or rolled back):
                        // the versions it marked become even, past every stored value, before any
                        // caller hears back, so a read right after its own write finds them even.
                        versions.Release()
                for job in jobs do
                    try
                        job.Reply()
                    with e ->
                        Log.error $"write reply failed: {e.Message}"
                if committed then
                    match (try Checkpoint.walPages conn with _ -> 0) with
                    | 0 -> ()
                    | pages when pages >= Pragmas.WalLimitPages ->
                        // RESTART waits for the readers; a request's thread must not (onCrack, unit R2.2): an empty
                        // write sends the writer thread round, which checks the WAL after it.
                        if onWriter then
                            let started = Diagnostics.Stopwatch.GetTimestamp()
                            cp.RestartWal conn
                            stats.Restarted(Diagnostics.Stopwatch.GetElapsedTime(started))
                        else queue.Enqueue(WriteJob<unit>(ignore, ignore)) |> ignore
                    | pages -> cp.WalGrewTo pages
            processInline <- fun jobs -> processGroup jobs false

            let thread =
                Thread(
                    (fun () ->
                        let groupMax = max config.GroupMax 1
                        let mutable running = true
                        while running do
                            let jobs = queue.TakeGroup(groupMax, config.GroupWindowUs)
                            if jobs.Count = 0 then
                                running <- false
                            else
                                try
                                    processGroup jobs true
                                finally
                                    queue.Finished()),
                    Name = "campfire-db-writer",
                    IsBackground = true
                )
            thread.Start()
            writerThread <- Some thread
            started thread

            for _ in 1 .. max config.Readers 1 do
                readers.GiveBack(openReader config.Path)
                let thread =
                    Thread(
                        (fun () ->
                            let mutable finished = None
                            let mutable running = true
                            while running do
                                match readers.Next finished with
                                | None -> running <- false
                                | Some(read, conn) ->
                                    // A read that fails fails its caller's read, not the reader.
                                    try
                                        read conn
                                    with _ ->
                                        ()
                                    finished <- Some conn),
                        Name = "campfire-db-reader",
                        IsBackground = true
                    )
                thread.Start()
                readerThreads.Add thread
                started thread
            new Database(env, config.Path, queue, readers, List.ofSeq readerThreads, cp, thread, conn, versions, stats, config.InlineWrites, processInline)
        with _ ->
            // Rust's `?` drops what was built: the queue's sender, which ends the writer thread and
            // with it the writer connection and the checkpointer, and the readers' connections.
            // Disposing the finished database does the same, in the same order.
            queue.Close()
            writerThread |> Option.iter (fun t -> t.Join())
            checkpoints |> Option.iter (fun c -> c.Stop())
            (conn :> IDisposable).Dispose()
            readers.Close()
            for thread in readerThreads do
                thread.Join()
            readers.DisposeConnections()
            versions.Unwatch()
            reraise ()

    member _.Env : Env = env

    member _.Path : string = path

    /// onCrack: the read cache's version counters, which this database's writer bumps.
    member _.Versions : Versions = versions

    /// onCrack: the writer's groups (`Writer`).
    member _.WriterStats : WriterStats = stats

    /// Reader threads still running; zero once disposed.
    member internal _.ReaderThreadsAlive : int = readerThreads |> List.filter (fun t -> t.IsAlive) |> List.length

    /// Reads waiting for a reader thread.
    member internal _.QueuedReads : int = readers.Queued

    /// Runs `f` as one immediate transaction on the writer thread (onCrack: or as part of one, with the
    /// writes queued beside it; see `Writer`).
    member this.Write(f: Tx -> 'T) : Task<Result<'T, DbError>> =
        if inlineWrites && PostPath.InlineWrites && WriteLoad.InFlight <= 1 && writeQueue.TryTakeInline() then
            this.WriteInline f
        else
            this.WriteQueued f

    /// onCrack (unit R2.2): `Write` on the calling thread, the writer connection taken by `TryTakeInline`: the same
    /// group of one, answers and WAL check as the writer thread's, and the task complete when it returns.
    member private _.WriteInline(f: Tx -> 'T) : Task<Result<'T, DbError>> =
        Interlocked.Increment(&stats.Inline) |> ignore
        let mutable outcome: Result<Result<'T, DbError>, exn> option = None
        let job = WriteJob<'T>(f, fun result -> outcome <- Some result)
        try
            processInline (ResizeArray [ job :> WriteJob ])
        finally
            writeQueue.ReleaseInline()
        match outcome with
        | Some(Ok result) -> Task.FromResult result
        | Some(Error e) -> Task.FromException<Result<'T, DbError>> e
        | None -> Task.FromResult(Error WriterGone)

    member private _.WriteQueued(f: Tx -> 'T) : Task<Result<'T, DbError>> =
        task {
            let reply = TaskCompletionSource<Result<'T, DbError>>(TaskCreationOptions.RunContinuationsAsynchronously)
            let job =
                WriteJob<'T>(
                    f,
                    function
                    | Ok result -> reply.SetResult result
                    | Error e -> reply.SetException e
                )
            let! queued = writeQueue.EnqueueAsync job
            if queued then return! reply.Task else return Error WriterGone
        }

    /// `Write` for synchronous callers (not from inside an async task).
    member _.WriteBlocking(f: Tx -> 'T) : Result<'T, DbError> =
        use replied = new ManualResetEventSlim(false)
        let outcome: Result<Result<'T, DbError>, exn> option ref = ref None
        let job =
            WriteJob<'T>(
                f,
                fun result ->
                    outcome.Value <- Some result
                    replied.Set()
            )
        if writeQueue.Enqueue job then
            replied.Wait()
            match outcome.Value with
            | Some(Ok result) -> result
            | Some(Error e) ->
                ExceptionDispatchInfo.Capture(e).Throw()
                Error WriterGone
            | None -> Error WriterGone
        else
            Error WriterGone

    /// Runs `f` on a reader connection: right here, on the calling task's thread, when one is free
    /// and no read is queued for one, since a read on a warm page cache takes less time than the
    /// hop to a reader thread and back; otherwise as `ReadOffloaded` does. At most as
    /// many pool threads as there are readers are ever inside `f`. The task is complete when it returns:
    /// Rust yields to the runtime's other tasks here (`tokio::task::yield_now`, a re-queue on the same
    /// worker), but a `Task.Yield` queues the continuation to the thread pool and wakes another worker to
    /// look for it, which cost a request with five or six reads 190 us of CPU at one connection.
    ///
    /// Reads whose cost grows with the whole database rather than with a page (search, every
    /// user, all of a user's messages) use `ReadOffloaded`, to keep them off the pool's threads.
    member this.Read(f: Conn -> 'T) : Task<Result<'T, DbError>> =
        match readers.TakeConnection() with
        | None -> this.ReadOffloaded f
        | Some conn ->
            // A read that raises a bug still gives its connection back, and fails its caller's task.
            try
                let result =
                    try
                        DbRun.attempt (fun () -> f conn)
                    finally
                        readers.GiveBack conn
                Task.FromResult result
            with e ->
                Task.FromException<Result<'T, DbError>> e

    /// Runs `f` on a reader thread, the next one free. Once queued, `f` runs even if its caller
    /// stops waiting (a request dropped when its client goes away): some reads broadcast
    /// what a write committed, like messages#create's.
    member _.ReadOffloaded(f: Conn -> 'T) : Task<Result<'T, DbError>> =
        let reply = TaskCompletionSource<Result<'T, DbError>>(TaskCreationOptions.RunContinuationsAsynchronously)
        readers.Push(fun conn ->
            try
                reply.SetResult(DbRun.attempt (fun () -> f conn))
            with e ->
                reply.SetException e)
        reply.Task

    /// `Read` for synchronous callers (tests), on the calling thread, so that `f` may borrow. It
    /// keeps a reader connection for these reads, and opens another for one that finds it in use:
    /// a `ReadBlocking` inside another would otherwise wait for itself.
    member _.ReadBlocking(f: Conn -> 'T) : Result<'T, DbError> =
        if blockingGate.Wait 0 then
            try
                let conn =
                    match blockingReader with
                    | Some conn -> conn
                    | None ->
                        let conn = Pragmas.openConnection path true
                        blockingReader <- Some conn
                        conn
                DbRun.attempt (fun () -> f conn)
            finally
                blockingGate.Release() |> ignore
        else
            use conn = Pragmas.openConnection path true
            DbRun.attempt (fun () -> f conn)

    interface IDisposable with
        member _.Dispose() =
            if not disposed then
                disposed <- true
                writeQueue.Close()
                writerThread.Join()
                checkpoints.Stop()
                (writer :> IDisposable).Dispose()
                readers.Close()
                for thread in readerThreads do
                    thread.Join()
                readers.DisposeConnections()
                blockingReader |> Option.iter (fun conn -> (conn :> IDisposable).Dispose())
                // After every connection: closing the WAL index's descriptor drops this process's locks on it.
                versions.Unwatch()
