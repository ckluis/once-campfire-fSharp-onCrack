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
      /// Messages buffered per broadcasting (shared by its subscribers) before a slow subscriber
      /// counts as lagging and is disconnected with `reconnect: true`.
      StreamCapacity: int
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
