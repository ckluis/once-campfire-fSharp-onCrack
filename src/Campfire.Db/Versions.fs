// onCrack: version counters for the read cache (no Rust counterpart).
//
// Every page the read cache keeps (`Campfire.App.ReadCache`) is stored with the versions of what it was
// read from, and served only while those versions are unchanged. A version is a counter:
//
// - `Global`: anything rare and shared by many pages: accounts, users (names, avatars, roles, status
//   are rendered in other people's pages), rooms created or destroyed, bans, blobs and their variants,
//   attachments and rich texts that don't belong to a message, webhooks;
// - `Room r`: room r's row, its messages, their bodies, attachments and boosts, and who is a member;
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
// One writer thread owns `pending` and does every bump; readers only read the counters.
namespace Campfire.Db

open System
open System.Collections.Concurrent
open System.Collections.Generic
open System.Threading

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

[<Sealed>]
type Versions() =
    let globalCell = VersionCell()
    let sessionsCell = VersionCell()
    let rooms = ConcurrentDictionary<int64, VersionCell>()
    let users = ConcurrentDictionary<int64, VersionCell>()
    static let make = Func<int64, VersionCell>(fun _ -> VersionCell())
    // The writer thread's: counters made odd by the job in progress.
    let pending = HashSet<VersionCell>(HashIdentity.Reference)
    let mutable marks = 0L

    member _.Global : VersionCell = globalCell
    member _.Sessions : VersionCell = sessionsCell
    member _.Room(id: int64) : VersionCell = rooms.GetOrAdd(id, make)
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

    interface IWriteMarks with
        member this.Mark(kind: int, id: int64) = this.Mark(enum<VersionKind> kind, id)

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
        if tables |> List.forall existing.Contains then
            for sql in triggers do
                conn.ExecuteBatch sql
            versions.Complete <- true
