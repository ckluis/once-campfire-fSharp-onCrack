// onCrack: tests that try to break the versioned read cache (`src/Campfire.App/ReadCache.fs`): a page
// served from it must never be older than the last write that finished, nor anyone else's.
module Campfire.App.Tests.ReadCacheTests

open System
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

let private post (test: Test) (roomId: int64) (userId: int64) (body: string) : Message =
    write test (fun tx -> Message.create tx { NewMessage.create roomId userId with Body = Some $"<div>{body}</div>" })

let private hits (test: Test) : int64 =
    let hits, _, _ = ReadCache.stats test.App.Db.Versions
    hits

/// Gets `path` until it comes from the cache, and checks it did (so the test isn't passing vacuously): the
/// first visit to a room sets `last_room`, which is part of the key, so it can take two misses.
let private warm (browser: Browser) (path: string) : Task<Reply> =
    task {
        let hits () = hits browser.Test
        let! _ = browser.Get path
        let! first = browser.Get path
        let before = hits ()
        let! second = browser.Get path
        Assert.Equal(first.Status, second.Status)
        Assert.Equal(first.Text, second.Text)
        if first.Status = 200 && ReadCache.enabled then Assert.True(hits () > before, $"{path} was served from the cache")
        return second
    }

let private jason (test: Test) : Task<Browser> =
    task {
        let b = browser test "198.51.100.23"
        do! b.SignIn "jason@37signals.com"
        return b
    }

/// A post as the composer sends it (a turbo stream is the only template `create` has).
let private postForm (roomId: int64) (body: string) : Req =
    ((request "POST" $"/rooms/{roomId}/messages").With("accept", "text/vnd.turbo-stream.html, text/html, application/xhtml+xml"))
        .Form(formBody [ "message[body]", body ])

let private lastMessages (test: Test) (roomId: int64) : Message list =
    read test (fun conn -> Message.forRoom conn roomId |> List.sortBy (fun m -> m.CreatedAt.Microsecond, m.Id))

[<Fact>]
let ``a new message, an edit and a delete show on the next request of every cached page`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        let room = $"/rooms/{ALL_TALK}"
        let older = (List.item 60 (lastMessages test ALL_TALK)).Id
        let messagesPage = $"/rooms/{ALL_TALK}/messages?before={older}"
        let search = "/searches?q=quokka"
        for path in [ room; messagesPage; search; "/users/me/sidebar" ] do
            let! _ = warm david path
            ()

        let message = post test ALL_TALK JASON "quokka sighting"
        let! page = david.Get room
        Assert.Contains("quokka sighting", page.Text)
        let! found = david.Get search
        Assert.Contains("quokka sighting", found.Text)

        write test (fun tx -> Message.updateBody tx message "<div>quokka migration</div>" |> ignore)
        let! page = warm david room
        Assert.Contains("quokka migration", page.Text)
        Assert.DoesNotContain("quokka sighting", page.Text)
        let! found = warm david search
        Assert.Contains("quokka migration", found.Text)

        // A message on the older page: its edit must reach the messages page too.
        let onOlderPage = List.item 30 (lastMessages test ALL_TALK)
        write test (fun tx -> Message.updateBody tx onOlderPage "<div>wombat edited</div>" |> ignore)
        let! older = warm david messagesPage
        Assert.Contains("wombat edited", older.Text)

        write test (fun tx -> Message.destroy tx (read test (fun conn -> Message.find conn message.Id)))
        let! page = warm david room
        Assert.DoesNotContain("quokka", page.Text)
        let! found = warm david search
        Assert.DoesNotContain("quokka migration", found.Text)
    }

[<Fact>]
let ``a boost shows on the next request`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        let room = $"/rooms/{ALL_TALK}"
        let! _ = warm david room
        let last = List.last (lastMessages test ALL_TALK)
        write test (fun tx -> Boost.create tx last.Id JASON "🦘" |> ignore)
        let! page = warm david room
        Assert.Contains("🦘", page.Text)
    }

[<Fact>]
let ``a writer reads its own post through HTTP right away`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        let room = $"/rooms/{ALL_TALK}"
        let! _ = warm david room
        for i in 1..5 do
            let body = $"read-after-write {i}"
            let! posted = david.Write(postForm ALL_TALK body)
            Assert.True(posted.Status < 400, posted.Text)
            let! page = david.Get room
            Assert.Contains(body, page.Text)
    }

[<Fact>]
let ``two users never get each other's pages, and a non-member never gets a member's`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        let! jason = jason test
        let room = $"/rooms/{ALL_TALK}"
        let! davids = warm david room
        let! jasons = warm jason room
        Assert.Equal(200, jasons.Status)
        // The pages say who is signed in (the current user's meta tag), so each has its own.
        Assert.NotEqual<string>(davids.Text, jasons.Text)
        let! davidsAgain = david.Get room
        Assert.Equal(davids.Text, davidsAgain.Text)
        let! sidebarD = warm david "/users/me/sidebar"
        let! sidebarJ = warm jason "/users/me/sidebar"
        Assert.NotEqual<string>(sidebarD.Text, sidebarJ.Text)

        // Kevin isn't in All Talk: he is sent away, whatever David's cached page says.
        let kevin = browser test "198.51.100.40"
        do! kevin.SignIn "kevin@37signals.com"
        let! kevins = kevin.Get room
        Assert.Equal(302, kevins.Status)
        let! kevinsMessages = kevin.Get $"/rooms/{ALL_TALK}/messages"
        Assert.Equal(404, kevinsMessages.Status)
        // Nor is David in Kevin and Bender's direct room.
        let! other = david.Get $"/rooms/{DIRECT_KEVIN_BENDER}"
        Assert.Equal(302, other.Status)
    }

[<Fact>]
let ``removing a membership takes the room away at once: page, messages, sidebar and search`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        let room = $"/rooms/{QUIET_CORNER}"
        post test QUIET_CORNER KEVIN "platypus in the quiet corner" |> ignore
        let! page = warm david room
        Assert.Equal(200, page.Status)
        let! _ = warm david $"/rooms/{QUIET_CORNER}/messages"
        let! sidebar = warm david "/users/me/sidebar"
        Assert.Contains($"/rooms/{QUIET_CORNER}", sidebar.Text)
        let! found = warm david "/searches?q=platypus"
        Assert.Contains("platypus in the quiet corner", found.Text)

        let quiet = read test (fun conn -> Room.find conn QUIET_CORNER)
        write test (fun tx -> Room.revokeFrom tx quiet [ DAVID ])
        let! page = david.Get room
        Assert.Equal(302, page.Status)
        let! messages = david.Get $"/rooms/{QUIET_CORNER}/messages"
        Assert.Equal(404, messages.Status)
        let! sidebar = david.Get "/users/me/sidebar"
        Assert.DoesNotContain($"/rooms/{QUIET_CORNER}", sidebar.Text)
        let! found = david.Get "/searches?q=platypus"
        Assert.DoesNotContain("platypus in the quiet corner", found.Text)
    }

[<Fact>]
let ``a ban signs the user out and takes their messages off every cached page`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        let! jason = jason test
        let room = $"/rooms/{ALL_TALK}"
        post test ALL_TALK JASON "echidna by jason" |> ignore
        let! page = warm david room
        Assert.True(page.Text.Contains "echidna by jason", $"the room page has the message (status {page.Status}, {page.Text.Length} bytes, location {page.Location})")
        let! _ = warm jason room
        let! found = warm david "/searches?q=echidna"
        Assert.Contains("echidna by jason", found.Text)

        let user = read test (fun conn -> User.find conn JASON)
        write test (fun tx -> User.ban tx user |> ignore)
        // `remove_banned_content` runs as a job after the ban's commit.
        let messages = write test (fun tx -> User.removeBannedContent tx user)
        Assert.NotEmpty messages
        let! page = david.Get room
        Assert.DoesNotContain("echidna by jason", page.Text)
        let! found = david.Get "/searches?q=echidna"
        Assert.DoesNotContain("echidna by jason", found.Text)
        // Jason's session is gone: no page for him, cached or not.
        let! jasons = jason.Get room
        Assert.Equal(302, jasons.Status)
    }

[<Fact>]
let ``a user's name and the account's custom styles reach every cached page`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        let room = $"/rooms/{ALL_TALK}"
        let! _ = warm david room
        let! _ = warm david "/users/me/sidebar"
        // A direct room is named after the other people in it, on its page (not a cached fragment).
        let direct = $"/rooms/{DIRECT_DAVID_JASON}"
        let! before = warm david direct
        Assert.DoesNotContain("Jasonius Maximus", before.Text)
        let user = read test (fun conn -> User.find conn JASON)
        write test (fun tx -> User.update tx user { UserChanges.none with Name = Some "Jasonius Maximus" } |> ignore)
        let! after = warm david direct
        Assert.Contains("Jasonius Maximus", after.Text)
        let account = read test (fun conn -> Account.first conn) |> Option.get
        write test (fun tx ->
            tx.Conn.Execute("UPDATE accounts SET custom_styles = ? WHERE id = ?", [| S ".marker-zz9 { color: red }"; I account.Id |]) |> ignore)
        let! page = warm david room
        Assert.Contains(".marker-zz9", page.Text)
    }

[<Fact>]
let ``the involvement a user picks shows on their next sidebar, and only theirs`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        let! jason = jason test
        let! before = warm david "/users/me/sidebar"
        Assert.Contains($"/rooms/{ALL_TALK}", before.Text)
        let! jasonsBefore = warm jason "/users/me/sidebar"
        let! updated =
            david.Write((request "PATCH" $"/rooms/{ALL_TALK}/involvement").Form(formBody [ "involvement", "invisible" ]))
        Assert.True(updated.Status < 400)
        let! after = david.Get "/users/me/sidebar"
        Assert.DoesNotContain($"/rooms/{ALL_TALK}\"", after.Text)
        Assert.NotEqual<string>(before.Text, after.Text)
        let! jasonsAfter = jason.Get "/users/me/sidebar"
        Assert.Equal(jasonsBefore.Text, jasonsAfter.Text)
    }

[<Fact>]
let ``readers racing a writer never see a page older than the last post that finished`` () =
    task {
        use! test = bootSeeded "default"
        let room = $"/rooms/{ALL_TALK}"
        let readers = [ for _ in 1..6 -> david test ]
        let poster = david test
        let mutable acknowledged: string | null = null
        let mutable checks = 0
        let stop = new CancellationTokenSource()
        let hitsBefore = hits test
        let reader (browser: Browser) =
            task {
                while not stop.IsCancellationRequested do
                    // Whatever was acknowledged before the request starts must be on the page it gets.
                    let expected = Volatile.Read(&acknowledged)
                    let! page = browser.Get room
                    Assert.Equal(200, page.Status)
                    match expected with
                    | null -> ()
                    | body ->
                        Assert.Contains(body, page.Text)
                        Interlocked.Increment(&checks) |> ignore
            }
        let running = readers |> List.map (fun b -> Task.Run(fun () -> reader b :> Task))
        for i in 1..40 do
            let body = $"race-{i}-{Guid.NewGuid():N}"
            let! posted = poster.Write(postForm ALL_TALK body)
            Assert.True(posted.Status < 400, posted.Text)
            Volatile.Write(&acknowledged, body)
            do! Task.Delay 5
        do! Task.Delay 50
        stop.Cancel()
        do! Task.WhenAll running
        Assert.True(checks > 100, $"{checks} pages checked")
        Assert.True(not ReadCache.enabled || hits test > hitsBefore, "some of them came from the cache")
    }

/// onCrack C2, group commit: posts arriving together share the writer's transaction. Each must still get its own
/// message back, be stored once, be on the next page read, and leave the room in the order the writer took them.
[<Fact>]
let ``concurrent posts each answer with their own message, and every one is stored and shown`` () =
    task {
        use! test = bootSeeded "default"
        let room = $"/rooms/{ALL_TALK}"
        let before = lastMessages test ALL_TALK |> List.length
        let token (poster: int) (i: int) = $"grouped-{poster:D2}-{i:D2}-end"
        let poster (n: int) =
            task {
                let browser = david test
                let replies = ResizeArray<string * Reply>()
                for i in 1..6 do
                    let body = token n i
                    let! reply = browser.Write(postForm ALL_TALK body)
                    replies.Add((body, reply))
                return replies
            }
        let! all = Task.WhenAll [| for n in 1..16 -> Task.Run<ResizeArray<string * Reply>>(Func<Task<ResizeArray<string * Reply>>>(fun () -> poster n)) |]
        let replies = all |> Seq.concat |> List.ofSeq
        let tokens = replies |> List.map fst
        for body, reply in replies do
            Assert.Equal(200, reply.Status)
            Assert.Contains(body, reply.Text)
            // No one else's message in this answer.
            for other in tokens do
                if other <> body then Assert.DoesNotContain(other, reply.Text)
        let messages = lastMessages test ALL_TALK
        Assert.Equal(before + 96, messages.Length)
        let stored = read test (fun conn -> messages |> List.map (fun m -> m.Id, Message.bodyHtml conn m |> Option.defaultValue ""))
        for body in tokens do
            Assert.Equal(1, stored |> List.filter (fun (_, b) -> b.Contains body) |> List.length)
        // Each poster's own posts were committed in the order it sent them.
        for n in 1..16 do
            let mine = stored |> List.filter (fun (_, b) -> b.Contains $"grouped-{n:D2}-") |> List.sortBy fst |> List.map snd
            Assert.Equal<string list>([ for i in 1..6 -> token n i ], mine |> List.map (fun b -> tokens |> List.find b.Contains))
        let! page = (david test).Get room
        Assert.Contains(token 16 6, page.Text)
        let stats = test.App.Db.WriterStats
        Assert.True(stats.Writes >= 96L, $"{stats.Writes} writes in {stats.Groups} groups, largest {stats.Largest}")
    }

/// onCrack C2, group commit and broadcast order (the verifier's A5). Posts committed in one group were broadcast from
/// their own requests in whatever order those continued (92-100 adjacent inversions in 319 against 33-49 without group
/// commit), and the client places an appended message by its `data-sort-value` (`messages_controller.js#followingMessage`),
/// milliseconds, so posts of one millisecond showed live in arrival order and after a reload in commit order. Posts now
/// broadcast in commit order (`BroadcastOrder`): every broadcast arrives, in commit order, and so the client's placement is
/// commit order too.
[<Fact>]
let ``concurrent posts are all broadcast in commit order`` () =
    task {
        use! test = bootSeeded "default"
        let roomRow = read test (fun conn -> Room.find conn ALL_TALK)
        let name =
            Campfire.Cable.Naming.streamNameFrom [ Campfire.RailsCompat.GlobalId.toParam (Campfire.App.Channels.Gid.roomGid roomRow); "messages" ]
        let wake = Campfire.Cable.Wake()
        use sub = test.App.Cable.Hub.Subscribe(name, null, wake)
        let frames = Collections.Concurrent.ConcurrentQueue<string>()
        use stop = new CancellationTokenSource()
        let drain =
            Task.Run(fun () ->
                let mutable frame = Unchecked.defaultof<Campfire.Cable.Socket.Frame>
                let mutable fin = false
                while not fin do
                    match sub.TryRecv(&frame) with
                    | Campfire.Cable.RecvStatus.Got -> frames.Enqueue frame.Text
                    | Campfire.Cable.RecvStatus.Lagged -> frames.Enqueue "LAGGED"
                    | _ -> if stop.IsCancellationRequested then fin <- true else Thread.SpinWait 50)
        let poster (k: int) =
            task {
                let b = david test
                for i in 1..20 do
                    let! r = b.Write(postForm ALL_TALK $"ordr{k}x{i}y")
                    Assert.Equal(200, r.Status)
            }
        let! _ = Task.WhenAll [| for k in 1..16 -> Task.Run<unit>(fun () -> poster k) |]
        do! Task.Delay 300
        stop.Cancel()
        do! drain
        Assert.DoesNotContain("LAGGED", frames)
        let appended =
            [ for f in frames do
                  let m = Text.RegularExpressions.Regex.Match(f, """data-message-id=\\"(\d+)\\"[\s\S]*?data-sort-value=\\"(\d+)""")
                  if m.Success then int64 m.Groups[1].Value, int64 m.Groups[2].Value ]
        Assert.Equal(320, appended.Length)
        Assert.Equal(320, appended |> List.distinctBy fst |> List.length)
        // The client: each appended message moves before the run of earlier siblings with a larger sort value.
        let dom = ResizeArray<int64 * int64>()
        for (id, sort) in appended do
            let mutable at = dom.Count
            while at > 0 && sort < snd dom[at - 1] do
                at <- at - 1
            dom.Insert(at, (id, sort))
        // Ids follow commit order, and so do sort values.
        let byId = appended |> List.sortBy fst
        Assert.Equal<int64 list>(byId |> List.map snd |> List.sort, byId |> List.map snd)
        let pairs = dom |> List.ofSeq |> List.pairwise
        let outOfCommitOrder = pairs |> List.filter (fun ((a, _), (b, _)) -> b < a)
        let inversions = appended |> List.pairwise |> List.filter (fun ((a, _), (b, _)) -> b < a) |> List.length
        match TestContext.Current.TestOutputHelper with
        | null -> ()
        | output ->
            output.WriteLine
                $"broadcast order: {inversions} adjacent inversions in arrival order, {outOfCommitOrder.Length} left after the client's placement (same millisecond)"
        Assert.Equal(0, inversions)
        Assert.Empty outOfCommitOrder
        Assert.Equal(0L, test.App.Broadcasts.Order.Skipped)
    }

// onCrack C3: a gzipped answer carries its Content-Length (it is not chunked), and that length is the bytes sent.
let private gunzip (bytes: byte[]) : byte[] =
    use input = new System.IO.MemoryStream(bytes)
    use gz = new System.IO.Compression.GZipStream(input, System.IO.Compression.CompressionMode.Decompress)
    use output = new System.IO.MemoryStream()
    gz.CopyTo output
    output.ToArray()

[<Fact>]
let ``a gzipped page, cached or not, is sent with the length of the bytes it sends and decodes to the identity page`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        let room = $"/rooms/{ALL_TALK}"
        let gz (path: string) = david.Send((get path).With("accept-encoding", "gzip"))
        for path in [ room; "/users/me/sidebar"; "/searches?q=quokka"; "/searches?q=a" ] do
            // The first answers are misses (pieces or a buffer), the later ones come from the cache.
            let! identity = warm david path
            for _ in 1..4 do
                let! reply = gz path
                Assert.Equal(200, reply.Status)
                Assert.Equal(Some "gzip", reply.Header "content-encoding")
                // (With the cache off a page in parts is streamed, chunked; with it on, a page is a frozen member.)
                if ReadCache.enabled then
                    Assert.Equal(None, reply.Header "transfer-encoding")
                    Assert.Equal(Some(string reply.Body.Length), reply.Header "content-length")
                Assert.Equal<byte[]>(identity.Body, gunzip reply.Body)
        // A write's answer (a buffer, not a page): the same.
        let! posted = david.Write((postForm ALL_TALK "length check").With("accept-encoding", "gzip"))
        Assert.Equal(Some "gzip", posted.Header "content-encoding")
        Assert.Equal(Some(string posted.Body.Length), posted.Header "content-length")
        Assert.Contains("length check", System.Text.Encoding.UTF8.GetString(gunzip posted.Body))
        // And a client that doesn't take gzip gets the plain page with its own length.
        let! plain = david.Get room
        Assert.Equal(None, plain.Header "content-encoding")
        Assert.Equal(Some(string plain.Body.Length), plain.Header "content-length")
    }

[<Fact>]
let ``a HEAD for a gzipped page has no body and keeps answering as it did`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        let room = $"/rooms/{ALL_TALK}"
        let! _ = warm david room
        let! reply = david.Send((request "HEAD" room).With("accept-encoding", "gzip"))
        Assert.Equal(200, reply.Status)
        Assert.Empty reply.Body
    }

// --- The signed-in user, read by authentication before the page takes its counters ---------------------
//
// Authentication reads the user (name, avatar, role) before the action takes the page's counters. A change
// to that user committed in between must not leave a page rendered from the old row and kept under the new
// counters (the verifier's A1, A1b and A1c: 50-93 stale pages in 1,500 writes before the fix, and the stale
// page served again by the next request). Twelve browsers read the page while the user changes; after each
// change returns, a fresh request must show it.

/// Changes David `rounds` times with `change i` while twelve browsers read `path`, checking after each change
/// that a fresh request shows it (`shows i page`); returns the stale pages it saw.
let private userChangesUnderReaders
    (test: Test)
    (path: string)
    (rounds: int)
    (change: int -> unit)
    (shows: int -> string -> bool)
    : Task<string list> =
    task {
        let readers = [ for _ in 1..12 -> david test ]
        let checker = david test
        for b in checker :: readers do
            let! _ = b.Get path
            ()
        use stop = new CancellationTokenSource()
        let reader (b: Browser) =
            task {
                while not stop.IsCancellationRequested do
                    let! _ = b.Get path
                    ()
            }
        let running = readers |> List.map (fun b -> Task.Run(fun () -> reader b :> Task))
        let stale = ResizeArray<string>()
        for i in 1..rounds do
            change i
            let! page = checker.Get path
            Assert.Equal(200, page.Status)
            if not (shows i page.Text) then stale.Add $"round {i}"
        stop.Cancel()
        do! Task.WhenAll running
        if ReadCache.enabled then Assert.True(hits test > 0L, "the readers were served from the cache")
        return List.ofSeq stale
    }

let private renameDavid (test: Test) (name: string) : unit =
    let user = read test (fun conn -> User.find conn DAVID)
    write test (fun tx -> User.update tx user { UserChanges.none with Name = Some name } |> ignore)

[<Fact>]
let ``a rename of the signed-in user shows on the next room page while others read it`` () =
    task {
        use! test = bootSeeded "default"
        let meta (name: string) = $"<meta name=\"current-user-name\" content=\"{name}\""
        let template (html: string) =
            let m =
                Text.RegularExpressions.Regex.Match(
                    html,
                    "data-messages-target=\"template\">[\\s\\S]*?<span class=\"message__author\"><strong>([^<]*)</strong>"
                )
            if m.Success then m.Groups[1].Value else "<none>"
        let! stale =
            userChangesUnderReaders test $"/rooms/{ALL_TALK}" 1000 (fun i -> renameDavid test $"David {i}") (fun i html ->
                html.Contains(meta $"David {i}") && template html = $"David {i}")
        Assert.True(stale.IsEmpty, $"stale room pages after a committed rename: {stale}")
    }

[<Fact>]
let ``a rename of the signed-in user shows on the next sidebar while others read it`` () =
    task {
        use! test = bootSeeded "default"
        let! stale =
            userChangesUnderReaders test "/users/me/sidebar" 1000 (fun i -> renameDavid test $"Davo {i}x") (fun i html ->
                html.Contains $"Davo {i}x")
        Assert.True(stale.IsEmpty, $"stale sidebars after a committed rename: {stale}")
    }

[<Fact>]
let ``a role change of the signed-in user shows on the next sidebar while others read it`` () =
    task {
        // On the restricted seed only administrators get the sidebar's New Chat Room button.
        use! test = bootSeeded "restricted"
        let roleOf i = if i % 2 = 0 then Role.Administrator else Role.Member
        let! stale =
            userChangesUnderReaders
                test
                "/users/me/sidebar"
                1000
                (fun i ->
                    write test (fun tx ->
                        tx.Conn.Execute("UPDATE users SET role = ? WHERE id = ?", [| I(int64 (int (roleOf i))); I DAVID |]) |> ignore))
                (fun i html -> html.Contains "New Chat Room" = (roleOf i = Role.Administrator))
        Assert.True(stale.IsEmpty, $"sidebars disagreeing with the committed role: {stale}")
    }

[<Fact>]
let ``room pages for rooms nobody has keep no counter per id`` () =
    task {
        // The verifier's A2: a signed-in user asking for /rooms/N and /rooms/N/messages with a new N each time
        // made a version counter per N, never removed. Ids a stripe apart now share one counter.
        use! test = bootSeeded "default"
        let versions = test.App.Db.Versions
        let before = versions.RoomCells
        let cookie = davidCookie ()
        let stripe = int64 Versions.RoomStripes
        for i in 0L .. 1999L do
            let id = 900_000_000L * stripe + i * stripe
            // No cookie jar: a redirect's flash would make the next request skip the cache.
            let path = if i % 2L = 0L then $"/rooms/{id}" else $"/rooms/{id}/messages"
            let! reply = test.Send((getWithCookie path cookie).With("accept", "text/html"))
            Assert.True(reply.Status = 302 || reply.Status = 404, $"{path}: {reply.Status}")
        Assert.True(versions.RoomCells - before <= 1, $"{versions.RoomCells - before} counters for 2,000 rooms that don't exist")
    }
