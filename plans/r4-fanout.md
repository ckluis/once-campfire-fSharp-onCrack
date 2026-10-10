# R4.2 plan: Cable fan-out at 1,000 and 2,000 clients, 2026-10-10

Design only; a builder implements it in about 2 hours. The baseline is `bench/results/oncrack-r4-fanout-baseline.md` (R4.1, raw
client, `--window 128`). At 1,000 clients onCrack delivers 1.23x Rust f9dca47 (paired per rep 1.03-1.23x), at 2,000 clients 1.06x
(0.81-1.24x). Server CPU per delivery is 2.55 / 2.64 us against Rust's 3.17 / 2.86. Pss saturated is 302 / 353 MB against Rust's 114 / 134.

**Goal:** beat Rust clearly at 1,000 and 2,000 clients on msgs/s and on CPU per delivery, measured against a Rust control in the same
session, and narrow the memory gap.

## What the profile says (and what it rules out)

The profile is one `bench/cable/perf` run on the R4.1 image (`campfire-oncrack:app` `sha256:69deaa8cdf60`) at 1,000 clients, 8 s
saturated, `SERVER_CPUS=0-3 LOADGEN_CPUS=4-7`. It read 1,222 msgs/s under perf, with host load 1.5 before and 4.1 after.
- Files: [`perf-oncrack-1000.txt`](../bench/results/oncrack-r4-fanout-plan/perf-1000/perf-oncrack-1000.txt) and
  [`breakdown.txt`](../bench/results/oncrack-r4-fanout-plan/perf-1000/breakdown.txt).
- Tool: [`breakdown.py`](../bench/results/oncrack-r4-fanout-plan/breakdown.py), run over the call chains that
  `KEEP_SCRIPT=1 bench/cable/perf` now keeps. The 6 MB chain file itself is not committed.

| where | share of the app's samples |
|---|---|
| `Writer.Send`: frames to the socket | **77.6%** |
| - `Memmove` copying frames into the pooled send buffer | **15.9%** |
| - the `sendto` syscall | 60.5% |
| -- `copy_from_user` (per byte) | 18.4% |
| -- loopback receive softirq, charged to the sender (per skb) | 16.8% |
| -- page and skb allocation, memcg charge (per byte, mostly; `clear_page` is 4.2%) | 10.7% |
| -- transmit path (per skb) | 8.0% |
| -- the rest of the syscall: entry, `lock_sock`, bookkeeping (per send) | 6.6% |
| the rest of the connection loop (drain 1.6%, wake, state machine) | ~3% |
| publishing (`Group.Publish`, `WakeBatch`, `BroadcastOrder`); `Wake.Set` alone 0.2% | 2.4% |
| the posts themselves (`messages#create`, render, SQLite, Kestrel HTTP): everything outside the connection loop | 19.3% |
| GC | 1.5% |

Other measurements from this profile:
- **Bytes per delivery:** 10,397 bytes on the wire, in 2.00 frames: the message's ~10.3 KB append and the ~100-byte unread ping.
  Every load generator client signs in as one user, so all of them share both groups.
- **Sends per delivery:** 0.075 (`perf stat`), against R4.1's 0.065, so a write carries about 13-15 messages.

The brief's numbers for sends per delivery (0.283 against Rust's 0.19) are round 2's, measured with the slow client. With R4.1's client
they are 0.065 against 0.031: Rust's writes hit its 64-frame `max_write_batch` cap, and ours carry about half that.

What this rules in and out:
1. **The one large user-space cost is the copy into the send buffer, 16%.** Rust does not make it: its `Sink::send` writes the
   shared payloads with `write_vectored`, with `IoSlice` pairs of header and payload (`rust/crates/cable/src/socket.rs:394`). This is
   lever 1.
2. **Waking and dispatch are already cheap.** Wakes, the thread pool, ring reads and the state machine come to about 3%. "One wake
   per batch" is done (R2.1's `WakeBatch`). A different scheduler (writer threads instead of pool tasks) has little left to win.
3. **Fewer sends wins at most about 5%.** Per-send kernel work is 6.6%. Larger writes would also trim the per-skb share a little (a
   partial last segment per write). Holding writes back to make them larger has a cost in this harness: the saturated phase keeps 128
   messages in flight, so throughput is about 128 / (post to last client). Added latency comes straight off msgs/s unless CPU is the
   only limit, and R4.1 found the window and the CPU limits close together. So no timer-based coalescer (below, under "Not to do").
4. **Per-byte kernel work is about 30% and the per-skb work about 25%.** Both scale with the 10.4 KB frame. Rust pays the same per
   byte. Shrinking the frame is a real lever, but it carries pixel risk and needs its own unit (deferred, with numbers).
5. **The posts are 19% of the CPU at 1,000 clients,** about 0.5 us of the 2.55 per delivery, or ~0.6 ms of CPU per post. A post
   alone costs 242 us (R2.4). This is the post path running cache-cold beside the fan-out. Rust pays its own post cost too.
   Deferred.
6. **Memory: per connection is close to Rust.** From 1,000 to 2,000 clients, idle Pss grows 20 KB a connection against Rust's
   16 KB. The gap is fixed and heap-shaped:
   - the JIT runtime's mappings (Pss at boot is 85 MB against 33, R2.5);
   - the GC heap's high-water mark from the saturated phases. The suite runs 100, 500, 1,000 and 2,000 clients in one container, and
     at 100 clients the posters post 6,000 times a second;
   - large pooled send buffers. A batch of ~15 messages is about 150 KB, so `ArrayPool.Shared` rents arrays from the 128 KB to 1 MB
     buckets. They live on the LOH, and the pool keeps them per thread and per core. This is not measured yet, and lever 1 removes
     them.

## The changes, ranked by expected gain

### 1. Gather writes: send the shared frame payloads in place (expected -12 to -15% CPU per delivery; memory down, unmeasured)

**What.** Applies only on a detached connection (`Writer.Detach` done, plain TCP). `Writer.Send(frames)` builds one gather list and
makes one non-blocking `sendmsg`, as Rust does:
- the list is header_i, payload_i for each frame;
- each header is 2-10 bytes in a scratch buffer;
- each payload is `frame.Bytes` or `frame.Deflated`, the shared array itself, never copied.

The stream path (before the probe's pong, TLS, `CAMPFIRE_CABLE_DIRECT=off`) keeps today's copy, because Kestrel's pipe copies anyway.

**How, in `Socket.fs`:**
- At `Detach`, set `direct.Blocking <- false`. Kestrel only issues asynchronous operations on its sockets, and on Linux the descriptor
  is already non-blocking. The flag makes .NET's synchronous `Send(IList<ArraySegment<byte>>, SocketFlags, byref SocketError)` one
  `sendmsg` attempt that returns `WouldBlock` (and a partial count) instead of waiting. Check this first, before anything else: in
  .NET's `SocketPal.Unix`, a handle that is not `IsNonBlocking` sends through `AsyncContext.Send` and blocks, so the flag is
  required. Confirm it with the test in step 1 below. A blocking send on a pool thread would stall the fan-out for up to the 30 s
  write timeout.
- Keep the scratch state thread-static: one `byte[]` for headers (grown as needed) and one `List<ArraySegment<byte>>`. The in-place
  path finishes before `Send` returns, so nothing per connection is added, which matters for memory.
- **Partial send or `WouldBlock`:** copy the unsent rest (from the right segment and offset) into a pooled buffer and hand it to the
  existing `FinishSend(SendAsync(rest), rest, pooled)` path. Its timeout and abort are unchanged. This path is rare once the client
  keeps up, and it is the one that needs care.
- **Any other `SocketError`:** raise `SocketException`, as `SendAsync` faults today. The connection ends.
- **Switch:** `Config.GatherWrites`, from `CAMPFIRE_CABLE_GATHER` (default on; `off` copies as today), read in `Boot.fs` beside
  `CAMPFIRE_CABLE_DIRECT`. Make `bench/cable/fsharp/Program.fs` read the same variable so that tier 1 can A/B it.
- **If the profile then shows .NET's gather call itself costing more than about 2%** (`SocketPal` `SendMsg`, `GCHandle` pinning per
  buffer, a handle array allocated per call): replace it with a P/Invoke `sendmsg(fd, msghdr, MSG_NOSIGNAL)`. Use the socket's
  `SafeHandle` with `DangerousAddRef`, a thread-static iovec block, and a thread-static `GCHandle[]` reused per call. That is a second
  change, measured on its own.

**Measure:**
- **Tier 0:** `bin/verify Cable`, plus the new test below.
- **Tier 1 (direction, macOS, minutes):**
  - Run `bench/cable/run fsharp --clients 1000 --bytes 10400 --burst 200` twice, alternating `CAMPFIRE_CABLE_GATHER=off` and on.
  - Read CPU per delivered message in the burst.
  - Confirm that the bench server's connections detach (`Server.DirectConnections`). Otherwise neither run exercises the change.
- **Tier 2 (about 3 min a pair):**
  - Build with `colima ssh -- bash -c "cd $PWD && bin/publish-mounted"`, then run
    `ONCRACK_MOUNT=/var/tmp/campfire-mounted SUITES=cable CABLE_CLIENTS="1000 2000" HTTP_ROUTES=up bench/run --apps oncrack --reps 1`.
  - Alternate `ONCRACK_EXTRA_ENV=CAMPFIRE_CABLE_GATHER=off` and on for 3 pairs, sampling `uptime` beside each.
  - Judge by server CPU per delivery first and msgs/s second. The host drifts 25-30% in 20 minutes, so read the pairs, not the means.
  - Once: `CABLE_SENDS=1`, which should show `sendmsg` in place of `sendto`.
  - Once: `KEEP_SCRIPT=1 bench/cable/perf --clients 1000` plus `breakdown.py`. `Memmove` under `Writer.Send` should be near 0.
- **Memory:**
  - Run `SMAPS=1 bench/mem cable:1000` with the switch off and on. That gives a fresh container, with no 100-client posting phase
    before it.
  - Also read the suite's Pss saturated at 1,000 and 2,000.
- **Tier 3:**
  - Rebuild the image: `CAMPFIRE_REVISION=$(git rev-parse HEAD) parity/bin/candidate build`, or the Dockerfile build `bench/run` uses.
  - Run R4.1's `review/part.sh` shape for Rust f9dca47 and onCrack, 3 reps, in alternating order, in one session, into a new
    results directory.
  - Skip the port to save 11 minutes; its R4.1 numbers stand as its reference.

**Correctness risk and the tests that catch it:**
- **Frame order and bytes on the wire.** The new frame bytes must equal the copy path's exactly: header encoding (7-bit, 16-bit and
  64-bit lengths, RSV1 on deflated payloads) and the order of frames.
  - New `SocketTests` case: gathered and copied writes are the same bytes. Random batches (1-80 frames, sizes 1, 125, 126, 127,
    65535, 65536 and 70000 bytes, deflate on and off) go out through a detached `Writer` on a loopback socket pair and through a
    copy-path `Writer` into a `MemoryStream`.
  - Run it twice: once with a reader that keeps up, and once with the server socket's `SendBufferSize` at 4 KB, with a reader that
    sleeps between small reads. That forces partial sends and `WouldBlock`.
  - The bytes must match exactly. Mutations it must catch: dropping the remainder's offset into the partial segment, or reusing the
    scratch header buffer before the remainder is copied.
- **A send that blocks.** New test: a detached `Writer` whose peer never reads. `Send` of 8 MB must return a pending `ValueTask` in
  under 100 ms, then time out and abort at the write timeout, as today (use a short timeout in the test). If `Blocking <- false` were
  missing, this test would hang.
- **The direct-write probe.** Nothing changes before `Detach`, and gather is used only after it. `DirectTests` cover the ordering
  across the switch: frames held during the probe, a client that never answers, an unsolicited or wrong pong, a ping during the probe,
  the 8 MB slow reader, and the 40 connections with a quarter never answering. All must pass unchanged, with the switch on and with it
  `off`.
- **Action Cable semantics.** The frames, their order and the lag rule (`reconnect: true` when a ring laps a subscriber) are
  untouched. `FanOutTests`, `GoldenTests` and the App suite's `BroadcastsTests` and `ChannelsTests` must pass.
- **Close.** A non-blocking socket must still close cleanly through Kestrel: the close handshake and an abort mid-send. The
  `DirectTests` close cases and `ServerTests` cover it.
- **Pixel parity of realtime states.** The wire bytes are identical by the first test, so this is a guard, not a hunt. Run
  `bin/pixel-parity --fast --only 'realtime/**'` on the default seed (104 cells), plus the interactions slice if time allows.
- **Every cable result:** `posted == complete` and `client.closed_midrun == 0`, at every client count.

### 2. Attribute the memory after lever 1 (no change; decides what memory work comes next)

Lever 1 removes the large pooled send buffers. What is left needs a split before anyone changes a GC setting. R2.5 measured 17 GC
settings on the HTTP workloads and kept none, so do not sweep them again blind.

**Measure:**
- `SMAPS=1 bench/mem idle:3 cable:1000 idle:5` and `... cable:2000 ...` with `CAMPFIRE_MEM_LOG_MS=500`. These give managed heap
  against the rest, gen0, gen1, gen2 and LOH committed, and Pss and anon per phase.
- The same on `campfire-oncrack:aot` (the opt-in Native AOT image). It shows the runtime-mapping floor; idle Pss there is 53 MB
  against 85.
- Record anon beside Pss. Pss counts shared runtime mappings that Rust does not have.

**Expected:** this is not a win in itself. It states how much of the gap is runtime mappings (AOT-only), how much is heap left behind
by the posts (the post path's allocation, R2.2/R2.5 territory), and how much is per connection (about 20 KB against 16).

**Risk:** none; it only measures.

**If a per-connection item stands out,** the candidates are:
- the `Channel<Received>` per connection;
- the 6 `Subscription`s, each with its identifier twice (raw and encoded);
- the upgrade request's `HttpContext`, which stays alive for the life of the socket.

Each is its own change, with `bench/mem cable:2000` before and after.

### 3. Batch-size knobs without new code (expected 0 to +5%; may be negative)

Do this only if lever 1 has landed and time remains.

**What:** two settings, each A/B'd at tier 2 as in lever 1, at 1,000 and 2,000 clients:
- `CAMPFIRE_CABLE_HOLD_US` at 1000 (the default) against 3000;
- `MaxWriteBatch` at 64 against 128 frames. This needs a `CAMPFIRE_CABLE_MAX_BATCH` read in `Boot.fs`. Rust is at its 64 cap and we
  average about 30 frames a write, so the cap rarely binds; that is what this checks.

Keep a setting only if CPU per delivery and msgs/s both improve in every pair, and paced p50/p99 at 100 clients do not get worse.

**Risk:** latency only. The hold delays wakes by at most its limit while a later post renders. Ordering is unchanged
(`BroadcastsTests`: commit order under 3,000 random places).

## Not to do in R4.2 (and why)

- **A timer or tick coalescer per connection.** At most about 5% to win (point 3 above). It adds latency, which the windowed
  saturated phase turns into lower msgs/s. R2.1's "yield before draining" lost 6%.
- **Writer threads that bypass the thread pool.** The pool, wakes and draining are about 3% together, and two writers on one socket
  are a frame-order hazard.
- **Another GC sweep.** R2.5 kept none of 17 settings. Do lever 2's attribution first.
- **`MSG_ZEROCOPY`.** Loopback and veth copy anyway. The client is local in every bench, and Rust copies too.

## Deferred (R4.3 candidates, with what is known)

- **Bytes per frame.**
  - What is known: about 30% of the CPU is per byte and about 25% per skb, and both scale with the 10.4 KB frame.
  - The message templates' literals (`Templates/Messages/_Message.fs`, `_Actions.fs`) hold about 480 bytes of indentation runs.
  - The JSON escapes about 280 attribute quotes as `\"`, which is about 8% of the frame between them.
  - Where the other ~5.5 KB comes from (inline SVG, signed URLs, form tokens) is not yet broken down.
  - Collapsing whitespace changes the server HTML, which the rules allow, but it can change rendering inside `pre`/`pre-wrap`
    contexts and `textContent`. It needs the full `realtime/**` and interactions pixel parity, on every seed.
- **The post path beside the fan-out:** 19% of the server's CPU at 1,000 clients, about 0.6 ms of CPU per post against 242 us alone.
  It is probably cache-cold.
- **A profile at 2,000 clients** after lever 1. CPU per delivery is higher there than at 1,000 (2.64 against 2.55 us), although the
  posts' share halves. That suggests per-connection cache misses, which only a profile can confirm.
- **The 100-client paced p99 of 22 ms** (R4.1), unexplained.

## The builder's 2 hours

| step | time |
|---|---|
| Write the two new socket tests against the current `Writer`. The bytes test passes trivially today; it is the harness. | 20 min |
| Implement lever 1 behind `CAMPFIRE_CABLE_GATHER`; `bin/verify Cable`; check that the non-blocking test does not hang. | 35 min |
| Tier 1 A/B on macOS (direction). | 5 min |
| Tier 2: `bin/publish-mounted`, 3 alternating pairs at 1,000 and 2,000 clients, one `CABLE_SENDS` pass, one perf profile. | 30 min |
| Lever 2's `bench/mem` runs (JIT, switch off and on; the AOT image). | 15 min |
| Gate: `bin/verify` (the whole suite), `bin/pixel-parity --fast --only 'realtime/**'`, `bin/clean-docker`, `bin/clean-parity`. | 15 min |

Tier 3 (rebuild the image, Rust and onCrack × 3 reps, about 25 min) follows if the tier 2 pairs agree, or else goes to the next
unit's opening.

## What "done" looks like

- A results file `bench/results/oncrack-r4-fanout.md` with:
  - the tier 2 pairs;
  - the same-session control;
  - CPU per delivery and msgs/s at 1,000 and 2,000 clients against Rust;
  - sends per delivery;
  - Pss and anon at 1,000 and 2,000;
  - the post-change profile's breakdown.
- AGENTS.md gets a paragraph for `CAMPFIRE_CABLE_GATHER`, and a line for `KEEP_SCRIPT` beside `bench/cable/perf`.
- Commit on `crack`.
