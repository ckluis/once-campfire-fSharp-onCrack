// Port of rust/crates/campfire/src/channels/broadcasts.rs
//
// Every broadcast the Rails app makes, with the stream names, targets and `<turbo-stream>`
// markup its Turbo and Action Cable calls produce. The HTML inside comes from `IPartials`.
//
// Stream names: records are their GID param (`turbo_stream_from @room, :messages` is
// `<room gid param>:messages`), symbols themselves. Targets are `dom_id`s: STI rooms use their
// own `param_key` (`messages_rooms_open_1`), and a message's `to_key` is its
// `client_message_id` (`message_<uuid>`).
namespace Campfire.App.Channels

open Campfire.Cable
open Campfire.Cable.Turbo
open Campfire.Db
open Campfire.RailsCompat

/// The partials Turbo renders for broadcasts (`ApplicationController.render(partial:, locals:)`,
/// html format, no request). Each returns the rendered HTML; the fragment-backed ones (a message and a boost, cached bytes) as the
/// UTF-8 they were rendered to, which the broadcast escapes as JSON without making a string of them.
type IPartials =
    /// `messages/_message` with `message:`.
    abstract Message: Message -> System.ReadOnlyMemory<byte>
    /// `messages/_presentation` with `message:`.
    abstract MessagePresentation: Message -> string
    /// `messages/boosts/_boost` with `boost:`.
    abstract Boost: Boost -> System.ReadOnlyMemory<byte>
    /// `users/sidebars/rooms/_shared` with `room:`.
    abstract SharedRoom: Room -> string
    /// `users/sidebars/rooms/_direct` with `membership:`.
    abstract DirectRoom: Membership -> string

/// `nil.inquiry`: NoMethodError.
type NilInquiry =
    | NilInquiry

    override _.ToString() = "undefined method 'inquiry' for nil"

module BroadcastNames =
    /// `dom_id(record, prefix)`.
    let domId (paramKey: string) (key: obj) (prefix: string option) : string =
        match prefix with
        | Some prefix -> $"{prefix}_{paramKey}_{key}"
        | None -> $"{paramKey}_{key}"

    /// `Room.model_name.param_key` for the room's STI class: `Rooms::Open` is `rooms_open`.
    let roomParamKey (room: Room) : string =
        (RoomType.className room.RoomType).Replace("::", "_").ToLowerInvariant()

    /// `dom_id(room, prefix)`.
    let roomDomId (room: Room) (prefix: string) : string = domId (roomParamKey room) room.Id (Some prefix)

    /// `dom_id(message, prefix)`: messages are keyed by `client_message_id`.
    let messageDomId (message: Message) (prefix: string option) : string = domId "message" message.ClientMessageId prefix

    [<Literal>]
    let Rooms = "rooms"

    [<Literal>]
    let Messages = "messages"

    let internal maintainScroll: (string * string option) list = [ "maintain_scroll", Some "true" ]

    /// `ActionCable.server.broadcast "user_#{id}_reads", { room_id: }`
    /// (reference/app/channels/presence_channel.rb).
    let readRoom (server: IServer) (userId: int64) (roomId: int64) : int =
        server.Broadcast(ReadRooms.streamNameFor userId, Value.Object [ "room_id", Value.Int roomId ])

/// onCrack: posts' broadcasts in commit order (the verifier's A5). Under group commit the writer answers the posts of
/// a group one after another and each request broadcasts from its own continuation, so posts committed together went
/// out in the order those continuations ran: the client places an appended message by its sort value (milliseconds),
/// so posts of one millisecond showed in that order live and in commit order after a reload. A post takes a place in
/// line on the writer, in an after-commit hook (commit order), and its request hands its broadcast to the line when
/// rendered; the line publishes each one once every earlier place has published or given its place up. Rendering
/// stays in the requests, in parallel; only the publishing is in order.
///
/// A place nobody fills (a request that died between its commit and its broadcast; every path gives its place up in a
/// `finally`) holds the line for at most `stallMs`, then is skipped.
///
/// onCrack (unit R2.1): the line also holds the wakes of what it publishes while later places are still being rendered, and
/// sets them once the line is empty (every reserved place published) or `holdUs` after it began holding, whichever comes
/// first. Each subscriber then reads the posts in flight together and sends them in one write. The frames are in their rings
/// at once; only the wakes wait, at most `holdUs` (`CAMPFIRE_CABLE_HOLD_US`, 1000 by default; 0 sets them when each turn ends).
[<Sealed>]
type BroadcastOrder(stallMs: int, holdUs: int) =
    let gate = obj ()
    let holdTicks = int64 holdUs * System.Diagnostics.Stopwatch.Frequency / 1_000_000L
    // Wakes held for the line (under `gate`), marked with `heldToken`; `heldSince` is when the first was held (0: none).
    let mutable held = System.Collections.Generic.List<Wake>()
    let mutable heldToken = WakeBatch.NewToken()
    let mutable heldSince = 0L
    let mutable holdTimer: System.Threading.Timer | null = null
    let waiting = System.Collections.Generic.Dictionary<int64, unit -> unit>()
    let mutable reserved = 0L
    let mutable next = 0L
    let mutable draining = false
    // The place the stall timer was armed for (-1: not armed).
    let mutable armedFor = -1L
    let mutable timer: System.Threading.Timer | null = null
    let mutable skipped = 0L

    new(stallMs: int) = BroadcastOrder(stallMs, 0)

    new() =
        let hold =
            match System.Int32.TryParse(System.Environment.GetEnvironmentVariable "CAMPFIRE_CABLE_HOLD_US") with
            | true, us when us >= 0 -> us
            | _ -> 1000
        BroadcastOrder(1000, hold)

    /// Takes every held wake, if the line is empty or they have been held `holdUs`, or `force`; under `gate`.
    member private _.TakeHeld(force: bool) : Wake[] | null =
        if held.Count = 0 then
            null
        else
            let now = System.Diagnostics.Stopwatch.GetTimestamp()
            let idle = next = System.Threading.Volatile.Read(&reserved) && waiting.Count = 0
            if force || idle || holdTicks = 0L || now - heldSince >= holdTicks then
                let taken = held.ToArray()
                held.Clear()
                heldToken <- WakeBatch.NewToken()
                heldSince <- 0L
                taken
            else
                null

    /// Sets wakes taken from the line, outside `gate`.
    static member private SetAll(wakes: Wake[] | null) : unit =
        match wakes with
        | null -> ()
        | wakes ->
            for wake in wakes do
                wake.Set()

    /// The hold's time limit passed: set whatever is still held.
    member private this.HoldExpired() : unit =
        BroadcastOrder.SetAll(lock gate (fun () -> this.TakeHeld true))

    /// A place in line: on the writer thread, after the commit (an after-commit hook), so places follow commit order.
    member _.Reserve() : int64 = System.Threading.Interlocked.Increment(&reserved) - 1L

    /// Places skipped because nobody filled them in time, for tests and logs.
    member _.Skipped : int64 = System.Threading.Volatile.Read(&skipped)

    /// Publishes `publish` once every earlier place is done (now, or later on whichever thread fills the gap).
    member this.Complete(place: int64, publish: unit -> unit) : unit =
        let drain =
            lock gate (fun () ->
                if place >= next then waiting[place] <- publish
                if draining then
                    false
                else
                    draining <- true
                    true)
        if drain then this.Drain()

    /// Gives a place up: nothing to publish.
    member this.Skip(place: int64) : unit = this.Complete(place, ignore)

    member private this.Drain() : unit =
        // onCrack (unit R2.1): what this turn publishes wakes its subscribers once, after the last of it, and while later
        // places are still being rendered the line holds those wakes (up to `holdUs`) for their posts to join.
        WakeBatch.Begin()
        try
            this.DrainHeld()
        finally
            let toSet =
                lock gate (fun () ->
                    let before = held.Count
                    WakeBatch.EndInto(held, heldToken)
                    if before = 0 && held.Count > 0 then heldSince <- System.Diagnostics.Stopwatch.GetTimestamp()
                    let taken = this.TakeHeld false
                    if isNull taken && held.Count > 0 then
                        // Held for a busy line: whatever happens next, they are set within `holdUs`.
                        let due = max 1 ((holdUs + 999) / 1000)
                        match holdTimer with
                        | null -> holdTimer <- new System.Threading.Timer((fun _ -> this.HoldExpired()), null, due, System.Threading.Timeout.Infinite)
                        | t -> t.Change(due, System.Threading.Timeout.Infinite) |> ignore
                    taken)
            BroadcastOrder.SetAll toSet

    member private this.DrainHeld() : unit =
        let mutable running = true
        let mutable published = 0
        while running do
            let publish =
                lock gate (fun () ->
                    match waiting.TryGetValue next with
                    | true, publish ->
                        waiting.Remove next |> ignore
                        next <- next + 1L
                        publish
                    | _ ->
                        draining <- false
                        // Later places wait on one that isn't filled yet: give it `stallMs`.
                        if waiting.Count > 0 && armedFor <> next then
                            armedFor <- next
                            match timer with
                            | null -> timer <- new System.Threading.Timer((fun _ -> this.Expire()), null, stallMs, System.Threading.Timeout.Infinite)
                            | t -> t.Change(stallMs, System.Threading.Timeout.Infinite) |> ignore
                        Unchecked.defaultof<_>)
            match box publish with
            | null -> running <- false
            | _ ->
                try
                    publish ()
                with e ->
                    eprintfn "ERROR campfire: broadcast failed: %s" e.Message
                // A drainer that keeps finding posts in line wakes their subscribers every few posts, not only at its end.
                published <- published + 1
                if published % 8 = 0 then
                    WakeBatch.Flush()
                    BroadcastOrder.SetAll(lock gate (fun () -> this.TakeHeld true))

    member private this.Expire() : unit =
        let drain =
            lock gate (fun () ->
                if armedFor <> next then
                    // The place it was armed for was filled (a later gap arms it again).
                    false
                elif draining || waiting.Count = 0 || waiting.ContainsKey next then
                    // A drainer is running (it arms again when it stops at a gap), or there is no gap.
                    armedFor <- -1L
                    false
                else
                    eprintfn "ERROR campfire: broadcast place %d not filled in %d ms: skipped" next stallMs
                    skipped <- skipped + 1L
                    next <- next + 1L
                    armedFor <- -1L
                    draining <- true
                    true)
        if drain then this.Drain()

/// One post's place in `BroadcastOrder`: taken at most once (a group's after-commit work can run again), then
/// published or given up exactly once.
[<Sealed; AllowNullLiteral>]
type BroadcastTicket(order: BroadcastOrder) =
    let mutable place = -1L
    let mutable finished = false

    /// In the write's after-commit hook.
    member _.Reserve() : unit = if place < 0L then place <- order.Reserve()

    /// Publishes in line (now, without a place: the write never reached its after-commit work).
    member _.Publish(publish: unit -> unit) : unit =
        if not finished then
            finished <- true
            if place >= 0L then order.Complete(place, publish) else publish ()

    /// Gives the place up, unless it was published.
    member _.Abandon() : unit =
        if not finished then
            finished <- true
            if place >= 0L then order.Skip place

[<Sealed>]
type Broadcasts(server: Cable) =
    static member private RoomMessages(room: Room) : string list = [ GlobalId.toParam (Gid.roomGid room); BroadcastNames.Messages ]

    static member private UserRooms(userId: int64) : string list = [ GlobalId.toParam (Gid.userGid userId); BroadcastNames.Rooms ]

    member private _.To(streamables: string list, action: Action, target: string, html: string option, attributes: (string * string option) list) : unit =
        let template =
            match html with
            | Some html -> Html html
            | None -> NoTemplate
        broadcastActionTo server streamables action (Target target) template attributes |> ignore

    /// onCrack: a message's or boost's tag is encoded (its fragment escaped as JSON) only when its stream has a
    /// subscriber; nobody else would receive it. The debug log still names every broadcast, as Rails logs it.
    member private _.ToUtf8(streamables: string list, action: Action, target: string, html: System.ReadOnlyMemory<byte>, attributes: (string * string option) list) : unit =
        let heard =
            match streamName streamables with
            | Some name -> server.Hub.HasSubscribers name || server.Logger.IsEnabled Microsoft.Extensions.Logging.LogLevel.Debug
            | None -> false
        if heard then broadcastActionTo server streamables action (Target target) (HtmlUtf8 html) attributes |> ignore

    // Message::Broadcasts (reference/app/models/message/broadcasts.rb)

    /// `message.broadcast_create`: append the message to the room, then tell every member's
    /// unread stream (`room.memberships.pluck(:user_id)`). Used by MessagesController#create,
    /// Webhook replies, and `Messages::ByBotsController`.
    member this.MessageCreate(conn: Conn, room: Room, message: Message, partials: IPartials) : unit =
        this.MessageCreateLater(conn, room, message, partials) ()

    /// onCrack: `MessageCreate` with what it reads (the partial, the members) read now, and the broadcasting
    /// left to the function it returns (for `BroadcastOrder`).
    member this.MessageCreateLater(conn: Conn, room: Room, message: Message, partials: IPartials) : unit -> unit =
        let html = partials.Message message
        let members = Membership.userIdsForRoom conn room.Id
        fun () ->
            // The append and the unread pings wake their subscribers together (`WakeBatch`).
            WakeBatch.Run(fun () ->
                this.ToUtf8(Broadcasts.RoomMessages room, Append, BroadcastNames.roomDomId room BroadcastNames.Messages, html, [])
                this.UnreadRoomTo(room, members))

    /// onCrack: the posts' broadcasts in commit order (`BroadcastOrder`).
    member val Order = BroadcastOrder()

    /// `broadcast_unread_room`: `{ roomId: }` to each member's `user_<id>_unreads`.
    member this.UnreadRoom(conn: Conn, room: Room) : unit =
        this.UnreadRoomTo(room, Membership.userIdsForRoom conn room.Id)

    /// `broadcast_unread_room` to `members` (`room.memberships.pluck(:user_id)`, read by the caller).
    member _.UnreadRoomTo(room: Room, members: int64 list) : unit =
        // The same message to every member's stream: encoded once.
        let json = System.Text.Encoding.UTF8.GetBytes(Json.encode (Value.Object [ "roomId", Value.Int room.Id ]))
        for userId in members do
            server.BroadcastEncoded(UnreadRooms.cachedStreamNameFor userId, System.ReadOnlySpan json) |> ignore

    /// `message.broadcast_remove`: MessagesController#destroy and `User#remove_banned_content`.
    member this.MessageRemove(room: Room, message: Message) : unit =
        this.To(Broadcasts.RoomMessages room, Remove, BroadcastNames.messageDomId message None, None, [])

    /// MessagesController#update: replace `[message, :presentation]` with
    /// `messages/_presentation`, keeping the scroll position.
    member this.MessageReplace(room: Room, message: Message, partials: IPartials) : unit =
        let html = partials.MessagePresentation message
        let target = BroadcastNames.messageDomId message (Some "presentation")
        this.To(Broadcasts.RoomMessages room, Replace, target, Some html, BroadcastNames.maintainScroll)

    // Messages::BoostsController (and its ByBots subclass)

    /// `broadcast_create`: append to `boosts_message_<client_message_id>`.
    member this.BoostCreate(room: Room, message: Message, boost: Boost, partials: IPartials) : unit =
        let html = partials.Boost boost
        let target = $"boosts_message_{message.ClientMessageId}"
        this.ToUtf8(Broadcasts.RoomMessages room, Append, target, html, BroadcastNames.maintainScroll)

    /// `broadcast_remove`: `dom_id(boost)`.
    member this.BoostRemove(room: Room, boost: Boost) : unit =
        this.To(Broadcasts.RoomMessages room, Remove, BroadcastNames.domId "boost" boost.Id None, None, [])

    // The sidebar's room lists (users/sidebars/show.html.erb streams from `:rooms` and
    // `[Current.user, :rooms]`).

    /// RoomsController#destroy: remove `[room, :list]` from everyone's `:rooms`.
    member this.RoomRemove(room: Room) : unit =
        this.To([ BroadcastNames.Rooms ], Remove, BroadcastNames.roomDomId room "list", None, [])

    /// Rooms::OpensController#create: prepend to everyone's `shared_rooms`.
    member this.OpenRoomCreate(room: Room, partials: IPartials) : unit =
        let html = partials.SharedRoom room
        this.To([ BroadcastNames.Rooms ], Prepend, "shared_rooms", Some html, [])

    /// Rooms::OpensController#update: replace `[room, :list]` on `:rooms`. `room` is the room as
    /// an open room (`becomes!(Rooms::Open)`), so the target names that class even when the
    /// room was closed before.
    member this.OpenRoomUpdate(room: Room, partials: IPartials) : unit =
        let html = partials.SharedRoom room
        this.To([ BroadcastNames.Rooms ], Replace, BroadcastNames.roomDomId room "list", Some html, [])

    /// Rooms::ClosedsController#create: render once, prepend to each member's own stream
    /// (`room.users`).
    member this.ClosedRoomCreate(conn: Conn, room: Room, partials: IPartials) : unit =
        let html = partials.SharedRoom room
        for userId in Room.userIds conn room do
            this.To(Broadcasts.UserRooms userId, Prepend, "shared_rooms", Some html, [])

    /// Rooms::ClosedsController#update: after `memberships.revise`, replace `[room, :list]` for
    /// each remaining member (`room` as a closed room).
    member this.ClosedRoomUpdate(conn: Conn, room: Room, partials: IPartials) : unit =
        let html = partials.SharedRoom room
        let target = BroadcastNames.roomDomId room "list"
        for userId in Room.userIds conn room do
            this.To(Broadcasts.UserRooms userId, Replace, target, Some html, [])

    /// Rooms::DirectsController#create: prepend `users/sidebars/rooms/_direct` to each member's
    /// `direct_rooms`, rendered per membership.
    member this.DirectRoomCreate(conn: Conn, room: Room, partials: IPartials) : unit =
        for membership in Room.memberships conn room do
            let html = partials.DirectRoom membership
            this.To(Broadcasts.UserRooms membership.UserId, Prepend, "direct_rooms", Some html, [])

    /// Rooms::InvolvementsController#update (`broadcast_visibility_changes`). `previous` is
    /// `involvement_previously_was` (the current value when the update changed nothing). Rails
    /// raises NoMethodError on a nil previous involvement (`nil.inquiry`) after the update has
    /// saved; that's the `Error`.
    member this.InvolvementChange(room: Room, membership: Membership, previous: Involvement option, partials: IPartials) : Result<unit, NilInquiry> =
        if Room.isDirect room then
            Ok()
        else
            let streamables = Broadcasts.UserRooms membership.UserId
            if Membership.involvedIn membership Involvement.Invisible then
                this.To(streamables, Remove, BroadcastNames.roomDomId room "list", None, [])
                Ok()
            else
                match previous with
                | None -> Error NilInquiry
                | Some Involvement.Invisible ->
                    let html = partials.SharedRoom room
                    this.To(streamables, Prepend, "shared_rooms", Some html, [])
                    Ok()
                | Some _ -> Ok()
