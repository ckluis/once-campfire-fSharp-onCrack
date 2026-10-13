// Adversarial checks of onCrack round 1 (read cache, group commit, content-length). Scratch project: never part of the repo.
module Campfire.Attack.Tests

open System
open System.Collections.Concurrent
open System.Text.RegularExpressions
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

let private write (test: Test) (f: Tx -> 'T) : 'T = test.App.Db.WriteBlocking f |> unwrap
let private read (test: Test) (f: Conn -> 'T) : 'T = test.App.Db.ReadBlocking f |> unwrap
let private stats (test: Test) = ReadCache.stats test.App.Db.Versions

let private out (s: string) = Console.Error.WriteLine s

let private postForm (roomId: int64) (body: string) : Req =
    ((request "POST" $"/rooms/{roomId}/messages").With("accept", "text/vnd.turbo-stream.html, text/html, application/xhtml+xml"))
        .Form(formBody [ "message[body]", body ])

let private metaName (html: string) : string =
    let m = Regex.Match(html, "<meta name=\"current-user-name\" content=\"([^\"]*)\"")
    if m.Success then m.Groups[1].Value else "<none>"

let private authorInTemplate (html: string) : string =
    let m = Regex.Match(html, "data-messages-target=\"template\">[\\s\\S]*?<span class=\"message__author\"><strong>([^<]*)</strong>")
    if m.Success then m.Groups[1].Value else "<none>"

/// A1. The signed-in user is read (authentication) before the page's version counters are taken. A change to that
/// user committed in between is rendered from the old row and stored under the new counters, so it is served after
/// the change finished. Self-rename: the name in the layout's meta tag and the composer's message template.
[<Fact>]
let ``A1 a page stored with the user read before its counters were taken`` () =
    task {
        use! test = bootSeeded "default"
        let room = $"/rooms/{ALL_TALK}"
        let readers = [ for _ in 1..12 -> david test ]
        let checker = david test
        for b in checker :: readers do
            let! _ = b.Get room
            let! _ = b.Get room
            ()
        let stop = new CancellationTokenSource()
        let reader (b: Browser) =
            task {
                while not stop.IsCancellationRequested do
                    let! _ = b.Get room
                    ()
            }
        let running = readers |> List.map (fun b -> Task.Run(fun () -> reader b :> Task))
        let mutable stale = 0
        let mutable checks = 0
        let examples = ResizeArray<string>()
        let user0 = read test (fun conn -> User.find conn DAVID)
        for i in 1..1500 do
            let name = $"David {i}"
            write test (fun tx -> User.update tx user0 { UserChanges.none with Name = Some name } |> ignore)
            // The rename has committed and its counters are released: every later request must show it.
            let! page = checker.Get room
            checks <- checks + 1
            let meta = metaName page.Text
            let author = authorInTemplate page.Text
            if meta <> name || author <> name then
                stale <- stale + 1
                if examples.Count < 5 then examples.Add($"after rename to '{name}': meta '{meta}', template '{author}'")
                // Still stale on the next request with no write in between?
                let! again = checker.Get room
                if examples.Count < 6 then examples.Add($"  next request: meta '{metaName again.Text}'")
        stop.Cancel()
        do! Task.WhenAll running
        let h, m, s = stats test
        out $"A1: {stale} stale of {checks} checks; cache hits {h}, misses {m}, stored {s}"
        for e in examples do out ("A1   " + e)
        Assert.True((stale = 0), $"{stale} of {checks} pages after a committed rename showed an older name: {String.Join(' ', examples)}")
    }

/// A1b. The same on the sidebar, which renders the current user's name and avatar.
[<Fact>]
let ``A1b sidebar stored with the user read before its counters were taken`` () =
    task {
        use! test = bootSeeded "default"
        let path = "/users/me/sidebar"
        let readers = [ for _ in 1..12 -> david test ]
        let checker = david test
        let stop = new CancellationTokenSource()
        let reader (b: Browser) =
            task {
                while not stop.IsCancellationRequested do
                    let! _ = b.Get path
                    ()
            }
        let running = readers |> List.map (fun b -> Task.Run(fun () -> reader b :> Task))
        let mutable stale = 0
        let examples = ResizeArray<string>()
        let user0 = read test (fun conn -> User.find conn DAVID)
        for i in 1..1500 do
            let name = $"Davo {i}x"
            write test (fun tx -> User.update tx user0 { UserChanges.none with Name = Some name } |> ignore)
            let! page = checker.Get path
            if not (page.Text.Contains name) then
                stale <- stale + 1
                let m = Regex.Match(page.Text, "Davo \\d+x")
                if examples.Count < 5 then examples.Add($"after '{name}' the sidebar says '{m.Value}'")
        stop.Cancel()
        do! Task.WhenAll running
        out $"A1b: {stale} stale sidebars of 1500"
        for e in examples do out ("A1b   " + e)
        Assert.True((stale = 0), String.Join(" | ", examples))
    }

/// A2. Version cells are made for any room id a signed-in user puts in a URL, member or not, existing or not, and
/// never removed.
[<Fact>]
let ``A2 version counters for room ids nobody has grow without bound`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        let versions = test.App.Db.Versions
        let field = typeof<Versions>.GetField("rooms", Reflection.BindingFlags.NonPublic ||| Reflection.BindingFlags.Instance)
        // Since round 2 the room cells are a fixed array of stripes (Versions.RoomStripes), so the bound is the array's length.
        let count () = (field.GetValue versions :?> VersionCell[]) |> Array.filter (fun c -> not (isNull (box c))) |> Array.length
        let before = count ()
        GC.Collect()
        let memBefore = GC.GetTotalMemory true
        let n = 40_000
        let! _ =
            Task.WhenAll
                [| for w in 0..7 ->
                       Task.Run<unit>(fun () ->
                           task {
                               let cookie = davidCookie ()
                               for i in 0 .. (n / 8) - 1 do
                                   // Since round 2 the counters are one per id modulo RoomStripes, so ids that are all equal modulo that
                                   // number reach one cell: 40,000 distinct ids must make at most one, however many a request names.
                                   let id = 900_000_000L + int64 (w * (n / 8) + i) * int64 Versions.RoomStripes
                                   // No cookie jar: a redirect's flash would make the next request skip the cache.
                                   let! r = test.Send((getWithCookie (if i % 2 = 0 then $"/rooms/{id}" else $"/rooms/{id}/messages") cookie).With("accept", "text/html"))
                                   if r.Status <> 302 && r.Status <> 404 then failwith $"status {r.Status}"
                           }) |]
        GC.Collect()
        let memAfter = GC.GetTotalMemory true
        let after = count ()
        out $"A2: room version cells {before} -> {after} after {n} requests for rooms that don't exist; managed heap {memBefore / 1024L} KB -> {memAfter / 1024L} KB ({(memAfter - memBefore) / int64 n} bytes per request kept)"
        Assert.True(after - before < 1000, $"{after - before} cells kept for rooms that don't exist")
        Assert.True(after <= Versions.RoomStripes, $"{after} cells, more than the {Versions.RoomStripes} stripes")
    }

/// A3. Membership removal racing readers of the room page, the messages page, the sidebar and search: once the
/// removal has committed, no page may show the room.
[<Fact>]
let ``A3 membership removed and restored under concurrent readers`` () =
    task {
        use! test = bootSeeded "default"
        let room = $"/rooms/{QUIET_CORNER}"
        let token = "zyzzyvaquiet"
        write test (fun tx -> Message.create tx { NewMessage.create QUIET_CORNER KEVIN with Body = Some $"<div>{token} bodymarker77</div>" }) |> ignore
        let paths = [ room; $"/rooms/{QUIET_CORNER}/messages"; "/users/me/sidebar"; $"/searches?q={token}" ]
        let readers = [ for _ in 1..12 -> david test ]
        let stop = new CancellationTokenSource()
        let reader (b: Browser) =
            task {
                let mutable i = 0
                while not stop.IsCancellationRequested do
                    let! _ = b.Get(paths[i % paths.Length])
                    i <- i + 1
            }
        let running = readers |> List.map (fun b -> Task.Run(fun () -> reader b :> Task))
        let checker = david test
        let mutable bad = 0
        let examples = ResizeArray<string>()
        let quiet = read test (fun conn -> Room.find conn QUIET_CORNER)
        for i in 1..300 do
            write test (fun tx -> Room.revokeFrom tx quiet [ DAVID ])
            let! page = checker.Get room
            let! msgs = checker.Get $"/rooms/{QUIET_CORNER}/messages"
            let! sidebar = checker.Get "/users/me/sidebar"
            let! search = checker.Get $"/searches?q={token}"
            let leaks =
                [ if page.Status <> 302 then $"room page {page.Status}"
                  if msgs.Status <> 404 then $"messages {msgs.Status}"
                  if sidebar.Text.Contains($"/rooms/{QUIET_CORNER}\"") then "sidebar lists the room"
                  if search.Text.Contains "bodymarker77" then "search finds the room's message" ]
            if not leaks.IsEmpty then
                bad <- bad + 1
                if examples.Count < 5 then examples.Add($"round {i} removed: " + String.Join(", ", leaks))
            write test (fun tx -> Room.grantTo tx quiet [ DAVID ])
            let! page = checker.Get room
            let! search = checker.Get $"/searches?q={token}"
            let missing =
                [ if page.Status <> 200 then $"room page {page.Status}"
                  if not (search.Text.Contains "bodymarker77") then "search misses the message" ]
            if not missing.IsEmpty then
                bad <- bad + 1
                if examples.Count < 5 then examples.Add($"round {i} restored: " + String.Join(", ", missing))
        stop.Cancel()
        do! Task.WhenAll running
        let h, m, s = stats test
        out $"A3: {bad} bad of 600 checks; hits {h} misses {m} stored {s}"
        for e in examples do out ("A3   " + e)
        Assert.True((bad = 0), String.Join(" | ", examples))
    }

/// A4. Other users' posts, edits and deletes under group commit while many readers hold cached pages: after each
/// write's reply, another user's next request (room page, messages page, search) shows it.
[<Fact>]
let ``A4 cross-user read after write under concurrent posting`` () =
    task {
        use! test = bootSeeded "default"
        let room = $"/rooms/{ALL_TALK}"
        let readers = [ for _ in 1..8 -> david test ]
        let stop = new CancellationTokenSource()
        let reader (b: Browser) =
            task {
                let mutable i = 0
                while not stop.IsCancellationRequested do
                    let! _ = b.Get(if i % 3 = 0 then room elif i % 3 = 1 then "/searches?q=wombatx" else "/users/me/sidebar")
                    i <- i + 1
            }
        let running = readers |> List.map (fun b -> Task.Run(fun () -> reader b :> Task))
        let posters = [ for k in 1..8 -> k, browser test $"198.51.100.{100 + k}" ]
        for _, p in posters do
            do! p.SignIn "jason@37signals.com"
        let checker = david test
        let failures = ConcurrentBag<string>()
        let mutable checks = 0
        let poster (k: int, b: Browser) =
            task {
                let checker = david test
                for i in 1..25 do
                    let body = $"wombatx w{k}n{i}q"
                    let! r = b.Write(postForm ALL_TALK body)
                    if r.Status <> 200 then failures.Add($"post {body}: {r.Status}")
                    let! page = checker.Get room
                    let! search = checker.Get "/searches?q=wombatx"
                    Interlocked.Increment(&checks) |> ignore
                    if not (page.Text.Contains body) then failures.Add($"room page after {body} replied")
                    // search shows the last 100: the newest is always there
                    if not (search.Text.Contains $"w{k}n{i}q") then failures.Add($"search after {body} replied")
            }
        let! _ = Task.WhenAll [| for p in posters -> Task.Run<unit>(fun () -> poster p) |]
        stop.Cancel()
        do! Task.WhenAll running
        let stored = read test (fun conn -> Message.forRoom conn ALL_TALK |> List.map (fun m -> Message.bodyHtml conn m |> Option.defaultValue ""))
        for k in 1..8 do
            for i in 1..25 do
                let body = $"wombatx w{k}n{i}q"
                let n = stored |> List.filter (fun b -> b.Trim() = body || b.Contains(body + "<")) |> List.length
                if n <> 1 then failures.Add($"{body} stored {n} times")
        let ws = test.App.Db.WriterStats
        out $"A4: {checks} checks, {failures.Count} failures; writer {ws.Writes} writes in {ws.Groups} groups, largest {ws.Largest}"
        for g in failures |> Seq.groupBy (fun f -> f.Split(' ') |> Array.skip 1 |> String.concat " " |> fun x -> Regex.Replace(x, "\\d+", "#")) do
            out $"A4   kind '{fst g}': {Seq.length (snd g)}"
        for f in Seq.truncate 4 failures do out ("A4   " + f)
        let sample = stored |> List.filter (fun b -> b.Contains "wombatx") |> List.truncate 2
        for b in sample do out ("A4   stored sample: " + b)
        Assert.Empty failures
    }

/// A5. Broadcast order against commit order for concurrent posts to one room (group commit on by default).
[<Fact>]
let ``A5 broadcasts of concurrent posts go out in commit order`` () =
    task {
        use! test = bootSeeded "default"
        let roomRow = read test (fun conn -> Room.find conn ALL_TALK)
        let name = Campfire.Cable.Naming.streamNameFrom [ Campfire.RailsCompat.GlobalId.toParam (Campfire.App.Channels.Gid.roomGid roomRow); "messages" ]
        let wake = Campfire.Cable.Wake()
        use sub = test.App.Cable.Hub.Subscribe(name, null, wake)
        let frames = ResizeArray<string>()
        let stop = new CancellationTokenSource()
        let drain =
            Task.Run(fun () ->
                let mutable frame = Unchecked.defaultof<Campfire.Cable.Socket.Frame>
                while not stop.IsCancellationRequested || sub.TryRecv(&frame) = Campfire.Cable.RecvStatus.Got do
                    match sub.TryRecv(&frame) with
                    | Campfire.Cable.RecvStatus.Got -> frames.Add frame.Text
                    | Campfire.Cable.RecvStatus.Lagged -> frames.Add "LAGGED"
                    | _ -> Thread.SpinWait 50)
        let posters = [ for k in 1..16 -> david test ]
        let poster (k: int) (b: Browser) =
            task {
                for i in 1..20 do
                    let! r = b.Write(postForm ALL_TALK $"ordr{k}x{i}y")
                    if r.Status <> 200 then failwith $"post {r.Status}"
            }
        let! _ = Task.WhenAll [| for k, b in List.indexed posters -> Task.Run<unit>(fun () -> poster k b) |]
        do! Task.Delay 300
        stop.Cancel()
        do! drain
        let ids =
            frames
            |> Seq.choose (fun f ->
                let m = Regex.Match(f, "data-message-id=\\\\\"(\\d+)")
                if m.Success then Some(int64 m.Groups[1].Value) else None)
            |> List.ofSeq
        if frames.Count > 0 then out ("A5 sample frame: " + frames[0].Substring(0, min 600 frames[0].Length))
        let lagged = frames |> Seq.filter ((=) "LAGGED") |> Seq.length
        let inversions = ids |> List.pairwise |> List.filter (fun (a, b) -> b < a) |> List.length
        let ws = test.App.Db.WriterStats
        let gc = Environment.GetEnvironmentVariable "CAMPFIRE_GROUP_COMMIT"
        out $"A5: group commit {gc}: {frames.Count} frames, {ids.Length} message ids, {inversions} adjacent inversions (broadcast before an earlier commit), lagged {lagged}; writer {ws.Writes} writes / {ws.Groups} groups, largest {ws.Largest}"
        Assert.Equal(320, ids.Length)
    }

/// A6. A cached hit answers with the headers a miss answers with (and with the cache off), apart from per-request
/// ones; and the same for HEAD then GET, and conditional GETs across users.
[<Fact>]
let ``A6 headers of a hit equal a miss, HEAD first does not poison GET, ETags stay per user`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        let jasonB = browser test "198.51.100.23"
        do! jasonB.SignIn "jason@37signals.com"
        let skip = set [ "date"; "x-request-id"; "x-runtime"; "set-cookie" ]
        let headersOf (r: Reply) = r.Headers |> List.filter (fun (k, _) -> not (skip.Contains(k.ToLowerInvariant()))) |> List.map (fun (k, v) -> k.ToLowerInvariant(), v) |> List.sort
        let problems = ResizeArray<string>()
        let older = read test (fun conn -> Message.forRoom conn ALL_TALK |> List.sortBy (fun m -> m.Id) |> List.item 50)
        for path in [ $"/rooms/{ALL_TALK}"; $"/rooms/{ALL_TALK}/messages"; $"/rooms/{ALL_TALK}/messages?before={older.Id}"; "/users/me/sidebar"; "/searches?q=the"; "/searches" ] do
            // HEAD first, as the very first request for the key.
            let! head = david.Send((request "HEAD" path).With("accept-encoding", "gzip"))
            let! g1 = david.Get path
            let! g2 = david.Get path
            let! g3 = david.Get path
            if g2.Text <> g3.Text then problems.Add($"{path}: two hits differ")
            if g1.Text <> g3.Text then problems.Add($"{path}: miss and hit bodies differ ({g1.Text.Length} vs {g3.Text.Length})")
            if g3.Body.Length = 0 && g3.Status = 200 then problems.Add($"{path}: empty 200 after a HEAD")
            if headersOf g1 <> headersOf g3 then problems.Add($"{path}: headers miss {headersOf g1} vs hit {headersOf g3}")
            if head.Status <> g3.Status then problems.Add($"{path}: HEAD {head.Status} vs GET {g3.Status}")
            // David's ETag sent by Jason must not get Jason a 304.
            match g3.Header "etag" with
            | Some etag ->
                let! j = jasonB.Send((get path).With("if-none-match", etag))
                // The messages pages carry a content ETag (Rack::ETag's digest, as Rails): two members who see the same page share it, and
                // authorization runs before the 304. The per-user pages (room, sidebar, search) must not share one.
                let contentEtag = path.Contains "/messages"
                if j.Status = 304 && not contentEtag then problems.Add($"{path}: Jason got 304 for David's ETag")
                let! d = david.Send((get path).With("if-none-match", etag))
                out $"A6 {path}: etag {etag}, David conditional {d.Status}, Jason with David's etag {j.Status}"
            | None -> out $"A6 {path}: no etag (status {g3.Status})"
        // A content ETag must never answer for a room the viewer cannot see: David's ETag sent for a room that does not exist.
        let! known = david.Get $"/rooms/{ALL_TALK}/messages"
        match known.Header "etag" with
        | Some etag ->
            let! nope = david.Send((get "/rooms/900000001/messages").With("if-none-match", etag))
            out $"A6 messages page of a room that does not exist, with a real content ETag: {nope.Status}"
            if nope.Status = 304 || nope.Status = 200 then problems.Add($"a room that does not exist answered {nope.Status} to a content ETag")
        | None -> problems.Add "no ETag on the messages page"
        // Accept variants on a warm key: JSON, turbo-stream.
        for path in [ $"/rooms/{ALL_TALK}"; "/users/me/sidebar"; "/searches?q=the"; $"/rooms/{ALL_TALK}/messages" ] do
            let! html = david.Get path
            let! json = david.Send((get path).With("accept", "application/json"))
            let! ts = david.Send((get path).With("accept", "text/vnd.turbo-stream.html"))
            out $"A6 {path}: html {html.Status} {html.ContentType}, json {json.Status} {json.ContentType}, turbo-stream {ts.Status} {ts.ContentType}"
        for p in problems do out ("A6   " + p)
        Assert.Empty problems
    }

/// A7. The C2 flake: a post straight to the database, then a room page, repeatedly, on fresh apps. Look for an
/// empty or truncated room page.
[<Fact>]
let ``A7 room page right after a direct post, on fresh apps`` () =
    task {
        let problems = ResizeArray<string>()
        // A7_ROUNDS raises the count (30 by default) for a hunt for the one failure round 3 saw.
        let rounds = match Environment.GetEnvironmentVariable "A7_ROUNDS" with | null | "" -> 30 | n -> int n
        for round in 1..rounds do
            use! test = bootSeeded "default"
            let david = david test
            let room = $"/rooms/{ALL_TALK}"
            let body = $"echidna{round}"
            write test (fun tx -> Message.create tx { NewMessage.create ALL_TALK JASON with Body = Some $"<div>{body}</div>" }) |> ignore
            // A7_SABOTAGE=1 signs David's sessions out first: the diagnostics below must then print (a check of the harness itself).
            if Environment.GetEnvironmentVariable "A7_SABOTAGE" = "1" && round = 2 then
                write test (fun tx -> tx.Conn.Execute("DELETE FROM sessions", [||]) |> ignore)
            let! warm = david.Get room
            let jarAfterWarm = david.Cookie "session_token"
            let! first = david.Get room
            let! second = david.Get room
            let failed = ResizeArray<string>()
            for r, label in [ warm, "warm"; first, "first"; second, "second" ] do
                let bad = if label = "warm" then r.Status <> 200 else not (r.Text.Contains body)
                if bad then
                    let cookies = String.Join(" | ", r.SetCookies)
                    failed.Add($"round {round} {label}: status {r.Status}, {r.Body.Length} bytes, location {r.Location}, set-cookie [{cookies}]")
            if failed.Count > 0 then
                problems.AddRange failed
                // The app's own account of what happened (what it logged), and what its database says about the session the
                // cookie names, read at the database with every cache bypassed.
                out $"A7 round {round}: app log follows ({test.Logs.Length} chars)"
                out (if test.Logs = "" then "(nothing logged)" else test.Logs)
                let vectorToken =
                    (Campfire.Tests.Repo.vector "campfire_sessions").RootElement.GetProperty("sessions").EnumerateArray()
                    |> Seq.find (fun s -> s.GetProperty("user_name").GetString() = "David")
                    |> fun s -> s.GetProperty("token").GetString()
                let rows = read test (fun conn -> conn.Count("SELECT COUNT(*) FROM sessions", [||]))
                let users = read test (fun conn -> conn.Count("SELECT COUNT(*) FROM users", [||]))
                let found = read test (fun conn -> Campfire.Db.Session.findByToken conn vectorToken)
                let user = read test (fun conn -> User.findById conn DAVID)
                out $"A7 round {round}: session rows {rows}, user rows {users}, session by the vector's token found {found.IsSome}, David found {user.IsSome}"
                out $"A7 round {round}: warm {warm.Status} {warm.Location} / first {first.Status} / second {second.Status}"
                out $"A7 round {round}: warm's Set-Cookie headers {warm.SetCookies |> List.map (fun c -> c.Split(';')[0])}"
                out $"A7 round {round}: the jar's session_token after warm: {jarAfterWarm}"
        for p in problems do out ("A7   " + p)
        Assert.Empty problems
    }

/// A1c. The same race with an admin control: on the restricted seed only administrators get the sidebar's
/// "New Chat Room" button. Toggle David's role; after each toggle commits, the sidebar must match the role.
[<Fact>]
let ``A1c admin control on a sidebar stored with the user read before its counters`` () =
    task {
        use! test = bootSeeded "restricted"
        let path = "/users/me/sidebar"
        let readers = [ for _ in 1..12 -> david test ]
        let checker = david test
        let stop = new CancellationTokenSource()
        let reader (b: Browser) =
            task {
                while not stop.IsCancellationRequested do
                    let! _ = b.Get path
                    ()
            }
        let running = readers |> List.map (fun b -> Task.Run(fun () -> reader b :> Task))
        let mutable wrong = 0
        let examples = ResizeArray<string>()
        let user0 = read test (fun conn -> User.find conn DAVID)
        let! first = checker.Get path
        let shown0 = first.Text.Contains "New Chat Room"
        out $"A1c: David starts as {user0.Role}; button shown: {shown0}"
        for i in 1..1500 do
            let role = if i % 2 = 0 then Role.Administrator else Role.Member
            write test (fun tx -> tx.Conn.Execute("UPDATE users SET role = ? WHERE id = ?", [| I(int64 (int role)); I DAVID |]) |> ignore)
            let! page = checker.Get path
            let shown = page.Text.Contains "New Chat Room"
            if shown <> (role = Role.Administrator) then
                wrong <- wrong + 1
                if examples.Count < 5 then examples.Add($"after David became {role} the sidebar's New Chat Room button shown={shown}")
        stop.Cancel()
        do! Task.WhenAll running
        out $"A1c: {wrong} sidebars of 1500 disagreed with the committed role"
        for e in examples do out ("A1c   " + e)
        Assert.True((wrong = 0), String.Join(" | ", examples))
    }

/// A8. The page store's bound: distinct keys (a query string the page ignores) each store a whole room page.
[<Fact>]
let ``A8 the page store stays within its budget under distinct keys`` () =
    task {
        use! test = bootSeeded "default"
        let cookie = davidCookie ()
        let! sample = test.Send((getWithCookie $"/rooms/{ALL_TALK}" cookie).With("accept", "text/html"))
        GC.Collect()
        GC.WaitForPendingFinalizers()
        GC.Collect()
        let before = GC.GetTotalMemory true
        let n = 4000
        let! _ =
            Task.WhenAll
                [| for w in 0..7 ->
                       Task.Run<unit>(fun () ->
                           task {
                               for i in 0 .. (n / 8) - 1 do
                                   let! r = test.Send((getWithCookie $"/rooms/{ALL_TALK}?x={w}-{i}" cookie).With("accept", "text/html").With("accept-encoding", "gzip"))
                                   if r.Status <> 200 then failwith $"status {r.Status}"
                           }) |]
        GC.Collect()
        GC.WaitForPendingFinalizers()
        GC.Collect()
        let after = GC.GetTotalMemory true
        let _, _, stored = stats test
        let mb (b: int64) = float b / 1048576.0
        out $"A8: page {sample.Body.Length} bytes; {n} distinct keys, stored {stored}; managed heap {mb before:F1} MB -> {mb after:F1} MB (would be {mb (int64 n * int64 sample.Body.Length):F0} MB unbounded)"
        Assert.True(after - before < 160L * 1048576L, "the store kept more than its budget allows")
    }

/// A9. A hit sets the same cookies a miss sets (names and attributes, values aside for signed ones), and the
/// same as with the cache off (run twice).
[<Fact>]
let ``A9 cookies of a hit equal a miss`` () =
    task {
        use! test = bootSeeded "default"
        let cookie0 = davidCookie ()
        // The first request re-issues the Rails session cookie; take the cookie it sets.
        let! first = test.Send((getWithCookie "/up" cookie0))
        let! warm = test.Send((getWithCookie "/users/me/profile" cookie0).With("accept", "text/html"))
        let cookie =
            match warm.SetCookies |> List.tryFind (fun c -> c.StartsWith "session_token=") with
            | Some c -> c.Split(';')[0]
            | None -> cookie0
        let names (r: Reply) =
            r.SetCookies |> List.map (fun c -> let parts = c.Split(';') |> Array.map (fun p -> p.Trim()) in (parts[0], parts |> Array.skip 1 |> Array.filter (fun a -> not (a.StartsWith "expires")) |> Array.sort |> String.concat ";")) |> List.sort
        for path in [ $"/rooms/{ALL_TALK}"; $"/rooms/{HQ}"; $"/rooms/{ALL_TALK}/messages"; "/users/me/sidebar"; "/searches?q=the" ] do
            let send () = test.Send((getWithCookie path (cookie + "; last_room=" + string HQ)).With("accept", "text/html"))
            let! miss = send ()
            let! hit1 = send ()
            let! hit2 = send ()
            let h, _, _ = stats test
            out $"A9 {path}: miss {names miss} | hit {names hit2} | hits so far {h}"
            Assert.Equal<(string * string) list>(names miss, names hit2)
            Assert.Equal<(string * string) list>(names hit1, names hit2)
    }
