# onCrack R2.1: Cable fan-out and per-connection memory, 2026-10-08

Round 1 left Cable fan-out where the port had it: 0.61-0.87x Rust in delivered messages per second, and 749 MB of app Pss
with 1,000 clients saturated against Rust's 126. This unit fixed the backend's write path, measured it in a harness that now
reports the server's CPU per delivery, and built and measured a server-sent-events prototype, which is left off.

**Verdict** (tier 3: the rebuilt image `campfire-oncrack:app` `sha256:449b485c8a0e`, label `72ddf9f`; the cable suite alone;
Rust and the F# port measured in the same session; 3 reps; `SERVER_CPUS=0-3 LOADGEN_CPUS=4-7`):

| clients | Rust msgs/s | F# port | **onCrack** | **onCrack / Rust** | **onCrack / port** | server CPU per delivery, onCrack / Rust |
|---|---|---|---|---|---|---|
| 100 | 3,368 | 2,858 | **4,194** | **1.25x** | **1.47x** | 6.68 / 8.13 us (0.82x) |
| 500 | 1,189 | 806 | **1,350** | **1.14x** | **1.68x** | 4.81 / 5.70 us (0.84x) |
| 1,000 | 752 | 390 | **747** | **0.99x** | **1.91x** | 4.62 / 4.78 us (0.97x) |

- **Against Rust:** onCrack now delivers more than Rust at 100 and 500 clients, and the same at 1,000. It uses less server
  CPU per delivery at all three.
- **At 1,000 clients the load generator is the limit** for both, at 3.84-3.86 of its 4 cores. 747 against 752 is a tie
  at the harness's ceiling, not a measure of either server. The server-side figure is CPU per delivery: 4.62 against 4.78 µs.
- **Against the port:** 1.47-1.91x the messages, and half the CPU per delivery.
- **Memory:** the app's Pss with 1,000 clients saturated is 294 MB, against the port's 633 and Rust's 110 in the same session.
  Round 1's 749 MB came from the cable suite run after the HTTP suite, so it isn't comparable. The comparable step is in the tier 2
  control below: 726 MB down to 295 MB on the same harness.
- **Latency:** every client had a post 11.1 ms after it was sent (p50 at 1,000 clients, paced), against Rust's 13.3 and the
  port's 16.1. Under saturation the figure is 13.3 ms, against Rust's 19.4.
- **The UI is unchanged:** 366/366 screenshots pixel-equal (all of the four small seeds; on the default seed, every realtime and
  interaction state; below). `bin/verify`: 1,095 tests, 1,088 passed, 7 skipped, 0 warnings.

All the tables here are printed by [`oncrack-r2-cable/review/table.py`](oncrack-r2-cable/review/table.py) from the raw JSON in
[`oncrack-r2-cable/`](oncrack-r2-cable/) (`--json` writes [`summary.json`](oncrack-r2-cable/summary.json)).

## What was wrong

A profile of round 1's image at 1,000 clients (`bench/cable/perf`) put 18% of the server's CPU in `Memmove` and 18% in the
kernel's `copy_from_user`. Each frame was copied three times:
1. into a pooled buffer;
2. by Kestrel's upgraded stream into the connection's output-pipe blocks;
3. by the kernel, out of those cold, per-connection blocks, on the socket transport's I/O thread.

The pipe also rented and returned a memory-pool block on every write, which drove background GCs. A delivery cost 10.2 µs of
server CPU, against Rust's 5.8. Rust's connection task `writev`s the shared payload itself.

## What changed

Three changes, each measured at tier 2 (one rep, mounted build, the cable suite alone). The load generator became cheaper
part-way through (below); every comparison is against a Rust run on the same harness.

**1. Direct writes** (`Socket.fs` `Writer.Detach`, `Connection.run`, `Endpoint.call`).
- On plain TCP (Kestrel's socket transport, no TLS), a connection writes to its own socket: one `send` per batch, from a
  buffer the sending thread has just filled. No pipe, no hop to the I/O thread.
- The risk is byte order: Kestrel's pipe may still hold the 101 response and the welcome. The connection proves it is empty:
  - Right after the welcome it sends a WebSocket ping with a random 8-byte payload (the probe) through Kestrel's stream, and holds
    every later write.
  - The pong echoing that payload means the client has read every byte up to the probe, so nothing is left in the pipe. Only
    then do writes go to the socket.
  - If the connection has to answer the client's own ping meanwhile, that pong goes through the stream, and a fresh probe follows it.
  - If no pong arrives within 2 s, or the connection closes, it stays on the stream for good.
- Browsers and WebSocket libraries answer pings by themselves. Action Cable's JavaScript never sees them.
- `CAMPFIRE_CABLE_DIRECT=off` turns it off.
- Tier 2, same old cable client: 376 → 550 msgs/s at 1,000 clients, 10.2 → 6.1 µs per delivery, Pss saturated 726 → 295 MB.

**2. One wake per post, and per line** (`WakeBatch` in `Pubsub.fs`, `BroadcastOrder` in `Broadcasts.fs`).
- Every published frame used to wake its subscribers at once. A connection could drain and send between a post's append and its
  unread ping, and again for each post behind it.
- `WakeBatch` holds the wakes a thread's broadcasts make until its scope ends: a post's two broadcasts wake each subscriber once.
- The commit-order line (`BroadcastOrder`) also holds the wakes of what it publishes while later places are still being rendered.
  It sets them when the line is empty, or `CAMPFIRE_CABLE_HOLD_US` (1,000) after it started holding, with a timer for a place
  that never fills.
- The frames are in their rings at once; only the wakes wait.
- Sends per delivery fell from 0.335 to 0.283 (Rust: 0.19).
- Tier 2: 674 → 685 msgs/s (WakeBatch), then 727 (the line's hold), at 1,000 clients.

**3. Compact Turbo Stream JSON** (`JsonStringWriter`'s compact mode, `Config.CompactJson`).
- Active Support escapes `<`, `>` and `&` as `<` and so on, so that JSON can sit inside an HTML `<script>`.
- A Cable frame is never inside one, and `JSON.parse` returns the same string either way.
- A message's frame is about a third smaller, so the server and the client both copy and send fewer bytes.
- `CAMPFIRE_CABLE_COMPACT_JSON=off` escapes them as Rails does. The Rails-golden tests run with it off.
- Tier 2: 727 → 778 msgs/s at 1,000 clients, 4.72 → 4.38 µs per delivery.

**Rejected:** yielding once to the back of the thread pool's queue before a connection drains, so that more frames are ready for
the same write. It went from 685 to 644 msgs/s, with more CPU per delivery.

The tier 2 sequence:

| run | build | 100: msgs/s (µs/delivery) | 500 | 1,000 | 1,000: server / loadgen cores | Pss saturated at 1,000 (MB) |
|---|---|---|---|---|---|---|
| `t2-base-0` | round 1's image (control; harness with CPU per delivery, old cable client) | 2,864 (10.46) | 767 (9.72) | 376 (10.22) | 3.80 / 3.62 | 726 |
| `t2-rust-0` | Rust (control, old cable client) | 3,306 (8.41) | 1,051 (6.31) | 588 (5.82) | 3.42 / 3.94 | 109 |
| `t2-direct-1` | + direct socket writes after the probe (old cable client) | 3,465 (7.86) | 1,014 (6.25) | 550 (6.09) | 3.36 / 3.90 | 295 |
| `t2-rust-lg2` | Rust, cheaper cable client | 3,576 (7.81) | 1,311 (5.28) | 802 (4.47) | 3.59 / 3.86 | 109 |
| `t2-direct-lg2` | direct writes, cheaper cable client | 3,789 (7.25) | 1,224 (5.30) | 674 (5.16) | 3.48 / 3.85 | 295 |
| `t2-batch-1` | + WakeBatch (a post's broadcasts wake once) | 3,823 (7.21) | 1,236 (5.21) | 685 (4.98) | 3.35 / 3.83 | 307 |
| `t2-yield1` | rejected: + one yield before draining | 3,823 (7.33) | 1,175 (5.48) | 644 (5.35) | 3.40 / 3.80 | 305 |
| `t2-hold1000` | + the line holds wakes up to 1 ms (no yield) | 4,131 (6.82) | 1,317 (4.95) | 727 (4.72) | 3.38 / 3.85 | 296 |
| `t2-compact` | + compact Turbo Stream JSON | 4,308 (6.62) | 1,390 (4.65) | 778 (4.38) | 3.41 / 3.83 | 298 |

One tier 2 loop was about 2.5 minutes: `bin/publish-mounted` (~1 min), then `bench/run` with `SUITES=cable` (~1.5 min).

## The harness (and why every number here is same-session)

- **Server CPU per delivery:**
  - `bench/lib/procmem.py` now samples the container's `cpu.stat` with its memory.
  - The load generator's `PHASE` lines carry its own CPU.
  - Each cable result therefore has the server's CPU over the saturated phase, divided by messages × clients, and both sides' cores busy.
  - `bench/quick compare` and `log` print and record it as the `cable` workload.
- **The load generator was most of the limit:**
  - At 500 and 1,000 clients it ran at 3.6-3.9 of its 4 cores, for Rust as much as for onCrack.
  - 26% of that went on scanning every frame twice with `str::find` and on reading `LOADGEN_DEBUG` per frame.
  - It now searches with memchr's `memmem`, and stops looking for confirmations once it has them all.
  - That raised Rust from 588 to 802 msgs/s at 1,000 clients on the same image.
  - So no cable number here is compared with round 1's stored medians, only with the same session's.
  - The load generator is still at about 3.85 cores at 1,000 clients for both apps. Its remaining cost is the kernel's receive copy,
    tungstenite's UTF-8 check and its copies.
- **The tier 3 shape:** the cable suite alone in a fresh container (`review/part.sh`), not after the HTTP suite as round 1 ran it.
  So Pss here is not round 1's figure. It is the same for all three apps.
- **Tools added:**
  - `bench/cable/perf` profiles the app (or, with `--loadgen`, the load generator) under a saturated fan-out, and counts its sends
    per delivery.
  - `bench/cable/driver.py` now answers pings, as a WebSocket library does. Without that, onCrack's connections stay on the stream
    there.

## Correctness

The ordering argument rests on the probe; these tests try to break it:
- **`DirectTests`** (Kestrel on loopback, a raw client):
  - frames held while the probe is out arrive after the welcome, in order;
  - a client that never answers is served through the stream, in order, after the 2 s hold;
  - an unsolicited pong, or one with the wrong payload, does not detach;
  - a client's ping during the probe is answered, and the probe is sent again;
  - after the switch, a client's ping gets its pong on the socket;
  - TLS never detaches;
  - a reader that stops reading for 8 MB of frames (partial sends, the pending path) gets every byte in order;
  - the switch off sends no probe;
  - 40 connections, a quarter of them never answering, each see 200 frames once and in order.
- **`WakeBatch` (PubsubTests):** a batch sets each wake once, after every frame is in. Nested scopes, a throwing scope and a flush
  behave. Eight threads publishing in scopes lose no wake.
- **The line's hold (BroadcastsTests):**
  - wakes come after the last place in flight publishes;
  - they come within the limit when a place never fills (the timer);
  - with the hold off, they come as each turn ends;
  - 3,000 places filled in random order from many threads reach 8 readers in commit order, with no wake lost.
- **Compact JSON (JsonTextTests):** compact strings parse to the same text (including `</script>`, controls, U+2028), and the
  bytes escape nothing JSON doesn't need. A Turbo Stream frame decodes to the Rails frame's value.
- **Delivery counts:** in all 27 tier 3 cable phases (3 apps × 3 client counts × 3 reps), every client subscribed and every
  posted message reached every client.
- **Pixel parity** (`bin/pixel-parity` on image `72ddf9f`; reports under `parity/out/pixel-parity-r2-cable/`, gitignored):
  - crowd 24/24, custom_styles 32/32, first_run 16/16 and restricted 8/8;
  - on the default seed, `realtime/**` 104/104 and all 182 `interactions` cells.
  - 366/366 pixel-equal, 0 flaky.
  - One non-screenshot cell differs: `pwa/manifest/custom_styles`, server layer only. It is the manifest's known JSON escaping,
    the same cell as in round 1, and the gate does not count it.
  - Not re-run: the default seed's static-page slices (rooms, messages, auth, search, pwa, account, errors, users; 578 cells in
    round 1). They render pages that no Cable frame changes during capture, so this unit's changes cannot reach them, and the
    frames' encoding is checked by the decode tests above. The round verifier's full run covers them.
- **Durability:** untouched. Nothing here touches a write's commit, and group commit and `synchronous` are as in round 1.
- **Defaults:** the three switches are on by default and none weakens durability. The only cost a person could see is the hold:
  a live message can reach a subscriber up to 1 ms later while another post is mid-render. Measured end to end, delivery got faster.

### post_message

The change touches the post's broadcast path, so `post_message` ran on the image (`t3-post`, 1 rep). It read 10,057 req/s at c=16,
against round 1's 13,215. CPU per request was the same (231.8 µs against 230.0), so the server was waiting, not working.

The investigation, in the same session:
- **Environment check:** the untouched F# port read 8,689 against its round-1 8,780, so the environment was normal.
- **First A/B:** round 1's source as a mounted build (`642c7ae`, `t2-post-base`) read 13,151, against 10,269 for the image. But
  the control's warm-up settled at 30 s, and the image's ran to its 90 s maximum.
- **Same warm-up for both:** with a fixed 90 s warm-up (`t2-post-base90`, `t2-post-new90`) they are level: 10,972 against 11,044
  req/s, and 231.4 against 230.7 µs per request.
- **The cause:** both builds post at about 13.5k for 70 s, then dip to 5-9k in some 2 s windows. The difference was where the
  warm-up stopped, not the change.
- The dip itself is round 1's code too. It is not explained here (deferred).

| run | build | c | req/s | CPU µs/req | warm-up |
|---|---|---|---|---|---|
| `t3-post` | R2.1 image | 1 | 3,340 | 592.1 | 30 s, settled |
| `t3-post` | R2.1 image | 16 | 10,057 | 231.8 | 91 s, reached the maximum |
| `t3-post-control` | the F# port (control) | 1 | 3,007 | 644.9 | 30 s, settled |
| `t3-post-control` | the F# port (control) | 16 | 8,689 | 356.1 | 30 s, settled |
| `t2-post-base` | round 1's source, mounted | 16 | 13,151 | 232.2 | 30 s, settled |
| `t2-post-new` | R2.1 image | 16 | 10,269 | 232.2 | 90 s, reached the maximum |
| `t2-post-base90` | round 1's source, 90 s warm-up | 16 | 10,972 | 231.4 | 90 s, fixed |
| `t2-post-new90` | R2.1 image, 90 s warm-up | 16 | 11,044 | 230.7 | 90 s, fixed |

## The server-sent-events prototype: measured, left off

**What it is:** `GET /sse` in the standalone F# Cable server (`bench/cable/fsharp`, `bench/cable/run --sse`, `driver.py --transport sse`).
It streams the same broadcasts as an event stream, one `data:` line each (the Turbo Stream as its JSON string), through Kestrel's
response.

**What it measured:** one run on macOS, 1,000 clients, 600-byte messages ([`cable-run-macos.jsonl`](oncrack-r2-cable/cable-run-macos.jsonl)):

| server CPU per delivery | F# WebSocket (this unit) | F# SSE | Rust WebSocket |
|---|---|---|---|
| burst of 200 | 1.00 µs | 0.80 µs | 0.75 µs |
| lone broadcast | 48.5 µs | 49.2 µs | 28.3 µs |

**Why it stays off:**
- It does not beat Rust's fan-out in either measure.
- In the app it could not use direct writes, the change that took the WebSocket from 10.2 to 4.4 µs per delivery. An event stream
  has no way back on the same connection, so nothing can prove Kestrel's pipe is empty, and it would stay on the pipe.
- Adopting it would also mean changing the page's stream sources and keeping a second channel for presence, typing and reads.

It is not in the app, so the parity question does not arise.

## Deferred

- **The load generator's ceiling at 1,000 clients.** A raw-socket cable client (no tungstenite, no UTF-8 check, markers searched in
  the read buffer) would move it. Until then 1,000 clients measures the harness as much as the servers.
- **Gather sends.** `Memmove` is still about 8% of the server's CPU: frames are copied into the send buffer, which is cache-hot.
  A per-connection `SocketAsyncEventArgs` with a buffer list would send the shared payloads as they are.
- **Sends per delivery.** onCrack makes 0.28 sends per delivery, Rust 0.19. The kernel's send path is now 58% of onCrack's CPU,
  so fewer, larger writes are the next lever.
- **A lone broadcast** costs about 1.7x Rust's in the standalone bench (48.5 against 28.3 µs per delivery on macOS). That is the
  thread pool spinning for the next of the 1,000 continuations it has just been given, as `cable-fanout.md` found.
- **Pss** is 2.5-2.9x Rust's. Most of it is the GC heap's high-water mark from the saturated phases (Server GC, 64 MiB gen0 per
  heap), not per-connection state. `DOTNET_GCgen0size` affects every HTTP workload, so it needs a unit of its own.
- **Posting at c=16 dips after about 70 s**, in round 1's code and this unit's alike.
- **The default seed's static-page parity slices**, left to the round's verifier (above).

## Reproducing

All inside colima unless noted. The tier 3 image was built from `72ddf9f`; `bin/clean-docker` ran after it.

```sh
CAMPFIRE_REVISION=$(git rev-parse HEAD) parity/bin/candidate build
for rep in 1 2 3; do for app in rust fsharp oncrack; do bench/results/oncrack-r2-cable/review/part.sh $app $rep; done; done   # bench/run orders each rep
python3 bench/results/oncrack-r2-cable/review/table.py --json
bench/cable/perf --app oncrack --clients 1000 [--loadgen]                     # profile and sends per delivery
bench/cable/run both --sse                                                    # on macOS: the standalone servers and the SSE prototype
bin/pixel-parity --seeds crowd,custom_styles,first_run,restricted; bin/pixel-parity --seeds default --only 'realtime/**'   # and the interactions, in two lists
bench/quick log bench/results/oncrack-r2-cable/t3 --unit r2-cable --tier 3 --kept true --build sha256:449b485c8a0e --commit 72ddf9f --change "..."
```
