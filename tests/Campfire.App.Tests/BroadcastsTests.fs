// Port of rust/crates/campfire/src/channels/tests/broadcasts_test.rs
//
// The broadcasts' streams, targets and markup, as delivered to subscribers.
module Campfire.App.Tests.BroadcastsTests

open System.Text.Json
open System.Threading.Tasks
open Xunit
open Campfire.App.Channels
open Campfire.Cable
open Campfire.Db
open Campfire.RailsCompat
open Campfire.App.Tests.ChannelsSupport

let private obj' (entries: (string * Value) list) : Value = Value.Object entries

/// The `<turbo-stream>` a delivery frame carries.
let private turboStream (frame: string) : string =
    use document = JsonDocument.Parse frame
    match document.RootElement.GetProperty("message").GetString() with
    | null -> failwith "a Turbo Stream string"
    | text -> text

let private roomMessages (app: TestApp) (client: Client) (room: string) : Task<string> =
    task {
        let! room = app.Room room
        let signed = app.SignedStreamName [ GlobalId.toParam (Gid.roomGid room); "messages" ]
        let channel = identifier (obj' [ "channel", Value.String "RoomMessagesChannel"; "signed_stream_name", Value.String signed ])
        do! client.Confirm channel
        return channel
    }

let private turbo (app: TestApp) (client: Client) (streamables: string list) : Task<string> =
    task {
        let channel =
            identifier (obj' [ "channel", Value.String "Turbo::StreamsChannel"; "signed_stream_name", Value.String(app.SignedStreamName streamables) ])
        do! client.Confirm channel
        return channel
    }

let private ok (result: Result<'T, DbError>) : 'T =
    match result with
    | Ok value -> value
    | Error error -> failwith (DbError.display error)

[<Fact>]
let ``message broadcasts`` () =
    task {
        use! app = start ()
        use! kevin = app.Connect "kevin"
        let! _ = roomMessages app kevin "designers"
        let unreads = identifier (obj' [ "channel", Value.String "UnreadRoomsChannel" ])
        do! kevin.Confirm unreads

        let! designers = app.Room "designers"
        let! message = app.Message "second"

        let! created = app.Db.Read(fun conn -> app.Broadcasts.MessageCreate(conn, designers, message, fakePartials))
        ok created
        let! frame = kevin.NextText()
        Assert.Equal(
            $"""<turbo-stream action="append" target="messages_rooms_closed_{designers.Id}"><template><div id="message_0002">message {message.Id}</div></template></turbo-stream>""",
            turboStream frame
        )
        let! frame = kevin.NextText()
        Assert.Equal(delivery unreads $"""{{"roomId":{designers.Id}}}""", frame)

        app.Broadcasts.MessageReplace(designers, message, fakePartials)
        let! frame = kevin.NextText()
        Assert.Equal(
            $"""<turbo-stream maintain_scroll="true" action="replace" target="presentation_message_0002"><template><div>presentation {message.Id} & more</div></template></turbo-stream>""",
            turboStream frame
        )

        app.Broadcasts.MessageRemove(designers, message)
        let! frame = kevin.NextText()
        Assert.Equal("""<turbo-stream action="remove" target="message_0002"></turbo-stream>""", turboStream frame)
        do! kevin.AssertSilent()
    }

[<Fact>]
let ``boost broadcasts`` () =
    task {
        use! app = start ()
        use! kevin = app.Connect "kevin"
        let! _ = roomMessages app kevin "designers"
        let! designers = app.Room "designers"
        let! message = app.Message "first"
        let! boost = app.Boost "first"

        app.Broadcasts.BoostCreate(designers, message, boost, fakePartials)
        let! frame = kevin.NextText()
        Assert.Equal(
            $"""<turbo-stream maintain_scroll="true" action="append" target="boosts_message_0001"><template><div>boost {boost.Id}</div></template></turbo-stream>""",
            turboStream frame
        )

        app.Broadcasts.BoostRemove(designers, boost)
        let! frame = kevin.NextText()
        Assert.Equal($"""<turbo-stream action="remove" target="boost_{boost.Id}"></turbo-stream>""", turboStream frame)
    }

[<Fact>]
let ``room list broadcasts`` () =
    task {
        use! app = start ()
        use! jz = app.Connect "jz"
        let! _ = turbo app jz [ "rooms" ]
        let ownRooms = GlobalId.toParam (Gid.userGid (id "jz"))
        let! _ = turbo app jz [ ownRooms; "rooms" ]

        let! hq = app.Room "hq"
        app.Broadcasts.OpenRoomCreate(hq, fakePartials)
        let! frame = jz.NextText()
        Assert.Equal(
            $"""<turbo-stream action="prepend" target="shared_rooms"><template><li>shared {hq.Id}</li></template></turbo-stream>""",
            turboStream frame
        )

        app.Broadcasts.OpenRoomUpdate(hq, fakePartials)
        let! frame = jz.NextText()
        Assert.Equal(
            $"""<turbo-stream action="replace" target="list_rooms_open_{hq.Id}"><template><li>shared {hq.Id}</li></template></turbo-stream>""",
            turboStream frame
        )

        app.Broadcasts.RoomRemove hq
        let! frame = jz.NextText()
        Assert.Equal($"""<turbo-stream action="remove" target="list_rooms_open_{hq.Id}"></turbo-stream>""", turboStream frame)

        // Closed rooms go to each member's own stream: jz is in designers, not the watercooler.
        let! designers = app.Room "designers"
        let! watercooler = app.Room "watercooler"
        let! closed =
            app.Db.Read(fun conn ->
                app.Broadcasts.ClosedRoomCreate(conn, watercooler, fakePartials)
                app.Broadcasts.ClosedRoomCreate(conn, designers, fakePartials)
                app.Broadcasts.ClosedRoomUpdate(conn, designers, fakePartials))
        ok closed
        let! frame = jz.NextText()
        Assert.Equal(
            $"""<turbo-stream action="prepend" target="shared_rooms"><template><li>shared {designers.Id}</li></template></turbo-stream>""",
            turboStream frame
        )
        let! frame = jz.NextText()
        Assert.Equal(
            $"""<turbo-stream action="replace" target="list_rooms_closed_{designers.Id}"><template><li>shared {designers.Id}</li></template></turbo-stream>""",
            turboStream frame
        )
        do! jz.AssertSilent()
    }

[<Fact>]
let ``direct room and involvement broadcasts`` () =
    task {
        use! app = start ()
        use! kevin = app.Connect "kevin"
        let ownRooms = GlobalId.toParam (Gid.userGid (id "kevin"))
        let! _ = turbo app kevin [ ownRooms; "rooms" ]

        let! direct = app.Room "bender_and_kevin"
        let! created = app.Db.Read(fun conn -> app.Broadcasts.DirectRoomCreate(conn, direct, fakePartials))
        ok created
        let! membership = app.Membership("bender_and_kevin", "kevin")
        let membership = membership.Value
        let! frame = kevin.NextText()
        Assert.Equal(
            $"""<turbo-stream action="prepend" target="direct_rooms"><template><li>direct {membership.Id}</li></template></turbo-stream>""",
            turboStream frame
        )
        do! kevin.AssertSilent()

        let! designers = app.Room "designers"
        let! membership = app.Membership("designers", "kevin")
        let membership = membership.Value

        // Direct rooms never change the list.
        Assert.True((app.Broadcasts.InvolvementChange(direct, membership, Some Invisible, fakePartials)).IsOk)
        do! kevin.AssertSilent()

        let membership = { membership with Involvement = Some Invisible }
        Assert.True((app.Broadcasts.InvolvementChange(designers, membership, Some Mentions, fakePartials)).IsOk)
        let! frame = kevin.NextText()
        Assert.Equal($"""<turbo-stream action="remove" target="list_rooms_closed_{designers.Id}"></turbo-stream>""", turboStream frame)

        let membership = { membership with Involvement = Some Everything }
        Assert.True((app.Broadcasts.InvolvementChange(designers, membership, Some Invisible, fakePartials)).IsOk)
        let! frame = kevin.NextText()
        Assert.Equal(
            $"""<turbo-stream action="prepend" target="shared_rooms"><template><li>shared {designers.Id}</li></template></turbo-stream>""",
            turboStream frame
        )

        Assert.True((app.Broadcasts.InvolvementChange(designers, membership, Some Mentions, fakePartials)).IsOk)
        do! kevin.AssertSilent()
        Assert.True((app.Broadcasts.InvolvementChange(designers, membership, None, fakePartials)).IsError)
    }

[<Fact>]
let ``broadcast frames use active support json escaping`` () =
    task {
        use! app = start ()
        use! kevin = app.Connect "kevin"
        let! channel = roomMessages app kevin "designers"
        let! designers = app.Room "designers"
        let! message = app.Message "first"
        app.Broadcasts.MessageReplace(designers, message, fakePartials)
        let! frame = kevin.NextText()
        Assert.Equal(
            delivery
                channel
                (htmlJson
                    $"""<turbo-stream maintain_scroll="true" action="replace" target="presentation_message_0001"><template><div>presentation {message.Id} & more</div></template></turbo-stream>"""),
            frame
        )
    }

// --- onCrack: BroadcastOrder (posts' broadcasts in commit order) ------------------------------------------

[<Fact>]
let ``the broadcast line publishes in place order whatever order places are filled in`` () =
    let order = BroadcastOrder(60_000)
    let published = System.Collections.Concurrent.ConcurrentQueue<int64>()
    let places = [| for _ in 1..2000 -> order.Reserve() |]
    let shuffled = places |> Array.sortBy (fun p -> (p * 7919L) % 2003L)
    System.Threading.Tasks.Parallel.ForEach(shuffled, (fun (p: int64) -> order.Complete(p, fun () -> published.Enqueue p))) |> ignore
    Assert.Equal<int64 list>(List.ofArray places, List.ofSeq published)
    Assert.Equal(0L, order.Skipped)

[<Fact>]
let ``a place given up does not hold the line, and an empty one is skipped after the stall`` () =
    task {
        let order = BroadcastOrder(200)
        let published = System.Collections.Concurrent.ConcurrentQueue<string>()
        let a, b, c, d = order.Reserve(), order.Reserve(), order.Reserve(), order.Reserve()
        order.Complete(c, fun () -> published.Enqueue "c")
        order.Skip b
        Assert.Empty published
        order.Complete(a, fun () -> published.Enqueue "a")
        Assert.Equal<string list>([ "a"; "c" ], List.ofSeq published)
        // `d`'s publisher never comes: `e` waits for the stall, then goes.
        let e = order.Reserve()
        order.Complete(e, fun () -> published.Enqueue "e")
        Assert.Equal<string list>([ "a"; "c" ], List.ofSeq published)
        let deadline = System.DateTime.UtcNow.AddSeconds 5.0
        while published.Count < 3 && System.DateTime.UtcNow < deadline do
            do! Task.Delay 20
        Assert.Equal<string list>([ "a"; "c"; "e" ], List.ofSeq published)
        Assert.Equal(1L, order.Skipped)
        // A place filled after it was skipped publishes nothing late and holds nothing.
        order.Complete(d, fun () -> published.Enqueue "d")
        let f = order.Reserve()
        order.Complete(f, fun () -> published.Enqueue "f")
        Assert.Equal<string list>([ "a"; "c"; "e"; "f" ], List.ofSeq published)
    }

[<Fact>]
let ``a ticket takes one place, publishes once, and gives it up only if unpublished`` () =
    let order = BroadcastOrder(60_000)
    let published = System.Collections.Concurrent.ConcurrentQueue<string>()
    let first = BroadcastTicket(order)
    // A group's after-commit work run again calls the hook twice: still one place.
    first.Reserve()
    first.Reserve()
    let second = BroadcastTicket(order)
    second.Reserve()
    second.Publish(fun () -> published.Enqueue "second")
    second.Abandon()
    Assert.Empty published
    first.Abandon()
    first.Publish(fun () -> published.Enqueue "first")
    Assert.Equal<string list>([ "second" ], List.ofSeq published)
    // Without a place (the write never got to its after-commit work), it publishes at once.
    let unplaced = BroadcastTicket(order)
    unplaced.Publish(fun () -> published.Enqueue "unplaced")
    Assert.Equal<string list>([ "second"; "unplaced" ], List.ofSeq published)
