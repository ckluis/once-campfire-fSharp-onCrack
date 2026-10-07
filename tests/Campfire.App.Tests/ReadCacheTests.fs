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
        Assert.Contains("echidna by jason", page.Text)
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
