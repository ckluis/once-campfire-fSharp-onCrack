// onCrack: version counters for the read cache (no Rust counterpart).
//
// Every page the read cache keeps (`Campfire.App.ReadCache`) is stored with the versions of what it was
// read from, and served only while those versions are unchanged. A version is a counter:
//
// - `Global`: anything rare and shared by many pages: accounts, users (names, avatars, roles, status
//   are rendered in other people's pages), rooms created or destroyed, bans, blobs and their variants,
//   attachments and rich texts that don't belong to a message, webhooks;
// - `Room r`: room r's row, its messages, their bodies, attachments and boosts, and who is a member
//   (one counter per room id modulo `RoomStripes`: readers ask for the room id in a URL before anything
//   checks the room exists, so a counter per id would grow with every id anyone types; rooms that share
//   a counter only invalidate each other's pages);
// - `User u`: u's memberships (involvement, unread state, connections), searches and push
//   subscriptions;
// - `Sessions`: any session row (sign in, sign out, the hourly activity refresh).
//
// The writer bumps them, not the code that writes: the writer connection carries TEMP triggers (they
// live in the connection, never in the database file, so the schema stays the reference's) on every
// table, which call `campfire_bump(kind, id)`. No write path can forget its bump, cascades and
// after-commit work included. The FTS5 table can't have triggers; its writes always run in the same
// write job as the message write that marks the room, and mark it again themselves (`Conn.Marks`).
//
// The invalidation rule, odd while in flight: the first mark of a counter in a write job makes it odd
// (before the row change, inside the transaction), and the job's end makes it even again, after the
// commit and the after-commit work. A reader takes the counters it depends on *before* its first
// query, stores what it read under them only if they were all even, and serves a stored page only while
// every counter still equals the stored value. So:
//
// - a change that committed is never hidden: from its first row change until after its commit, its
//   counters are odd (no hit, no store), and after it they have moved past every stored value;
// - a page read under counters taken before a commit, and stored after it, is stored under the old
//   values, which no later request sees again.
//
// One writer thread owns `pending` and does every bump; readers only read the counters, except for the watch below,
// which adds 2 (keeping each counter's parity) under its own lock.
//
// Commits by other connections (the round 2 verifier's critical finding): the triggers live in the writer's connection, so a
// row changed by anything else (a Rails console or a rollback to Rails, a second container during a deploy, an admin script,
// the sqlite3 shell) moved no counter, and a revoked session, a deleted membership or a renamed room stayed served from the
// caches for as long as the process ran. The watch closes that:
//
// - SQLite's WAL index (the `-shm` file every connection to the database maps) starts with a header whose `iChange` is
//   incremented by every commit that writes, by any connection, and by nothing else: not by checkpoints, WAL restarts, empty
//   commits, rollbacks or TEMP writes (sqlite.org/walformat.html, 2.2.1; checked in `VersionsWatchTests`). The watch maps it
//   read-only and keeps `accepted`, the value every commit up to which is accounted for.
// - The writer's own commits go through `Committing` (a `COMMIT`, an after-commit hook's autocommitted statements), under the
//   watch's lock: it reads the writer connection's `PRAGMA data_version` before and after, which changes only when another
//   connection committed, then makes the header's value after the commit the accepted one. If either reading shows another
//   connection's commit (since the last one, or during this one), everything is invalidated first.
// - `Sync` is what every cache calls before it serves anything (a page, a session, a user, a fast path replay) and what a
//   request calls before it reads (the fragment store's epoch): a header value nobody accounted for is a commit by another
//   connection (or one of the writer's own outside `Committing`, which costs the same and is never wrong), and moves every
//   counter by 2 and the epoch by 1 before it is accepted. A reader that finds the header moved while the writer is in
//   `Committing` waits for it on the lock, and then finds the value accepted.
//
// So a request that starts after another connection's commit returned never sees a cached page, session or fragment from
// before it. A database without a WAL index to map (in memory, or not in WAL mode) is never cached (`Complete` stays false).
namespace Campfire.Db

#nowarn "9" // the WAL index header, read through a pointer into its mapping

open System
open System.Collections.Concurrent
open System.Collections.Generic
open System.IO
open System.Threading
open Microsoft.FSharp.NativeInterop

/// One version counter. Even when no write that changes what it covers is in flight.
[<Sealed; AllowNullLiteral>]
type VersionCell() =
    [<DefaultValue>]
    val mutable Value: int64

    member this.Read() : int64 = Volatile.Read(&this.Value)

/// What a counter covers.
type VersionKind =
    | Global = 0
    | Room = 1
    | User = 2
    | Sessions = 3

/// The libc calls the WAL index's mapping needs, by the name each platform gives libc (as `Campfire.Kit.Server` does).
module private LinuxC =
    open System.Runtime.InteropServices

    [<DllImport("libc.so.6", EntryPoint = "open")>]
    extern int openFile(byte[] path, int flags)

    [<DllImport("libc.so.6", EntryPoint = "close")>]
    extern int closeFile(int fd)

    [<DllImport("libc.so.6", EntryPoint = "mmap")>]
    extern nativeint mmap(nativeint addr, unativeint length, int prot, int flags, int fd, int64 offset)

    [<DllImport("libc.so.6", EntryPoint = "munmap")>]
    extern int munmap(nativeint addr, unativeint length)

module private MacC =
    open System.Runtime.InteropServices

    [<DllImport("libSystem.dylib", EntryPoint = "open")>]
    extern int openFile(byte[] path, int flags)

    [<DllImport("libSystem.dylib", EntryPoint = "close")>]
    extern int closeFile(int fd)

    [<DllImport("libSystem.dylib", EntryPoint = "mmap")>]
    extern nativeint mmap(nativeint addr, unativeint length, int prot, int flags, int fd, int64 offset)

    [<DllImport("libSystem.dylib", EntryPoint = "munmap")>]
    extern int munmap(nativeint addr, unativeint length)

module private Libc =
    // O_RDONLY, PROT_READ and MAP_SHARED have these values on Linux and macOS alike.
    [<Literal>]
    let O_RDONLY = 0

    [<Literal>]
    let PROT_READ = 1

    [<Literal>]
    let MAP_SHARED = 1

    let supported = OperatingSystem.IsLinux() || OperatingSystem.IsMacOS()

    let openFile (path: byte[], flags: int) : int =
        if OperatingSystem.IsLinux() then LinuxC.openFile (path, flags) else MacC.openFile (path, flags)

    let closeFile (fd: int) : int =
        if OperatingSystem.IsLinux() then LinuxC.closeFile fd else MacC.closeFile fd

    let mmap (addr: nativeint, length: unativeint, prot: int, flags: int, fd: int, offset: int64) : nativeint =
        if OperatingSystem.IsLinux() then LinuxC.mmap (addr, length, prot, flags, fd, offset)
        else MacC.mmap (addr, length, prot, flags, fd, offset)

    let munmap (addr: nativeint, length: unativeint) : int =
        if OperatingSystem.IsLinux() then LinuxC.munmap (addr, length) else MacC.munmap (addr, length)

/// The `iChange` field of a WAL index's header (`<db>-shm`, offset 8, native byte order), mapped read-only.
///
/// Through libc, not `FileStream`: .NET takes a `flock` on a file it opens, which on macOS conflicts with SQLite's `fcntl`
/// locks on the same file. And the descriptor stays open until `Dispose`, which must come after every SQLite connection of
/// this process to the database has closed: closing any descriptor of a file drops the process's POSIX locks on it,
/// SQLite's included (the WAL index's dead-man switch among them).
[<Sealed>]
type WalChangeCounter private (fd: int, address: nativeint) =
    static let length = 4096un
    let mutable disposed = false

    /// The counter of the database at `path`, or null when it has no WAL index (yet) to map, or the platform can't map it
    /// (the caches then stay off: `Versions.install`).
    static member Open(path: string) : WalChangeCounter | null =
        let shm = path + "-shm"
        if not Libc.supported || String.IsNullOrEmpty path || not (File.Exists shm) || FileInfo(shm).Length < int64 length then
            null
        else
            try
                let bytes = Array.append (Text.Encoding.UTF8.GetBytes shm) [| 0uy |]
                let fd = Libc.openFile (bytes, Libc.O_RDONLY)
                if fd < 0 then
                    null
                else
                    let address = Libc.mmap (0n, length, Libc.PROT_READ, Libc.MAP_SHARED, fd, 0L)
                    if address = -1n || address = 0n then
                        Libc.closeFile fd |> ignore
                        null
                    else
                        new WalChangeCounter(fd, address)
            with
            | :? DllNotFoundException
            | :? EntryPointNotFoundException -> null

    /// The header's change counter now (every commit that wrote anything moved it by one).
    member _.Read() : uint32 =
        // Callers read `accepted` (volatile) right after, which keeps this load from being reused across calls.
        NativePtr.read (NativePtr.ofNativeInt<uint32> (address + 8n))

    interface IDisposable with
        member _.Dispose() =
            if not disposed then
                disposed <- true
                Libc.munmap (address, length) |> ignore
                Libc.closeFile fd |> ignore

[<Sealed>]
type Versions() =
    let globalCell = VersionCell()
    let sessionsCell = VersionCell()
    let rooms: VersionCell[] = Array.zeroCreate Versions.RoomStripes
    let users = ConcurrentDictionary<int64, VersionCell>()
    static let make = Func<int64, VersionCell>(fun _ -> VersionCell())
    // The writer thread's: counters made odd by the job in progress.
    let pending = HashSet<VersionCell>(HashIdentity.Reference)
    let mutable marks = 0L

    member _.Global : VersionCell = globalCell
    member _.Sessions : VersionCell = sessionsCell
    /// Room `id`'s counter, shared with the ids equal to it modulo `RoomStripes` (bounded whatever ids
    /// requests name; sequential ids share none until there are that many rooms).
    member _.Room(id: int64) : VersionCell =
        let i = int (id &&& int64 (Versions.RoomStripes - 1))
        match Volatile.Read(&rooms[i]) with
        | null ->
            let made = VersionCell()
            match Interlocked.CompareExchange(&rooms[i], made, null) with
            | null -> made
            | existing -> existing
        | cell -> cell

    /// Room counters made so far (at most `RoomStripes`), for tests.
    member _.RoomCells : int =
        let mutable n = 0
        for i in 0 .. rooms.Length - 1 do
            if not (isNull (Volatile.Read(&rooms[i]))) then n <- n + 1
        n

    /// How many room counters there are at most (a power of two).
    static member RoomStripes = 65536
    member _.User(id: int64) : VersionCell = users.GetOrAdd(id, make)

    /// The counter for `kind` and `id` (an unknown id, -1, is `Global`).
    member this.Cell(kind: VersionKind, id: int64) : VersionCell =
        match kind with
        | VersionKind.Room when id >= 0L -> this.Room id
        | VersionKind.User when id >= 0L -> this.User id
        | VersionKind.Sessions -> sessionsCell
        | _ -> globalCell

    /// On the writer thread, before a change to what `cell` covers: odd until `Release`.
    member _.Mark(cell: VersionCell) : unit =
        if pending.Add cell then
            Interlocked.Increment(&cell.Value) |> ignore
            marks <- marks + 1L

    member this.Mark(kind: VersionKind, id: int64) : unit = this.Mark(this.Cell(kind, id))

    /// On the writer thread, once the job's transaction and after-commit work are done (or rolled back):
    /// every counter it marked is even again, one past where it was.
    member _.Release() : unit =
        if pending.Count > 0 then
            for cell in pending do
                Interlocked.Increment(&cell.Value) |> ignore
            pending.Clear()

    /// Whether the writer marks every table (it can't on a database without the schema): the read cache
    /// stores nothing otherwise.
    member val Complete = false with get, set

    /// Counters marked since the start, for tests and the cache's statistics.
    member _.Marks : int64 = Volatile.Read(&marks)

    // --- The watch for other connections' commits (see the top of the file) ---

    [<DefaultValue>]
    val mutable private accepted: uint32

    [<DefaultValue>]
    val mutable private epoch: int64

    [<DefaultValue>]
    val mutable private lastDataVersion: int64

    [<DefaultValue>]
    val mutable private counter: WalChangeCounter | null

    [<DefaultValue>]
    val mutable private watched: Conn | null

    member val private WatchGate = obj ()

    /// Every counter moves by 2 (keeping its parity, so one a write has made odd stays odd until its `Release`), and the
    /// epoch by 1. Under `WatchGate`.
    member private this.Unexplained() : unit =
        Interlocked.Add(&globalCell.Value, 2L) |> ignore
        Interlocked.Add(&sessionsCell.Value, 2L) |> ignore
        for i in 0 .. rooms.Length - 1 do
            match Volatile.Read(&rooms[i]) with
            | null -> ()
            | cell -> Interlocked.Add(&cell.Value, 2L) |> ignore
        for KeyValue(_, cell) in users do
            Interlocked.Add(&cell.Value, 2L) |> ignore
        let epoch = Interlocked.Increment(&this.epoch)
        // The app's own writes never come here (`ForeignWriteTests`, "the app's own writes never count ..."); a bench that logs
        // this line has a write path outside `Committing`.
        if epoch <= 10L || epoch % 1000L = 0L then
            eprintfn "WARN campfire_db: a commit by another connection: every cache invalidated (epoch %d)" epoch

    /// Starts watching the database at `path` for commits by connections other than `conn` (the writer's). False when
    /// it has no WAL index to watch.
    member this.Watch(conn: Conn, path: string) : bool =
        match WalChangeCounter.Open path with
        | null -> false
        | counter ->
            lock this.WatchGate (fun () ->
                this.counter <- counter
                this.watched <- conn
                this.lastDataVersion <- Versions.DataVersion conn
                Volatile.Write(&this.accepted, counter.Read()))
            true

    /// Whether `Watch` found a WAL index.
    member this.Watching : bool = not (isNull this.counter)

    /// Accounts for every commit made so far: any that no `Committing` made invalidates every counter. Returns the
    /// epoch, which moves once for each time that happened (the fragment store's generation). Callers: every cache before
    /// it serves anything, and every request before its first read.
    member this.Sync() : int64 =
        match this.counter with
        | null -> ()
        | counter ->
            if counter.Read() <> Volatile.Read(&this.accepted) then
                lock this.WatchGate (fun () ->
                    let now = counter.Read()
                    if now <> this.accepted then
                        this.Unexplained()
                        Volatile.Write(&this.accepted, now))
        Volatile.Read(&this.epoch)

    /// The epoch, without syncing.
    member this.Epoch : int64 = Volatile.Read(&this.epoch)

    /// On the writer's connection: runs `commit`, telling its commits apart from other connections' by the connection's
    /// `data_version`, which moves only for theirs.
    member this.Committing(commit: unit -> unit) : unit =
        match this.counter, this.watched with
        | null, _
        | _, null -> commit ()
        | counter, conn ->
            lock this.WatchGate (fun () ->
                let before = Versions.DataVersion conn
                if before <> this.lastDataVersion then this.Unexplained()
                try
                    commit ()
                finally
                    let now = counter.Read()
                    let after = Versions.DataVersion conn
                    if after <> before then this.Unexplained()
                    this.lastDataVersion <- after
                    Volatile.Write(&this.accepted, now))

    /// `PRAGMA data_version` on `conn`, or -1 (which no reading equals, so the caller invalidates) if it fails.
    static member private DataVersion(conn: Conn) : int64 =
        try
            conn.QueryRow("PRAGMA data_version", [||], fun r -> r.Int64 0)
        with _ ->
            -1L

    /// Stops watching (the database is closing).
    member this.Unwatch() : unit =
        lock this.WatchGate (fun () ->
            match this.counter with
            | null -> ()
            | counter ->
                this.counter <- null
                this.watched <- null
                (counter :> IDisposable).Dispose())

    interface IWriteMarks with
        member this.Mark(kind: int, id: int64) = this.Mark(enum<VersionKind> kind, id)
        member this.Committing(commit: unit -> unit) = this.Committing commit

module Versions =
    /// The SQL function the triggers call.
    [<Literal>]
    let FunctionName = "campfire_bump"

    let private g = "SELECT campfire_bump(0, 0);"
    let private room (row: string) (column: string) = "SELECT campfire_bump(1, " + row + "." + column + ");"
    let private user (row: string) (column: string) = "SELECT campfire_bump(2, " + row + "." + column + ");"

    /// The room of a row that belongs to a message by `column`, or -1 (global) when the message is gone.
    let private roomOfMessage (row: string) (column: string) =
        "SELECT campfire_bump(1, coalesce((SELECT room_id FROM main.messages WHERE id = " + row + "." + column + "), -1));"

    /// A polymorphic row (`record_type`, `record_id`): a message's marks its room, anything else is global.
    let private recordRow (row: string) =
        let message = row + ".record_type = 'Message'"
        "SELECT campfire_bump(CASE WHEN " + message + " THEN 1 ELSE 0 END, CASE WHEN " + message
        + " THEN coalesce((SELECT room_id FROM main.messages WHERE id = " + row + ".record_id), -1) ELSE 0 END);"

    /// Per table, the bumps for an inserted row (NEW), a deleted one (OLD), and an updated one (both).
    let private rules: (string * (string -> string)) list =
        [ "accounts", (fun _ -> g)
          "users", (fun _ -> g)
          "bans", (fun _ -> g)
          "webhooks", (fun _ -> g)
          "active_storage_blobs", (fun _ -> g)
          "active_storage_variant_records", (fun _ -> g)
          "active_storage_attachments", recordRow
          "action_text_rich_texts", recordRow
          "messages", (fun row -> room row "room_id")
          "boosts", (fun row -> roomOfMessage row "message_id")
          "searches", (fun row -> user row "user_id")
          "push_subscriptions", (fun row -> user row "user_id")
          "sessions", (fun _ -> "SELECT campfire_bump(3, 0);") ]

    /// The TEMP triggers that mark every change. Rooms and memberships have their own: a room created
    /// or destroyed changes which room is the original and what exists (global); a membership's own
    /// columns (involvement, unread, connections) are rendered only to its user, while one added,
    /// removed or moved changes the room's members.
    let triggers: string list =
        let trigger (name: string) (event: string) (table: string) (body: string) =
            "CREATE TEMP TRIGGER IF NOT EXISTS cv_" + name + " AFTER " + event + " ON main." + table + " BEGIN " + body + " END"
        let table (name: string) (bump: string -> string) =
            [ trigger (name + "_i") "INSERT" name (bump "NEW")
              trigger (name + "_d") "DELETE" name (bump "OLD")
              trigger (name + "_u") "UPDATE" name (bump "OLD" + " " + bump "NEW") ]
        [ for name, bump in rules do
              yield! table name bump
          yield trigger "rooms_i" "INSERT" "rooms" (g + " " + room "NEW" "id")
          yield trigger "rooms_d" "DELETE" "rooms" (g + " " + room "OLD" "id")
          yield trigger "rooms_u" "UPDATE" "rooms" (room "OLD" "id" + " " + room "NEW" "id")
          yield trigger "memberships_i" "INSERT" "memberships" (room "NEW" "room_id" + " " + user "NEW" "user_id")
          yield trigger "memberships_d" "DELETE" "memberships" (room "OLD" "room_id" + " " + user "OLD" "user_id")
          yield
              trigger
                  "memberships_u"
                  "UPDATE"
                  "memberships"
                  (user "OLD" "user_id"
                   + " "
                   + user "NEW" "user_id"
                   + " SELECT campfire_bump(1, OLD.room_id), campfire_bump(1, NEW.room_id) WHERE OLD.room_id IS NOT NEW.room_id OR OLD.user_id IS NOT NEW.user_id;") ]

    /// The tables the triggers watch.
    let tables: string list = (rules |> List.map fst) @ [ "rooms"; "memberships" ]

    /// Gives the writer connection `campfire_bump` and the triggers, marking `versions`. A database
    /// without some table (one opened without its schema) gets no triggers, and the cache stays off.
    let install (conn: Conn) (versions: Versions) : unit =
        conn.Raw.CreateFunction(
            FunctionName,
            Func<int64, int64, int64>(fun kind id ->
                versions.Mark(enum<VersionKind> (int kind), id)
                0L),
            false
        )
        conn.Marks <- versions
        let existing =
            conn.QueryAll("SELECT name FROM sqlite_master WHERE type = 'table'", [||], fun r -> r.Text 0) |> Set.ofList
        // A database whose other connections' commits can't be seen is never cached.
        let watching = versions.Watch(conn, conn.Raw.DataSource)
        if tables |> List.forall existing.Contains then
            for sql in triggers do
                conn.ExecuteBatch sql
            versions.Complete <- watching
