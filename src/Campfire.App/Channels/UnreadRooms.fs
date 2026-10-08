// Port of rust/crates/campfire/src/channels/unread_rooms.rs
//
// `UnreadRoomsChannel` (reference/app/channels/unread_rooms_channel.rb).
module Campfire.App.Channels.UnreadRooms

open System.Threading.Tasks
open Campfire.Cable

/// `UnreadRoomsChannel.stream_name_for(user_id)`: per user, so activity in a room only reaches
/// its members.
let streamNameFor (userId: int64) : string = $"user_{userId}_unreads"

/// onCrack: `streamNameFor`, made once per user (a post into a room of 500 pings 500 streams).
let private streamNames = System.Collections.Concurrent.ConcurrentDictionary<int64, string>()

let private makeStreamName = System.Func<int64, string>(streamNameFor)

let cachedStreamNameFor (userId: int64) : string = streamNames.GetOrAdd(userId, makeStreamName)

let private subscribed (sub: Subscription<CableUser>) : Task<ChannelResult<unit>> =
    sub.StreamFrom(streamNameFor sub.CurrentUser.Id)
    Channel.ok

let channel: Channel<CableUser> =
    { Channel.empty with
        Subscribed = subscribed
        // `subscribed` is public, so it's an action too.
        Perform =
            fun action _ sub ->
                match action with
                | "subscribed" ->
                    task {
                        match! subscribed sub with
                        | Ok() -> return Ok true
                        | Error error -> return Error error
                    }
                | _ -> Task.FromResult(Ok false) }
