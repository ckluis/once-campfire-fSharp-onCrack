// Port of `Config` and `ConnectRequest` in rust/crates/cable/src/server.rs
namespace Campfire.Cable

open System
open Microsoft.AspNetCore.Http

/// `config.action_cable.*` as the production reference runs it.
type Config =
    { DisableRequestForgeryProtection: bool
      /// Exact `Origin` values accepted in addition to the same-origin rule.
      AllowedRequestOrigins: string list
      AllowSameOriginAsHost: bool
      /// `config.assume_ssl` (on unless `DISABLE_SSL`): `ActionDispatch::AssumeSSL` makes every
      /// request look like HTTPS, so the same-origin check compares against `https://<host>`.
      AssumeSsl: bool
      /// Frames per chunk of a broadcasting's log (shared by its subscribers); with `RingLog`, the ring's size: messages
      /// buffered before a slow subscriber counts as lagging and is disconnected with `reconnect: true`.
      StreamCapacity: int
      /// onCrack (unit R4.5): the most a broadcasting's log holds behind its oldest subscriber. A subscriber further behind is
      /// disconnected with `reconnect: true`; anything nearer loses nothing. `CAMPFIRE_CABLE_LAG_BYTES`.
      LagBytes: int64
      /// Round 4 verifier, unit R5.2: the most all broadcastings' logs hold together, counting every chunk and every frame some subscriber
      /// has yet to read; over it the subscribers with the most yet to read are cut (`Hub.TotalBudget`). `CAMPFIRE_CABLE_HUB_BYTES` (1 GiB).
      HubBytes: int64
      /// onCrack (unit R4.5): a post waits (`Broadcasts.AwaitRoom`) while more than half of its room's subscribers are more than this many frames
      /// behind, so a room fed faster than it can be fanned out holds a bounded backlog instead of cutting its clients; 0 never waits.
      /// `CAMPFIRE_CABLE_PRESSURE_FRAMES` (2048; `CAMPFIRE_CABLE_PRESSURE=off` is 0).
      PressureFrames: int
      /// The longest one post waits (`CAMPFIRE_CABLE_PRESSURE_MS`, 2000).
      PressureWait: TimeSpan
      /// onCrack (unit R4.5): the fixed ring of rounds 1-4 instead of the log (`CAMPFIRE_CABLE_LOG=ring`): the A/B switch.
      RingLog: bool
      /// onCrack (unit R4.5): a connection takes the frames of its streams in the order they were published, across the streams
      /// (`Connection.Merge`); off: a stream at a time, in the order they were subscribed (rounds 1-4). `CAMPFIRE_CABLE_ORDER=stream`.
      PublishOrder: bool
      /// onCrack (unit R4.5): how long a socket write may go without the peer taking any bytes before the connection is cut:
      /// 30 s, five times the browser's own 6 s threshold for abandoning a connection that has gone quiet. A peer that is
      /// reading, however slowly, is not cut. `CAMPFIRE_CABLE_STALL_MS`.
      StallTimeout: TimeSpan
      /// Frames coalesced into one socket write at most, which also bounds what a connection
      /// buffers beyond the socket.
      MaxWriteBatch: int
      /// How long to wait for the client's close frame after we close.
      CloseTimeout: TimeSpan
      /// onCrack (unit R2.1): a connection on plain TCP writes to its socket itself once its probe is answered
      /// (`Connection.run`), instead of through Kestrel's upgraded stream. `CAMPFIRE_CABLE_DIRECT=off` turns it off.
      DirectWrites: bool
      /// onCrack (unit R4.2): a direct connection sends a batch with one `sendmsg` over the frames' shared payloads instead of
      /// copying them into a send buffer first. `CAMPFIRE_CABLE_GATHER=off` copies.
      GatherWrites: bool
      /// onCrack (unit R2.1): Turbo Stream broadcasts leave `<`, `>` and `&` unescaped in their JSON (`JsonStringWriter`'s
      /// compact mode): the same string once parsed, a third fewer bytes. `CAMPFIRE_CABLE_COMPACT_JSON=off` escapes them as Rails.
      CompactJson: bool }

module Config =
    let defaults: Config =
        { DisableRequestForgeryProtection = false
          AllowedRequestOrigins = []
          AllowSameOriginAsHost = true
          AssumeSsl = true
          StreamCapacity = 256
          LagBytes = 256L * 1024L * 1024L
          HubBytes = 1024L * 1024L * 1024L
          RingLog = false
          PressureFrames = 2048
          PressureWait = TimeSpan.FromSeconds 2.0
          PublishOrder = true
          StallTimeout = TimeSpan.FromSeconds 30.0
          MaxWriteBatch = 64
          CloseTimeout = TimeSpan.FromSeconds 5.0
          DirectWrites = true
          GatherWrites = true
          CompactJson = true }

/// What the connection's `connect` sees of the upgrade request: its path and query, and its headers
/// (`Headers["Cookie"]` has one value per Cookie header line). Kestrel's headers are only good while the
/// request is, so `connect` reads what it needs from them, as it does for a request in Rust.
type ConnectRequest =
    { Uri: string
      Headers: IHeaderDictionary }
