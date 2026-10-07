// onCrack: the read cache's version counters (`src/Campfire.Db/Versions.fs`). The writer's triggers mark
// what each change covers, odd from the change until after the commit and the after-commit work.
module Campfire.Db.Tests.VersionsTests

open System.Threading
open Xunit
open Campfire.Db
open Campfire.Db.Tests.Support

/// Every counter a test looks at, read at once.
type private Snapshot =
    { Global: int64
      Sessions: int64
      Rooms: Map<string, int64>
      Users: Map<string, int64> }

let private rooms = [ "designers"; "pets"; "watercooler"; "hq" ]
let private users = [ "david"; "jason"; "jz"; "kevin" ]

let private snapshot (t: TestDb) : Snapshot =
    let v = t.Db.Versions
    { Global = v.Global.Read()
      Sessions = v.Sessions.Read()
      Rooms = rooms |> List.map (fun r -> r, v.Room(id r).Read()) |> Map.ofList
      Users = users |> List.map (fun u -> u, v.User(id u).Read()) |> Map.ofList }

/// What moved between two snapshots, as names: "global", "sessions", "room:x", "user:x".
let private moved (before: Snapshot) (after: Snapshot) : string list =
    [ if before.Global <> after.Global then "global"
      if before.Sessions <> after.Sessions then "sessions"
      for r in rooms do
          if before.Rooms[r] <> after.Rooms[r] then "room:" + r
      for u in users do
          if before.Users[u] <> after.Users[u] then "user:" + u ]

let private allEven (s: Snapshot) : bool =
    s.Global % 2L = 0L
    && s.Sessions % 2L = 0L
    && s.Rooms |> Map.forall (fun _ v -> v % 2L = 0L)
    && s.Users |> Map.forall (fun _ v -> v % 2L = 0L)

let private change (t: TestDb) (f: Tx -> unit) : string list =
    let before = snapshot t
    t.Write f
    let after = snapshot t
    Assert.True(allEven after, "every counter is even once the write is done")
    moved before after

[<Fact>]
let ``a message marks its room and only its room (members' unread state marks them)`` () =
    use t = new TestDb()
    let changed =
        change t (fun tx ->
            Message.create tx { NewMessage.create (id "designers") (id "jason") with Body = Some "hi" } |> ignore)
    Assert.Contains("room:designers", changed)
    Assert.DoesNotContain("room:pets", changed)
    Assert.DoesNotContain("room:watercooler", changed)
    Assert.DoesNotContain("global", changed)
    Assert.DoesNotContain("sessions", changed)
    // The creator's own membership isn't marked unread.
    Assert.DoesNotContain("user:jason", changed)

[<Fact>]
let ``editing, boosting and deleting a message mark its room`` () =
    use t = new TestDb()
    let message =
        t.Write(fun tx -> Message.create tx { NewMessage.create (id "pets") (id "david") with Body = Some "one" })
    let edited = change t (fun tx -> Message.updateBody tx message "two" |> ignore)
    Assert.Equal<string list>([ "room:pets" ], edited)
    let boosted = change t (fun tx -> Boost.create tx message.Id (id "jason") "👍" |> ignore)
    Assert.Equal<string list>([ "room:pets" ], boosted)
    let message = t.Read(fun c -> Message.find c message.Id)
    let deleted = change t (fun tx -> Message.destroy tx message)
    Assert.Equal<string list>([ "room:pets" ], deleted)

[<Fact>]
let ``a membership's own columns mark only its user; adding or removing one marks the room too`` () =
    use t = new TestDb()
    let membership = t.Read(fun c -> Membership.findByRoomAndUser c (id "designers") (id "david")) |> Option.get
    let involvement = change t (fun tx -> Membership.updateInvolvement tx membership (Some Involvement.Everything) |> ignore)
    Assert.Equal<string list>([ "user:david" ], involvement)
    let room = t.Read(fun c -> Room.find c (id "designers"))
    let revoked = change t (fun tx -> Room.revokeFrom tx room [ id "david" ])
    Assert.Contains("room:designers", revoked)
    Assert.Contains("user:david", revoked)
    Assert.DoesNotContain("user:jason", revoked)
    let granted = change t (fun tx -> Room.grantTo tx room [ id "david" ])
    Assert.Contains("room:designers", granted)
    Assert.Contains("user:david", granted)

[<Fact>]
let ``users, accounts, bans and new rooms are global; sessions have their own counter`` () =
    use t = new TestDb()
    let user = t.Read(fun c -> User.find c (id "jason"))
    Assert.Contains("global", change t (fun tx -> User.update tx user { UserChanges.none with Name = Some "J" } |> ignore))
    Assert.Contains("global", change t (fun tx -> Ban.create tx (id "jason") "93.184.216.34" |> ignore))
    let created = change t (fun tx -> Room.create tx RoomType.Open (Some "New") (id "david") |> ignore)
    Assert.Contains("global", created)
    let session = change t (fun tx -> Session.start tx (id "david") None None |> ignore)
    Assert.Equal<string list>([ "sessions" ], session)
    Assert.Equal<string list>([ "user:david" ], change t (fun tx -> Search.record tx (id "david") "eels" |> ignore))

[<Fact>]
let ``a counter is odd from the change until after the commit and the after-commit work`` () =
    use t = new TestDb()
    let cell = t.Db.Versions.Room(id "designers")
    let start = cell.Read()
    let mutable before = -1L
    let mutable inside = -1L
    let mutable afterCommit = -1L
    t.Write(fun tx ->
        before <- cell.Read()
        Message.create tx { NewMessage.create (id "designers") (id "jason") with Body = Some "odd" } |> ignore
        inside <- cell.Read()
        tx.AfterCommit(fun _ -> afterCommit <- cell.Read()))
    Assert.Equal(start, before)
    Assert.Equal(1L, inside % 2L)
    Assert.Equal(inside, afterCommit)
    Assert.Equal(start + 2L, cell.Read())

[<Fact>]
let ``a rolled back write still leaves its counters even and moved`` () =
    use t = new TestDb()
    let cell = t.Db.Versions.Room(id "designers")
    let start = cell.Read()
    let result =
        t.TryWrite(fun tx ->
            Message.create tx { NewMessage.create (id "designers") (id "jason") with Body = Some "gone" } |> ignore
            raise (DbException(Other(exn "roll back"))))
    Assert.True(Result.isError result)
    Assert.Equal(start + 2L, cell.Read())

[<Fact>]
let ``a reader never sees an even counter with a change it doesn't cover yet`` () =
    // Readers take the counter, count, and take it again; a writer posts all the while. Every count taken
    // between two equal even readings of the counter must be the same for that value: nothing commits
    // while the counter stays at one even value, which is what lets a page stored under it be served.
    use t = new TestDb()
    let roomId = id "designers"
    let cell = t.Db.Versions.Room roomId
    let stop = ref false
    let writer =
        Thread(fun () ->
            let mutable n = 0
            while not stop.Value do
                n <- n + 1
                t.Write(fun tx ->
                    Message.create tx { NewMessage.create roomId (id "jason") with Body = Some(string n) } |> ignore))
    writer.Start()
    let seen = System.Collections.Generic.Dictionary<int64, int64>()
    let mutable checks = 0
    let deadline = System.Diagnostics.Stopwatch.StartNew()
    while deadline.ElapsedMilliseconds < 1500L do
        let v = cell.Read()
        let count = t.Read(fun c -> c.Count("SELECT COUNT(*) FROM messages WHERE room_id = ?", [| I roomId |]))
        if v % 2L = 0L && cell.Read() = v then
            match seen.TryGetValue v with
            | true, earlier ->
                checks <- checks + 1
                Assert.Equal(earlier, count)
            | _ -> seen[v] <- count
    stop.Value <- true
    writer.Join()
    Assert.True(seen.Count > 1, "the writer moved the counter")
    Assert.True(checks > 0, "some counts were compared")

[<Fact>]
let ``room counters stay bounded whatever room ids are asked for, and ids that share one share its marks`` () =
    // Readers ask for the room id in a URL before anything checks the room exists (the verifier's A2: a
    // counter per id grew by one per request for a room nobody has, and was never removed).
    let v = Versions()
    for i in 0L .. 1_000_000L do
        v.Room(900_000_000L + i * 7L) |> ignore
    v.Room(-1L) |> ignore
    v.Room(System.Int64.MinValue) |> ignore
    v.Room(System.Int64.MaxValue) |> ignore
    Assert.True(v.RoomCells <= Versions.RoomStripes, $"{v.RoomCells} room counters")
    // Rooms whose ids are equal modulo the stripes share a counter: a write to one invalidates the other's
    // pages, never the reverse of what it covers.
    let a = v.Room 486777696L
    let b = v.Room(486777696L + int64 Versions.RoomStripes)
    Assert.Same(a, b)
    Assert.NotSame(a, v.Room 486777697L)
    let before = b.Read()
    v.Mark a
    Assert.Equal(before + 1L, b.Read())
    v.Release()
    Assert.Equal(before + 2L, b.Read())
    // The seed's rooms have counters of their own.
    let seedRooms = [ 104393281L; 186869642L; 201306877L; 340026324L; 486777696L; 654632876L; 699448325L; 699448326L; 699448327L; 699448328L; 699448329L ]
    Assert.Equal(seedRooms.Length, seedRooms |> List.map (fun id -> v.Room id) |> List.distinctBy (fun c -> System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode c) |> List.length)
