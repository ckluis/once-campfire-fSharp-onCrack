# R4.5 plan: keep every live Cable subscriber, with bounded memory, 2026-10-10

Design only; a builder implements it (about 2 hours for changes 1-3, change 4 is optional). The baseline
(`bench/results/oncrack-r4-reliability-baseline.md`, upstream `bin/reliability`, session started 12:04 EDT) is still running: at 12:10
it had Rails' round 1 (overload 0 errors / 0 invalid at 64 and 256 clients; `cable` 1,000/1,000 subscribed, 317/317 delivered) and was on
Rust. onCrack's rows do not exist yet, so the "no disconnects, no overload problems" in that file is a placeholder, not a measurement.
This plan does not wait for them: the 256-frame ring makes the failure certain under `cable_heavy` (below), and AGENTS.md (R4.1) already
records it. **Step 0 of the build is to read onCrack's and oncrack-cached's `cable_heavy` rows when the session finishes** (`disconnected`,
`complete`/`posted`, `drain_secs`) and copy them into the baseline file as the "before"; any overload row with errors or invalid
responses becomes change 5.

## What Rails does with a slow subscriber (the reference)

Read from the gems the reference image runs (actioncable 8.x, websocket-driver 0.8, nio4r; local copies under
`~/.local/share/mise/installs/ruby/3.3.11/lib/ruby/gems/3.3.0/gems/`):

- **The server never drops a slow reader.** `ActionCable::Connection::Stream#write` tries `write_nonblock`; whatever the socket does not
  take goes on `@write_buffer`, an unbounded `Queue` of strings, flushed by the nio4r loop when the socket is writable. Nothing bounds it,
  no timeout applies, and nothing checks pongs (the server sends `{"type":"ping"}` every 3 s, `BEAT_INTERVAL`, into the same queue).
  Each connection holds its own copy of every frame.
- **A dead client** goes away only when the socket errors: a write gets `EPIPE`/`ECONNRESET` once TCP gives up (about 15 minutes of
  retransmissions with data in flight). **An alive client that stopped reading** (zero window) is held forever and its queue grows until
  the process runs out of memory.
- **Order:** `stream_from` hands each broadcast to the connection's worker pool (`worker_pool_stream_handler`, `async_invoke`, 4 threads by
  default), so under load two broadcasts can even reach one connection out of order. onCrack's guarantee (per-stream publish order) is
  already stronger; keep it.
- **The browser decides staleness, not the server.** `ConnectionMonitor` (actioncable.esm.js) records every incoming message
  (`recordMessage`), and reconnects when nothing has arrived for `staleThreshold` = 6 s (with backoff and jitter, at most a few times
  that). So a browser that has received no byte for ~6-12 s has already given up on that socket itself.
- **Campfire recovers on reconnect.** `refresh_room_controller.js` subscribes to `HeartbeatChannel`; on `connected` it GETs
  `/rooms/:id/refresh?since=<last loaded>` (`Rooms::RefreshesController`: messages created or updated since), so a reconnecting
  browser gets the open room's missed messages back. What it does not get back is anything else delivered by Cable meanwhile (sidebar
  unread pings for other rooms, presence, typing).

So "Rails-like" for onCrack is: **a client that is reading, however slowly, is never cut and gets every frame in order**; a client is cut
only when a browser would already have abandoned that socket (no progress for far longer than 6 s) or when holding it would break the
memory bound Rails does not have; a cut is a socket close the browser treats as a network drop (it reconnects and refreshes the room). The
comment in `bench/loadgen/src/main.rs` (window) that says the ring lapping and closing "is what Action Cable does" is wrong and is fixed
in change 1's commit.

## What onCrack does now, and why `cable_heavy` breaks it

- `Hub` keeps one ring of `StreamCapacity` = 256 frames (`Config.fs`) per (broadcasting, identifier) group, shared by its subscribers
  (`Pubsub.fs` `Group`). A subscriber more than 256 frames behind gets `RecvStatus.Lagged`; `Connection.run` then sends
  `{"type":"disconnect","reason":null,"reconnect":true}` and closes. The client's missed frames are gone.
- The connection loop awaits `sink.Send` (`Writer.FinishSend`) while the socket is full, so it reads nothing from its rings meanwhile; a
  write that has not completed 30 s after it started (`Socket.WriteTimeout`, whole write, not progress) aborts the socket.
- `drain` reads the connection's streams in list order, up to `MaxWriteBatch` (64) frames, and a full batch re-wakes and starts again
  from the first stream: with a deep backlog on one stream, the later streams wait (only the 256-frame lag cut has kept this short).
- Upstream `cable_heavy`: 1,000 tungstenite clients (one user, 6 subscriptions each), **64 closed-loop posters, no window**, 15 s, then
  up to 60 s to drain; a closed client is counted `disconnected` and misses everything after. onCrack accepts posts far faster than 1,000
  clients can be fanned out to (R4.2: ~900 msgs/s delivered to all at 1,000 clients with our raw client; the upstream tungstenite client is
  slower still, it was the limit at 1,000 in round 2), so within a second every client is >256 frames behind the room's ring and is cut.

## Changes, ranked

### 1. Replace the fixed ring with a shared, chunked, refcounted log (the fix)

`Group` keeps an append-only log of the frames it already shares, in chunks of 256 slots (`Frame[]`, plus each slot's cumulative byte
offset as an `int64[]`, plus `next`). A `Subscriber`'s cursor is (chunk, index), not a position modulo the ring.

- **Publish** (under the group's existing lock, one publisher at a time as now): write the frame and its end offset into the tail chunk's
  slot, then `Volatile.Write` the group's tail count (frames) and tail bytes; when the chunk is full, allocate the next one and link it
  (`Volatile.Write(&chunk.next, ...)`) before advancing the tail. No wraparound, so the "a publish wrapped onto this slot while it was read"
  re-check in `TryRead` disappears.
- **Read** (one thread per subscriber, lock-free as now): if index < the chunk's filled count read the slot; at the end of a full chunk
  follow `next`. Crossing a chunk: `Interlocked.Decrement` the old chunk's reader count, `Interlocked.Increment` the new one's.
- **Free:** each chunk counts the cursors in it; `Add` counts into the tail chunk, `Release` uncounts (both under the lock). At each chunk
  allocation the publisher advances `head` past chunks whose count is zero; nothing then references them and the GC takes them. The
  group's **retained bytes** = tail bytes - head chunk's first offset; the hub keeps an `Interlocked` total of the deltas (a gauge for the
  bench and the log: `Hub.RetainedBytes`, peak too).
- **The bound (replaces `StreamCapacity`):** `CAMPFIRE_CABLE_LAG_BYTES` (default **64 MB**) per group. When a publish leaves retained bytes
  above it, the publisher marks every subscriber whose cursor is in the head chunk (the furthest behind) `Overrun`, removes them from the
  group at once (so their chunks can go even before their connections notice), advances `head`, and queues each one's connection to be cut
  (`ThreadPool.UnsafeQueueUserWorkItem` calling the connection's `abort`, so a connection blocked in `FinishSend` wakes with an error;
  the publisher never makes a syscall). `TryRecv` of an `Overrun` subscriber returns `Lagged`; `Connection.run` then closes as today (the
  disconnect frame is best effort: a stalled socket cannot take it). 64 MB is ~45,000 Campfire message frames (~1.4 KB), minutes of the
  busiest room the benches post; memory is shared, so it is 64 MB per *group*, not per client (Rails would copy it into each client's
  queue).
- `Config.StreamCapacity` becomes the chunk size (keep the field, 256); `CAMPFIRE_CABLE_LOG=ring` keeps the old ring for one round as the
  A/B switch (read at start-up; both paths behind one `Group` interface, or two `Group` types chosen by the hub).

**Measure.** (a) Upstream `bin/reliability --apps rust,oncrack --profiles cable --rounds 1` (inner loop; `--rounds 3` once at the end):
`cable_heavy.disconnected` 0, `complete == posted`, `drain_secs`, and the container's peak memory during `cable_heavy` (sample
`docker stats --no-stream` each second beside `host-load-*.txt`; the harness does not record Pss). (b) The R4.1 cable suite, `bench/run
SUITES=cable` at 1,000 and 2,000 clients with the default `--window 128`, alternating `CAMPFIRE_CABLE_LOG=ring/log` in one session
(`bench/cable/ab` or `pair.sh`): CPU per delivery and msgs/s must be within the pair spread (the read path gains a chunk-crossing branch
and an `Interlocked` pair per 256 frames; it loses the second tail read). (c) The same suite with `CABLE_ARGS="--window 0 --posters 64"`:
`closed_midrun` 0 and `posted == complete` (before: closes), `Hub.RetainedBytes` peak.

**Correctness risk:** high (lock-free reads across chunk links; refcounts that miss a crossing leak chunks or free one a cursor is in).
A freed chunk cannot be read wrongly in .NET (the cursor keeps it alive), so the failure modes are leaks, a wrong retained gauge, or a
wrong frame order at a chunk edge. **Tests that catch it** (`PubsubTests.fs`, rewrite the two lag tests):
- a subscriber 100,000 frames behind reads every one, in order, then `Empty`; a chunk-edge test publishes exactly 255, 256, 257, 512
  frames;
- one publisher and 8 readers on threads for 2 s, readers stalling at random: each reads its exact sequence (the existing concurrent test,
  with stalls and without a capacity);
- refcount/gauge: after every reader catches up or is disposed, `RetainedBytes` returns to under one chunk, and a `WeakReference` to an
  early chunk is collected after `GC.Collect()`; dispose a subscriber mid-chunk and check the same;
- overrun: a subscriber that never reads, 70 MB published with the budget at 64 MB (or a test budget of 1 MB): it gets `Lagged`, the
  others read on untouched, retained bytes stay under budget plus one frame;
- mutation checks the builder runs once by hand: skip the decrement on crossing (the gauge test fails), link `next` after advancing the
  tail (the threaded test fails under `bin/linux-tests Cable`).

### 2. Drain in publish order across a connection's streams

With deep backlogs allowed, `drain`'s "first stream until 64" starves later streams and reorders across them. Stamp each frame with a
hub-wide sequence when it is published (one `Interlocked.Increment` per group publish, stored in a parallel `int64[]` in the chunk; the
group lock already orders a group's publishes), and have `drain` take the smallest head sequence among the connection's readers each time
(a 6-way compare per frame; most connections have 1-6 streams). That is the order one Rails connection's single write queue would see
(minus the worker pool's reordering), and it makes a post's room append and its unread ping arrive together.

**Measure:** cable suite at 1,000 clients, window 128: CPU per delivery within noise (the merge is a few compares per frame against ~2 us
per delivery). **Risk:** medium (an off-by-one that skips or repeats a frame when a stream empties mid-merge). **Tests:** two streams on
one connection, 10,000 interleaved publishes while the reader is stalled, then drained in 64-frame batches: the received sequences are
strictly increasing and complete; a starvation test (stream A always has >64 ready, stream B gets one frame) sees B's frame in the first
batch after it was published; the existing `DirectTests` ordering tests pass unchanged.

### 3. Cut on stalled progress, not on a slow write

`FinishSend`'s 30 s is a deadline for a whole write. Make it a **no-progress** timeout: re-arm it whenever the socket takes a byte (the
`SendAsync` loop already sees each `n`). `CAMPFIRE_CABLE_STALL_MS`, default **30,000** (5x the browser's own 6 s stale threshold, so it
only ever cuts a socket a browser has already abandoned or a peer that is gone). A cut is `abort ()` as now; the connection's subscribers
are released at once (`Connection.run`'s `finally`), which drops their chunk references. Also check stall from the outside: a connection
whose `Wake` has been set but which has not returned to `drain` for the stall time is blocked in a send, and the `FinishSend` timer covers
it; nothing else can block it. Kernel memory: a stalled socket also holds up to its send buffer (`tcp_wmem` max, ~4 MB autotuned); record
`ss -tm` totals in the stall test rather than shrinking `SO_SNDBUF` (that would cost throughput; deferred unless it shows).

**Measure:** a new `bench/cable` stall check (or a `DirectTests` case on Linux): 40 clients, a quarter stop reading after their welcome,
1,000 frames published: the readers get all 1,000 in order; the stalled ones are cut within stall time + 1 s; `RetainedBytes` falls back
to under a chunk after the cut. With the test hook `CAMPFIRE_CABLE_STALL_MS=500`. **Risk:** low-medium (a slow-but-reading client cut
wrongly if progress is not re-armed). **Tests:** a client reading 1 KB/s from a 2 MB backlog is never cut with the stall at 500 ms; a
client that reads nothing is cut at 500 ms +- 250; the existing 8 MB slow reader and the never-answering-probe tests pass.

### 4. Optional: catch up faster when behind (throughput, not correctness)

When `drain` returns `Full` on consecutive turns (a backlog), allow batches up to `MaxGatherFrames` (256) and ~256 KB per `sendmsg`
instead of 64 frames: fewer syscalls per frame while catching up. Measure with the cable suite at `--window 0` (drain_secs, CPU per
delivery) and at window 128 (no change expected: batches are rarely full there). Risk: low (`SendGather` already handles 256 frames and
partial sends). Test: the gather byte-exactness tests at 256 frames. Do it only if change 1's `--window 0` drain is slow.

### 5. Fixes for overload problems found

None found: the baseline listed `[]`, and onCrack's overload rows were not yet run when this was written. If step 0 finds errors or invalid
responses for `oncrack`/`oncrack-cached` at 64 or 256 clients, they come before change 2 (rule: fix bugs first), each with the failing
route rerun alone with `loadgen http --conc 256 --validate`.

## Not chosen, and why

- **A per-connection queue that copies frames** (what Rails has): memory x clients; the shared log keeps one copy.
- **Coalescing frames** (dropping superseded ones, e.g. repeated unread pings for one room): Turbo Stream actions are not idempotent in
  general (append twice is two messages), and the unread ping is cheap; it would break "every message in order" for little gain.
- **Throttling posters when the fan-out is behind** (backpressure in `messages#create`): it would make `cable_heavy` drain faster, but one
  room's slow fan-out would slow every poster, Rails does not do it, and a post's latency is the person's experience. Revisit only if
  change 1's `cable_heavy` run shows `complete < posted` because the 60 s drain deadline expires (backlog / delivery rate > 60 s) with no
  client cut. Then measure it as a disclosed setting, off by default.
- **Raising `StreamCapacity`** (say to 65,536): a fixed ring of that size per group costs its slots up front for every group (most rooms are
  idle) and still cuts a live client at a fixed frame count, not a byte budget.

## Deferred

- The baseline's onCrack rows (step 0) and the post-change `bin/reliability --rounds 3` run.
- `SO_SNDBUF` per stalled socket, if `ss -tm` shows kernel memory as the larger part of a stall.
- The Mac had 14 GB free at 12:10 with the baseline session running (floor 12 GB): run `bin/clean-docker` and `bin/clean-parity` before the
  builder's first measurement.
