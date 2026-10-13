// onCrack (unit R2.2): tests that try to break the post path's shortcuts: unread marks only where they change state
// (`PostPath.UnreadSkip`), the search index's text worked out before the write (`PostPath.PlainTextEarly`), and the
// sidebar that shows the unread state served from the read cache.
module Campfire.App.Tests.PostPathTests

open System
open System.Threading.Tasks
open Xunit
open Campfire.App.Tests.Support
open Campfire.Db

let private unwrap (result: Result<'T, DbError>) : 'T =
    match result with
    | Ok value -> value
    | Error e -> failwith (DbError.display e)

let private read (test: Test) (f: Conn -> 'T) : 'T = test.App.Db.ReadBlocking f |> unwrap

let private postForm (roomId: int64) (body: string) : Req =
    ((request "POST" $"/rooms/{roomId}/messages").With("accept", "text/vnd.turbo-stream.html, text/html, application/xhtml+xml"))
        .Form(formBody [ "message[body]", body ])

let private membership (test: Test) (roomId: int64) (userId: int64) : Membership =
    read test (fun conn -> (Membership.findByRoomAndUser conn roomId userId).Value)

let private lastMessage (test: Test) (roomId: int64) : Message =
    read test (fun conn -> Message.forRoom conn roomId |> List.maxBy (fun m -> m.Id))

/// Whether the sidebar's link to `roomId` (`dom_id(room, :list)`) carries the `unread` class.
let private unreadIn (sidebar: string) (roomId: int64) : bool =
    let found = Text.RegularExpressions.Regex.Match(sidebar, $"id=\"list_[a-z_]+_{roomId}\"")
    Assert.True(found.Success, $"room {roomId} is in the sidebar")
    let at = found.Index
    let start = sidebar.LastIndexOf("<a", at, StringComparison.Ordinal)
    let tag = sidebar.Substring(start, sidebar.IndexOf('>', at) - start)
    // `data-badge-dot-target="unread"` is on every room link; the state is the class.
    let classes = Text.RegularExpressions.Regex.Match(tag, "class=\"([^\"]*)\"").Groups[1].Value
    classes.Split(' ') |> Array.contains "unread"

let private jason (test: Test) : Task<Browser> =
    task {
        let b = browser test "198.51.100.24"
        do! b.SignIn "jason@37signals.com"
        return b
    }

let private post (david: Browser) (roomId: int64) (body: string) : Task<unit> =
    task {
        let! reply = david.Write(postForm roomId body)
        Assert.True((reply.Status = 200), reply.Text)
    }

[<Fact>]
let ``a post marks unread who wasn't, keeps who was, and every member's cached sidebar shows it at once`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        let! jason = jason test
        // Jason's sidebar, from the cache, with HQ read.
        let! _ = jason.Get "/users/me/sidebar"
        let! before = jason.Get "/users/me/sidebar"
        Assert.False(unreadIn before.Text HQ, "HQ starts read")

        do! post david HQ "first"
        let first = lastMessage test HQ
        let! after = jason.Get "/users/me/sidebar"
        Assert.True(unreadIn after.Text HQ, "the post shows on Jason's next sidebar")
        Assert.Equal(Some first.CreatedAt, (membership test HQ JASON).UnreadAt)
        let kevin = membership test HQ KEVIN
        Assert.Equal(Some first.CreatedAt, kevin.UnreadAt)

        // A second post leaves the rows already unread as they are (Rails rewrites them with its time; only
        // `unread?` reads the column), and the sidebars still show the room unread.
        do! post david HQ "second"
        let second = lastMessage test HQ
        Assert.True(second.CreatedAt > first.CreatedAt)
        Assert.Equal(Some first.CreatedAt, (membership test HQ JASON).UnreadAt)
        Assert.Equal(kevin.UpdatedAt, (membership test HQ KEVIN).UpdatedAt)
        let! still = jason.Get "/users/me/sidebar"
        Assert.True(unreadIn still.Text HQ, "still unread after the second post")

        // Jason reads the room (as his presence in it does); the next post marks him again, with that post's time.
        test.App.Db.WriteBlocking(fun tx -> Membership.read tx (membership test HQ JASON) |> ignore) |> unwrap
        Assert.Equal(None, (membership test HQ JASON).UnreadAt)
        let! read = jason.Get "/users/me/sidebar"
        Assert.False(unreadIn read.Text HQ, "read after visiting the room")
        do! post david HQ "third"
        let third = lastMessage test HQ
        Assert.Equal(Some third.CreatedAt, (membership test HQ JASON).UnreadAt)
        let! again = jason.Get "/users/me/sidebar"
        Assert.True(unreadIn again.Text HQ, "unread again after the third post")
        // The poster's own row is never marked.
        Assert.Equal(None, (membership test HQ DAVID).UnreadAt)
    }

[<Fact>]
let ``a post into a direct room still rewrites every other member's row, for the sidebar fragment keyed by it`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        do! post david DIRECT_DAVID_JASON "one"
        let first = lastMessage test DIRECT_DAVID_JASON
        let marked = membership test DIRECT_DAVID_JASON JASON
        Assert.Equal(Some first.CreatedAt, marked.UnreadAt)
        do! post david DIRECT_DAVID_JASON "two"
        let second = lastMessage test DIRECT_DAVID_JASON
        let remarked = membership test DIRECT_DAVID_JASON JASON
        Assert.Equal(Some second.CreatedAt, remarked.UnreadAt)
        Assert.True(remarked.UpdatedAt > marked.UpdatedAt, "the row's updated_at moved, so its sidebar fragment is made again")
    }

[<Fact>]
let ``the search index's text, worked out before the write, is the stored body's plain text`` () =
    task {
        use! test = bootSeeded "default"
        let david = david test
        for body in
            [ "<div>plain words</div>"
              "<div><strong>bold</strong> and <em>em</em><br>line two</div>"
              "<ul><li>one</li><li>two &amp; three</li></ul><pre>code  here</pre>"
              "<div>   </div>" ] do
            do! post david ALL_TALK body
            let message = lastMessage test ALL_TALK
            let indexed, recomputed =
                read test (fun conn ->
                    let indexed =
                        conn.QueryOne("SELECT body FROM message_search_index WHERE rowid = ?", [| I message.Id |], (fun r -> r.Text 0)).Value
                    indexed, Message.plainTextBody conn test.App.Db.Env.RichText message)
            Assert.Equal(recomputed, indexed)
        // And search finds a post at once.
        do! post david ALL_TALK "<div>zyzzyvaquokka</div>"
        let! found = david.Get "/searches?q=zyzzyvaquokka"
        Assert.Contains("zyzzyvaquokka", found.Text)
    }
