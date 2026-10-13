// Port of rust/crates/db/src/models/session.rs
// `reference/app/models/session.rb`
namespace Campfire.Db

open System

type Session =
    { Id: int64
      UserId: int64
      Token: string
      IpAddress: string option
      UserAgent: string option
      LastActiveAt: Timestamp
      CreatedAt: Timestamp
      UpdatedAt: Timestamp }

module Session =
    /// `Session::ACTIVITY_REFRESH_RATE`
    let activityRefreshRate : TimeSpan = TimeSpan.FromHours 1.0

    let private fromRow (r: Row) : Session =
        { Id = r.Int64 0
          UserId = r.Int64 1
          Token = r.Text 2
          IpAddress = r.OptText 3
          UserAgent = r.OptText 4
          LastActiveAt = r.Timestamp 5
          CreatedAt = r.Timestamp 6
          UpdatedAt = r.Timestamp 7 }

    let find (conn: Conn) (id: int64) : Session =
        conn.QueryOne($"SELECT {Columns.Session} FROM \"sessions\" WHERE \"sessions\".\"id\" = ? LIMIT 1", [| I id |], fromRow)
        |> Err.orNotFound "Session"

    /// `Session.find_by(token:)`
    let findByToken (conn: Conn) (token: string) : Session option =
        conn.QueryOne($"SELECT {Columns.Session} FROM \"sessions\" WHERE \"sessions\".\"token\" = ? LIMIT 1", [| S token |], fromRow)

    let forUser (conn: Conn) (userId: int64) : Session list =
        conn.QueryAll($"SELECT {Columns.Session} FROM \"sessions\" WHERE \"sessions\".\"user_id\" = ?", [| I userId |], fromRow)

    let countForUser (conn: Conn) (userId: int64) : int64 =
        conn.Count("""SELECT COUNT(*) FROM "sessions" WHERE "sessions"."user_id" = ?""", [| I userId |])

    /// `user.sessions.start!(user_agent:, ip_address:)`: a new 24-character base58
    /// `has_secure_token`, and `last_active_at ||= Time.now` in `before_create`.
    let start (tx: Tx) (userId: int64) (userAgent: string option) (ipAddress: string option) : Session =
        let now = tx.Now()
        let lastActiveAt = tx.Now()
        let token = Sql.base58 24
        let id =
            tx.Conn.QueryRow(
                """INSERT INTO "sessions" ("created_at", "ip_address", "last_active_at", "token", "updated_at", "user_agent", "user_id") VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING "id" """,
                [| T now; Sql.optS ipAddress; T lastActiveAt; S token; T now; Sql.optS userAgent; I userId |],
                fun r -> r.Int64 0
            )
        { Id = id
          UserId = userId
          Token = token
          IpAddress = ipAddress
          UserAgent = userAgent
          LastActiveAt = lastActiveAt
          CreatedAt = now
          UpdatedAt = now }

    /// Whether `resume` would refresh the session at `now`: its activity is over an hour old.
    let needsResume (session: Session) (now: Timestamp) : bool = session.LastActiveAt < now.Ago activityRefreshRate

    /// `resume`: refreshes activity, user agent and IP at most once an hour.
    let resume (tx: Tx) (session: Session) (userAgent: string option) (ipAddress: string option) : Session =
        let now = tx.Now()
        if not (needsResume session now) then
            session
        else
            let resumed =
                { session with
                    UserAgent = userAgent
                    IpAddress = ipAddress
                    LastActiveAt = now
                    UpdatedAt = tx.Now() }
            tx.Conn.Execute(
                """UPDATE "sessions" SET "ip_address" = ?, "last_active_at" = ?, "updated_at" = ?, "user_agent" = ? WHERE "sessions"."id" = ?""",
                [| Sql.optS resumed.IpAddress; T resumed.LastActiveAt; T resumed.UpdatedAt; Sql.optS resumed.UserAgent; I resumed.Id |]
            )
            |> ignore
            resumed

    /// `destroy!`
    let destroy (tx: Tx) (session: Session) : unit =
        tx.Conn.Execute("""DELETE FROM "sessions" WHERE "sessions"."id" = ?""", [| I session.Id |]) |> ignore

/// onCrack R3.2 (`CAMPFIRE_FRESH_AUTH`): upstream's fresh authorization on a cache hit, as narrow existence queries (Laravel's shape,
/// one prepared statement each) instead of the rows the miss read. What a hit is served on must still hold in the database now:
/// - the session: a row with the cookie's token, the id and the user the answer was made for, and that user's row (authentication
///   reads `Session.find_by(token:)`, then `session.user`; a sign-out, a ban or a deactivation deletes the row, a rotated token no
///   longer matches);
/// - for a page about one room: the user's membership in it, and the room (`set_room` finds the membership, then its room).
/// A deleted, rotated or reassigned session, a deleted user, a removed membership or a deleted room each make it false.
module FreshAuth =
    [<Literal>]
    let private SessionExists =
        """EXISTS (SELECT 1 FROM "sessions" INNER JOIN "users" ON "users"."id" = "sessions"."user_id" WHERE "sessions"."token" = ? AND "sessions"."id" = ? AND "sessions"."user_id" = ?)"""

    [<Literal>]
    let private MembershipExists =
        """EXISTS (SELECT 1 FROM "memberships" INNER JOIN "rooms" ON "rooms"."id" = "memberships"."room_id" WHERE "memberships"."room_id" = ? AND "memberships"."user_id" = ?)"""

    [<Literal>]
    let private SessionSql = "SELECT " + SessionExists

    [<Literal>]
    let private MembershipSql = "SELECT " + MembershipExists

    [<Literal>]
    let private BothSql = "SELECT " + SessionExists + " AND " + MembershipExists

    /// Checks run, in this process (tests read it to know a hit was checked rather than passing because nothing was cached).
    let checks = ref 0L

    /// The user's membership in `roomId`, and the room.
    let membership (conn: Conn) (roomId: int64) (userId: int64) : bool =
        System.Threading.Interlocked.Increment(&checks.contents) |> ignore
        conn.Count(MembershipSql, [| I roomId; I userId |]) = 1L

    /// The session (`token`, `sessionId`, `userId`) and its user, and with `room` the membership in it and the room: what a replay
    /// of an answer made for that session needs, in one statement.
    let replay (conn: Conn) (token: string) (sessionId: int64) (userId: int64) (room: int64 voption) : bool =
        System.Threading.Interlocked.Increment(&checks.contents) |> ignore
        match room with
        | ValueNone -> conn.Count(SessionSql, [| S token; I sessionId; I userId |]) = 1L
        | ValueSome roomId -> conn.Count(BothSql, [| S token; I sessionId; I userId; I roomId; I userId |]) = 1L
