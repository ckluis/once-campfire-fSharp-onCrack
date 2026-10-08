// onCrack R2.3: tests that try to break the front server's fast path (`Campfire.Kit.FastCandidate`, `FastStore` in
// `src/Campfire.Kit/Front/Handler.fs`): an answer replayed before routing, the kit adapter and cookie parsing must be the answer the
// app would give that request now, for that session, never anyone else's, never across a write, a sign-out or a due session refresh.
// Every app here is served behind the front server (`bootSeededWith true`), as in production.
module Campfire.App.Tests.FastPathTests

open System
open System.IO
open System.IO.Compression
open System.Text.RegularExpressions
open System.Threading
open System.Threading.Tasks
open Xunit
open Campfire.App
open Campfire.App.Tests.Support
open Campfire.Db
open Campfire.Kit

let private unwrap (result: Result<'T, DbError>) : 'T =
    match result with
    | Ok value -> value
    | Error e -> failwith (DbError.display e)

let private write (test: Test) (f: Tx -> 'T) : 'T = test.App.Db.WriteBlocking f |> unwrap

let private read (test: Test) (f: Conn -> 'T) : 'T = test.App.Db.ReadBlocking f |> unwrap

let private post (test: Test) (roomId: int64) (userId: int64) (body: string) : Message =
    write test (fun tx -> Message.create tx { NewMessage.create roomId userId with Body = Some $"<div>{body}</div>" })

let private boot () = bootSeededWith true [] "default"

let private store (test: Test) : FastStore = nonNull (nonNull test.Host.Front).Fast

let private fastHits (test: Test) : int64 = Volatile.Read(&(store test).Hits)

let private enabled = FastCandidate.enabled

/// Gets `path` until its answer is a replay, and checks it was (so a test isn't passing vacuously): the first visit can set
/// `last_room`, then the read cache keeps the page, then the fast path the answer, then it replays.
let private warmFast (browser: Browser) (path: string) : Task<Reply> =
    task {
        let test = browser.Test
        let mutable reply = Unchecked.defaultof<Reply>
        for _ in 1..4 do
            let! r = browser.Get path
            reply <- r
        let before = fastHits test
        let! last = browser.Get path
        Assert.Equal(reply.Status, last.Status)
        Assert.Equal(reply.Text, last.Text)
        if enabled && last.Status = 200 then Assert.True(fastHits test > before, $"{path} was replayed by the fast path")
        return last
    }

let private postForm (roomId: int64) (body: string) : Req =
    ((request "POST" $"/rooms/{roomId}/messages").With("accept", "text/vnd.turbo-stream.html, text/html, application/xhtml+xml"))
        .Form(formBody [ "message[body]", body ])

let private lastMessages (test: Test) (roomId: int64) : Message list =
    read test (fun conn -> Message.forRoom conn roomId |> List.sortBy (fun m -> m.CreatedAt.Microsecond, m.Id))

let private jason (test: Test) : Task<Browser> =
    task {
        let b = browser test "198.51.100.23"
        do! b.SignIn "jason@37signals.com"
        return b
    }

/// The headers that differ between two answers to one request by design.
let private volatileHeader (name: string) =
    [ "date"; "x-request-id"; "x-runtime"; "set-cookie" ] |> List.contains (name.ToLowerInvariant())

let private stable (reply: Reply) = reply.Headers |> List.filter (fun (k, _) -> not (volatileHeader k))

let private uuid = Regex("^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

let private gunzip (bytes: byte[]) : string =
    use input = new GZipStream(new MemoryStream(bytes), CompressionMode.Decompress)
    use output = new StreamReader(input)
    output.ReadToEnd()

[<Fact>]
let ``a replay is the app's answer: same status, headers and body, a fresh request id and runtime`` () =
    task {
        use! test = boot ()
        let david = david test
        let older = (List.item 60 (lastMessages test ALL_TALK)).Id
        for path in [ $"/rooms/{ALL_TALK}"; $"/rooms/{ALL_TALK}/messages?before={older}"; "/users/me/sidebar"; "/searches?q=quokka" ] do
            let! first = david.Get path
            let! second = david.Get path
            let! replay = warmFast david path
            Assert.Equal(200, replay.Status)
            Assert.Equal(second.Text, replay.Text)
            Assert.Equal<(string * string) list>(stable second, stable replay)
            Assert.Empty(replay.SetCookies)
            let ids = [ first; second; replay ] |> List.map (fun r -> (r.Header "x-request-id").Value)
            for id in ids do
                Assert.Matches(uuid, id)
            Assert.Equal(3, ids |> List.distinct |> List.length)
            Assert.True((replay.Header "x-runtime").IsSome)
        // A request id the client sends is the one answered, as ActionDispatch::RequestId does.
        let! echoed = david.Send((get "/users/me/sidebar").With("x-request-id", "abc-123!?"))
        Assert.Equal(Some "abc-123", echoed.Header "x-request-id")
    }

[<Fact>]
let ``a gzipped replay is the same member, and a request that differs in any header gets its own answer`` () =
    task {
        use! test = boot ()
        let david = david test
        let room = $"/rooms/{ALL_TALK}"
        let! plain = warmFast david room
        // Same session and path, gzip: its own entry, which decodes to the same page.
        let gz (r: Req) = r.With("accept-encoding", "gzip")
        let mutable zipped = Unchecked.defaultof<Reply>
        for _ in 1..5 do
            let! r = david.Send(gz (get room))
            zipped <- r
        Assert.Equal(Some "gzip", zipped.Header "content-encoding")
        Assert.Equal(plain.Text, gunzip zipped.Body)
        Assert.Equal(Some(string zipped.Body.Length), zipped.Header "content-length")
        // A Turbo-Frame request gets the frame layout, never the replay of the whole page.
        let! frame = david.Send((get room).With("turbo-frame", "messages"))
        Assert.Equal(200, frame.Status)
        Assert.NotEqual<string>(plain.Text, frame.Text)
        // A conditional request for the page it holds is answered 304 by the app.
        let etag = (plain.Header "etag").Value
        let! notModified = david.Send((get room).With("if-none-match", etag))
        Assert.Equal(304, notModified.Status)
        // HEAD and a GET with a body are never replayed.
        let before = fastHits test
        let! head = david.Send(request "HEAD" room)
        Assert.Equal(200, head.Status)
        Assert.Empty(head.Body)
        let! withBody = david.Send((get room).WithBody("bot_key=nope"))
        Assert.Equal(200, withBody.Status)
        Assert.Equal(before, fastHits test)
    }

[<Fact>]
let ``a new message, an edit and a delete show on the next request of every replayed page`` () =
    task {
        use! test = boot ()
        let david = david test
        let room = $"/rooms/{ALL_TALK}"
        let older = (List.item 60 (lastMessages test ALL_TALK)).Id
        let messagesPage = $"/rooms/{ALL_TALK}/messages?before={older}"
        let search = "/searches?q=quokka"
        for path in [ room; messagesPage; search; "/users/me/sidebar" ] do
            let! _ = warmFast david path
            ()
        let message = post test ALL_TALK JASON "quokka sighting"
        let! page = david.Get room
        Assert.Contains("quokka sighting", page.Text)
        let! found = david.Get search
        Assert.Contains("quokka sighting", found.Text)
        write test (fun tx -> Message.updateBody tx message "<div>quokka migration</div>" |> ignore)
        let! page = warmFast david room
        Assert.Contains("quokka migration", page.Text)
        let! found = warmFast david search
        Assert.Contains("quokka migration", found.Text)
        let onOlderPage = List.item 30 (lastMessages test ALL_TALK)
        write test (fun tx -> Message.updateBody tx onOlderPage "<div>wombat edited</div>" |> ignore)
        let! older = david.Get messagesPage
        Assert.Contains("wombat edited", older.Text)
        write test (fun tx -> Message.destroy tx (read test (fun conn -> Message.find conn message.Id)))
        let! page = david.Get room
        Assert.DoesNotContain("quokka", page.Text)
        let! found = david.Get search
        Assert.DoesNotContain("quokka migration", found.Text)
    }

[<Fact>]
let ``two users never get each other's replays, and a non-member is still sent away`` () =
    task {
        use! test = boot ()
        let david = david test
        let! jason = jason test
        let room = $"/rooms/{ALL_TALK}"
        let! davids = warmFast david room
        let! jasons = warmFast jason room
        Assert.NotEqual<string>(davids.Text, jasons.Text)
        let! davidsAgain = david.Get room
        Assert.Equal(davids.Text, davidsAgain.Text)
        let kevin = browser test "198.51.100.40"
        do! kevin.SignIn "kevin@37signals.com"
        let! kevins = kevin.Get room
        Assert.Equal(302, kevins.Status)
        // Kevin with David's path but his own cookies, and David's own cookies with a different header: never David's replay.
        let! kevinsMessages = kevin.Get $"/rooms/{ALL_TALK}/messages"
        Assert.Equal(404, kevinsMessages.Status)
    }

[<Fact>]
let ``signing out stops the replay of the session's pages at once`` () =
    task {
        use! test = boot ()
        let b = browser test "198.51.100.50"
        do! b.SignIn "david@37signals.com"
        let room = $"/rooms/{ALL_TALK}"
        let! _ = warmFast b room
        let! _ = warmFast b "/users/me/sidebar"
        let cookie = b.Cookie "session_token" |> Option.get
        let session = b.Cookie "_campfire_session"
        let header =
            match session with
            | Some s -> $"session_token={cookie}; _campfire_session={s}; last_room={ALL_TALK}"
            | None -> $"session_token={cookie}; last_room={ALL_TALK}"
        let! signedOut = b.Form("delete", "/session", [])
        Assert.True(signedOut.Status < 400, signedOut.Text)
        // The old cookie, replayed byte for byte, no longer authenticates.
        let stale = Browser(test, Some "198.51.100.50")
        stale.AbsorbCookieHeader header
        let! page = stale.Get room
        Assert.Equal(302, page.Status)
        let! sidebar = stale.Get "/users/me/sidebar"
        Assert.Equal(302, sidebar.Status)
    }

[<Fact>]
let ``a ban, a removed membership and a deactivation stop the replay at once`` () =
    task {
        use! test = boot ()
        let david = david test
        let! jason = jason test
        let room = $"/rooms/{QUIET_CORNER}"
        let! page = warmFast david room
        Assert.Equal(200, page.Status)
        let! _ = warmFast david $"/rooms/{QUIET_CORNER}/messages"
        let quiet = read test (fun conn -> Room.find conn QUIET_CORNER)
        write test (fun tx -> Room.revokeFrom tx quiet [ DAVID ])
        let! page = david.Get room
        Assert.Equal(302, page.Status)
        let! messages = david.Get $"/rooms/{QUIET_CORNER}/messages"
        Assert.Equal(404, messages.Status)

        let! _ = warmFast jason $"/rooms/{ALL_TALK}"
        let user = read test (fun conn -> User.find conn JASON)
        write test (fun tx -> User.ban tx user |> ignore)
        let! jasons = jason.Get $"/rooms/{ALL_TALK}"
        Assert.Equal(302, jasons.Status)
    }

[<Fact>]
let ``a replay sets a permanent cookie with the expiry of its own moment`` () =
    task {
        use! test = boot ()
        let david = david test
        // David's own cookies, but no `last_room`: every answer to the room page sets it, 20 years from when it is sent.
        let cookie = davidCookie ()
        let room = $"/rooms/{ALL_TALK}"
        let before = fastHits test
        let mutable replies = []
        for _ in 1..6 do
            let! reply = test.Send((get room).With("cookie", cookie).With("user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36").With("accept", "text/html"))
            replies <- reply :: replies
        Assert.True(not enabled || fastHits test > before, "some were replays")
        for reply in replies do
            Assert.Equal(200, reply.Status)
            let set = reply.SetCookies |> List.filter (fun c -> c.StartsWith "last_room=")
            Assert.Single set |> ignore
            let m = Regex.Match(set.Head, "expires=([^;]+)")
            let expires = DateTimeOffset.Parse(m.Groups[1].Value)
            let expected = DateTimeOffset.UtcNow.AddYears 20
            Assert.True(abs (expires - expected).TotalSeconds < 3.0, $"{set.Head} expires 20 years from now")
            Assert.Equal($"last_room={ALL_TALK}; path=/; expires={m.Groups[1].Value}; samesite=lax", set.Head)
        ignore david
    }

[<Fact>]
let ``a session due for its activity refresh is refreshed, not replayed`` () =
    task {
        use! test = boot ()
        let b = browser test "198.51.100.60"
        do! b.SignIn "david@37signals.com"
        let room = $"/rooms/{ALL_TALK}"
        // Last active an hour ago less three seconds: the refresh falls due while the page is being replayed.
        let lastActive = Timestamp.FromDateTimeOffset(DateTimeOffset.UtcNow.AddSeconds(-3600.0 + 3.0))
        write test (fun tx -> tx.Conn.Execute("UPDATE sessions SET last_active_at = ? WHERE user_id = ?", [| S(lastActive.ToDb()); I DAVID |]) |> ignore)
        let! _ = warmFast b room
        do! Task.Delay 4000
        let before = fastHits test
        let! page = b.Get room
        Assert.Equal(200, page.Status)
        Assert.Equal(before, fastHits test)
        Assert.Contains(page.SetCookies, fun c -> c.StartsWith "session_token=")
        let refreshed =
            read test (fun conn -> conn.QueryAll("SELECT last_active_at FROM sessions WHERE user_id = ?", [| I DAVID |], fun r -> r.Timestamp 0))
        Assert.Contains(refreshed, fun at -> at.Microsecond > lastActive.Microsecond + 3_000_000L)
    }

[<Fact>]
let ``readers racing a writer never get a replay older than the last post that finished`` () =
    task {
        use! test = boot ()
        let room = $"/rooms/{ALL_TALK}"
        let readers = [ for _ in 1..6 -> david test ]
        let poster = david test
        let! _ = warmFast readers.Head room
        let mutable acknowledged: string | null = null
        let mutable checks = 0
        let stop = new CancellationTokenSource()
        let before = fastHits test
        let reader (browser: Browser) =
            task {
                while not stop.IsCancellationRequested do
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
        Assert.True(not enabled || fastHits test > before, "some of them were replays")
    }
