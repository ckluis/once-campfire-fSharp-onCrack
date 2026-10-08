# onCrack unit R2.4: one connection

Date 2026-10-08, branch `crack`. Code commits `82168d8` (the scheduling change), `46deb83` (cheap paths), `4e12ec8` (image). Image
`campfire-oncrack:app` `sha256:c4942d0a4aa7` (label `4e12ec8`); `campfire-fsharp:app` (the port) untouched. Raw data in
[`oncrack-r2-c1/`](oncrack-r2-c1/); every table below is printed by [`review/table.py`](oncrack-r2-c1/review/table.py) (its output is
[`review/table.txt`](oncrack-r2-c1/review/table.txt)) or quoted from a file named beside it. Console-only runs are in
[`evidence/console-notes.txt`](oncrack-r2-c1/evidence/console-notes.txt).

onCrack is scored on its own terms (plan rule 4). It is not a like-for-like port result.

## Verdict

- **Reads at one connection were already done by R2.3** (replays on the event thread): 0.48-0.50 cores busy against Rust's 0.89-0.94, and
  17-19 µs of CPU per request against 140-162. This unit did not change them.
- **What was left at c=1 was every request that is not a replay**, and it was expensive: `/up` cost 110 µs and 2.03 cores, a post 393 µs
  and 1.9 cores. Each hop to the thread pool woke a worker that then spun for about 100 µs. Now:
  - **A post** costs **245.6 µs** of CPU at **1.27 cores** (R2.3: 391.6, 1.91; Rust 408.7, 1.13). Req/s 5,172 (R2.3 4,876; Rust 2,759):
    **1.87x Rust, 1.70x the port.** p50 / p99 0.17 / 0.29 ms (R2.3 0.18 / 0.39).
  - **`/up`** costs 22.4 µs at 0.54 cores (was 114, 2.11; Rust 44.8, 0.66): 24,004 req/s, 1.62x Rust.
- **c=16 and c=64 did not lose**, except one cell: `spread` reads are **6% lower** (87-89k against R2.3's 93.6k; same-session A/B
  below), the price of pool workers that do not spin. Everything else at c=16/64 is level or higher.
- **Tier 3 geometric mean of the five** (round 1's Rust and port medians): c=1 **3.72x Rust, 3.21x the port** (R2.3: 3.60x, 3.11x);
  c=16 **5.10x, 3.84x** (R2.3: 4.91x, 3.70x). The gain is almost all in the post rows: the read rows are within noise of R2.3.
- **Correct:** every response 2xx, 0 connection errors in all tier 3 runs; post rows equal the answers; nothing here changes what a request
  returns, only which thread runs it (details under Checks).

## Where the second core went

R2.3's tier 2 left the pool with the requests that are not replays. [`evidence/threads-base.txt`](oncrack-r2-c1/evidence/threads-base.txt) is the
R2.3 behavior (`CAMPFIRE_INLINE_SOLO_MS=off`, default spin), [`threads-shipped.txt`](oncrack-r2-c1/evidence/threads-shipped.txt) the shipped build, both
`THREADS=1 bench/paths --conc 1` (the new per-thread CPU report: `/proc/<pid>/task`, grouped by thread name), CPU per post:

| Thread | R2.3 behavior | shipped |
|---|---|---|
| `.NET TP Worker` (x4) | 373.7 µs (the request, plus spinning) | 76.4 |
| `.NET Sockets` (event threads) | 9.5 | 162.5 (the request itself, in place) |
| writer, checkpointer, GC | 16.4 | 15.9 |
| **total** | **399.5 µs, 1.99 cores** | **255.0 µs, 1.30 cores** |

A hop is a futex wake, a worker switching in, and then `ThreadNative_SpinWait` and `sched_yield` until the spin limit: 13.9M syscalls in 8 s for
`/up` at 18k req/s (750 a request). `perf` on a post (`bench/results/oncrack-r2-c1/perf-post-solo/`, the solo build before spin 0) had the pool at
45% of the CPU and 14% of all samples in `ThreadNative_SpinWait`; the thread report counted 14.6 involuntary context switches a post on the pool's
workers (0.15 after spin 0): the spinning workers took the cores the request needed. `bench/c1-wakes` (new: futex calls per request by thread and managed call chain) shows what still wakes the pool after the change,
three times per post: the push job's channel (`Writer.afterCommitAlone` -> `TryWrite`), `WebPushPool.DeliverLater`'s `Task.Run`, and a worker waking
another. Each is asynchronous work the Rails app does too (the push job reads the room's subscriptions and queues the notifications), so they stay.

## What changed

1. **Solo event threads run the app in place** (`EventThreadWatch`, `CAMPFIRE_INLINE_SOLO_MS`, default 200; commit `82168d8`).
   - Each event thread remembers the connection it last served and since when it has served only that one. An app request that arrives on a thread
     that has served only its own connection for 200 ms runs right there: no hop, no wake, no spin.
   - The first request of a connection, and every request after the thread served another connection in the window, still hops to the pool, so
     nobody's request ever waits behind a slow one *by this rule's choice*. (A request already running on an event thread blocks a connection that
     arrives on that thread later for as long as its synchronous part runs; that is bounded by one request's CPU time between awaits, and a
     connection that arrives starts the window again.)
   - Never for an `Upgrade` request.
   - `off` restores R2.3. `0` runs every app request in place, which is how the App suite was stressed (Checks).
2. **Idle pool workers do not spin** (`DOTNET_ThreadPool_UnfairSemaphoreSpinLimit=0`, set by `Program.main` unless the container gives a value;
   only while `CAMPFIRE_INLINE` is on).
   - R2.3 rejected this setting because, with every hit going through the pool, c=16 fell 29%. Hits no longer go through the pool, which is what
     changed the answer.
   - The AOT image's boot script used to set a longer spin; removed (a post at c=1 cost 405 µs with it and 255 without, level at c=16).
3. **Cheap paths** (`Campfire.Kit.CheapPaths`, `/up`, `/up.html`, `/up.json`; commit `46deb83`): requests the app answers in microseconds with no
   I/O run in place whatever else the thread serves. Without it, spin 0 cost `/up` 30% at c=16 (182k -> 124k req/s: a hop is now a futex
   wake per request). With it `/up` is 189k at c=16 and 236k at c=64 (spin on, hop: 182k, 197k).

All three are scheduling only: no durability, ordering or caching change.

## The settings matrix

Posts, tier 2 (mounted build of the shipped code, one rep each, one session, `bench/quick --routes post_message`; req/s with CPU µs per post in
brackets). Env: `CAMPFIRE_INLINE_SOLO_MS=off` and `DOTNET_ThreadPool_UnfairSemaphoreSpinLimit=0`.

| Setting | c=1 | c=2 | c=4 | c=16 | c=64 |
|---|---|---|---|---|---|
| R2.3 behavior (solo off, pool spins) | 4,638 (390) | 6,557 (340) | 6,680 (271) | 12,626 (184) | 17,618 (163) |
| solo only | 5,082 (345) | 7,704 (322) | 6,062 (254) | 15,373 (186) | 17,683 (162) |
| spin 0 only | 4,767 (266) | 7,252 (260) | 7,192 (225) | 11,589 (176) | 18,010 (158) |
| **solo + spin 0 (shipped)** | **4,898 (263)** | **7,994 (256)** | **8,079 (222)** | **15,817 (179)** | **17,806 (162)** |

Solo alone moves req/s (the request is not woken), spin 0 alone moves CPU (a woken worker goes back to sleep at once); together they do both.
c=16 posting is the cell the WAL-restart stall (R2.2, still open) swings between 10k and 16k, so the c=16 column is read for CPU, not req/s.

Spin values between (`DOTNET_ThreadPool_UnfairSemaphoreSpinLimit` is hex): post at c=1 costs 246 µs at 0, 251-264 at 0x8-0x10, 271 at 0x14, 299 at
0x25 and 345 at the default 0x46, and `spread` reads are 85.9k, 88.2k and 91-92k at 0x8, 0x14 and the default against 85.9-87.2k at 0. The
trade is linear; there is no cheap middle. Cable fan-out at 100 / 500 / 1,000 clients is level with spin 0 (5,191 / 1,524 / 819 msgs/s and
5.76 / 4.41 / 4.22 µs per delivery, against 5,123 / 1,530 / 822 and 6.01 / 4.40 / 4.27).

## Tried and not shipped

| What | Result | Why not |
|---|---|---|
| A middle spin (0x8, 0x10, 0x14, 0x25) | see above | CPU per post and `spread` move together, linearly |
| `CAMPFIRE_INLINE=all` | `/up` c=16 190k, c=64 239k; R2.3 measured `spread_mixed` posts -15% | cheap paths take the benefit where it is safe |
| Pinning the server to fewer cores (`SERVER_CPUS`) | 2 cores: post 214 µs, 1.11 cores, req/s level; 1 core: post 3,286 req/s, room page 20k (was 26k) | a deployment choice, not a default; level on every other cell |
| Fewer worker threads | not run alone | with spin 0 an idle worker costs nothing; the four pool workers a post uses exist because three things wake it (above) |
| `SO_BUSY_POLL` | not run | no NAPI device on loopback (R2.3) |
| Dedicated threads for the push job | not built | the job's read and the queued deliveries are real work; the wakes left are 3 x ~25 µs |

## Tier 3

`bench/quick`, 3 reps, `campfire-oncrack:app` `sha256:c4942d0a4aa7`, default seed, `SERVER_CPUS=0-3 LOADGEN_CPUS=4-7`, warm-up to flat. Rust and the
port are round 1's same-session medians (`oncrack-round1-final/`), as R2.3 used; req/s with CPU µs per request in brackets, and for onCrack R2.4
the server's cores busy.

| Workload | c | Rust | F# port | onCrack R2.3 | **onCrack R2.4** | **/ Rust** | **/ port** | / R2.3 | p50 / p99 ms (R2.3) |
|---|---|---|---|---|---|---|---|---|---|
| room page | 1 | 6,395 (143.8) | 7,555 (210.5) | 26,080 (19.3) | **26,590 (18.7, 0.50)** | **4.16x** (CPU 0.13x) | **3.52x** (CPU 0.09x) | 1.02x | 0.04 / 0.05 (0.04 / 0.05) |
| room page | 16 | 28,582 (122.5) | 39,459 (90.3) | 174,412 (17.7) | **176,184 (17.4, 3.10)** | **6.16x** (CPU 0.14x) | **4.46x** (CPU 0.19x) | 1.01x | 0.08 / 0.21 (0.08 / 0.21) |
| messages page | 1 | 6,684 (140.6) | 8,155 (201.4) | 25,963 (18.9) | **27,186 (18.0, 0.49)** | **4.07x** (CPU 0.13x) | **3.33x** (CPU 0.09x) | 1.05x | 0.04 / 0.05 (0.04 / 0.05) |
| messages page | 16 | 30,158 (114.2) | 42,404 (83.7) | 184,722 (16.4) | **182,906 (16.4, 3.00)** | **6.06x** (CPU 0.14x) | **4.31x** (CPU 0.20x) | 0.99x | 0.08 / 0.20 (0.08 / 0.20) |
| sidebar | 1 | 6,134 (149.0) | 7,838 (184.0) | 26,723 (18.1) | **27,784 (17.1, 0.48)** | **4.53x** (CPU 0.11x) | **3.54x** (CPU 0.09x) | 1.04x | 0.04 / 0.05 (0.04 / 0.05) |
| sidebar | 16 | 28,378 (122.5) | 38,001 (95.0) | 197,204 (14.8) | **196,077 (15.0, 2.93)** | **6.91x** (CPU 0.12x) | **5.16x** (CPU 0.16x) | 0.99x | 0.08 / 0.19 (0.07 / 0.18) |
| search | 1 | 5,509 (162.2) | 5,734 (328.9) | 27,500 (17.5) | **27,351 (17.5, 0.48)** | **4.96x** (CPU 0.11x) | **4.77x** (CPU 0.05x) | 0.99x | 0.04 / 0.05 (0.04 / 0.05) |
| search | 16 | 26,396 (124.6) | 33,773 (108.2) | 192,332 (15.3) | **194,734 (15.1, 2.94)** | **7.38x** (CPU 0.12x) | **5.77x** (CPU 0.14x) | 1.01x | 0.08 / 0.19 (0.08 / 0.19) |
| post a message | 1 | 2,759 (408.7) | 3,034 (636.0) | 4,876 (391.6) | **5,172 (245.6, 1.27)** | **1.87x** (CPU 0.60x) | **1.70x** (CPU 0.39x) | 1.06x | 0.17 / 0.29 (0.18 / 0.39) |
| post a message | 16 | 7,082 (388.1) | 8,780 (354.8) | 10,664 (186.2) | **12,782 (175.0, 2.24)** | **1.80x** (CPU 0.45x) | **1.46x** (CPU 0.49x) | 1.20x | 0.84 / 4.39 (0.89 / 4.60) |

Geometric means of the five: c=1 **3.72x Rust, 3.21x the port**; c=16 **5.10x, 3.84x**. Against R2.3: 1.03x and 1.04x.

Cores busy at c=1, Rust -> R2.3 -> R2.4: room page 0.92 -> 0.50 -> 0.50, sidebar 0.91 -> 0.48 -> 0.48, search 0.89 -> 0.48 -> 0.48,
**post 1.13 -> 1.91 -> 1.27**.

The post c=16 reps read 10,964, 12,782 and 14,320 (`oncrack-r2-c1/tier3`): the WAL-restart stall of R2.2 is still in the window, so the
+20% over R2.3 is not claimed as this unit's; the same-session matrix above shows solo helping at c=16 (12.6k -> 15.8k) and CPU per post
falling 184 -> 179 µs, which is the stable signal.

### Other routes (one rep, 20-40 s warm-up)

| Route | c | Rust (round 1) | onCrack round 1 | **onCrack R2.4** | / Rust | p50 / p99 ms |
|---|---|---|---|---|---|---|
| /up | 1 | 14,782 (44.8, 0.66) | 18,615 (114.4, 2.11) | **24,004 (22.4, 0.54)** | 1.62x | 0.04 / 0.06 |
| /up | 16 | 116,041 (22.4, 2.60) | 166,137 (22.3, 3.67) | **185,900 (17.6, 3.26)** | 1.60x | 0.07 / 0.22 |
| /up | 64 | 132,304 (20.4, 2.69) | 188,325 (20.1, 3.74) | **236,629 (15.2, 3.60)** | 1.79x | 0.22 / 1.18 |
| avatar | 1 | 20,190 (33.5, 0.67) | 24,674 (87.4, 2.16) | **29,078 (15.9, 0.46)** | 1.44x | 0.03 / 0.05 |
| avatar | 16 | 141,004 (15.7, 2.22) | 170,736 (21.8, 3.72) | **203,063 (13.8, 2.81)** | 1.44x | 0.07 / 0.18 |
| avatar | 64 | 167,106 (13.8, 2.29) | 192,565 (19.6, 3.77) | **276,408 (12.2, 3.37)** | 1.65x | 0.20 / 0.73 |
| CSS file | 1 | 20,201 (33.7, 0.68) | 26,669 (81.4, 2.16) | **30,846 (14.6, 0.45)** | 1.53x | 0.03 / 0.04 |
| CSS file | 16 | 150,301 (14.8, 2.22) | 186,488 (20.3, 3.79) | **230,143 (11.6, 2.66)** | 1.53x | 0.07 / 0.16 |
| CSS file | 64 | 177,509 (12.8, 2.30) | 217,948 (17.2, 3.73) | **321,002 (10.4, 3.35)** | 1.81x | 0.18 / 0.52 |
| post a message | 64 | 4,459 (387.0, 1.72) | 17,684 (186.6, 3.31) | **17,757 (162.5, 2.88)** | 3.98x | 3.16 / 8.57 |

**The avatar and CSS rows looked too good (+20-47% over round 1) and are not this unit's.** They are served from the front's cache on the event
thread, which R2.3 did and did not re-measure. Control: the same build with `CAMPFIRE_INLINE=off` (pool) reads avatar 170,311 / 174,887 and CSS
191,185 / 220,648 at c=16 / 64 at 19.6-21.8 µs, round 1's numbers ([`evidence/assets-inline-off.txt`](oncrack-r2-c1/evidence/assets-inline-off.txt)).
The server kept 2.7-3.4 of its 4 cores busy at 10-14 µs a request, which fits what Kestrel plus a send costs once the pool is gone.

### Realistic workloads (3 reps, c=16 readers)

| Workload | lane | Rust | F# port | onCrack R2.3 | **onCrack R2.4** | / R2.3 | / Rust | / port |
|---|---|---|---|---|---|---|---|---|
| mixed | reads | 18,597 | 24,232 | 45,187 | **43,029** | 0.95x | 2.31x | 1.78x |
| mixed | posts | 688 | 753 | 1,355 | **1,377** | 1.02x | 2.00x | 1.83x |
| spread | reads | 25,655 | 29,902 | 93,619 | **87,243** | 0.93x | 3.40x | 2.92x |
| spread_mixed | reads | 13,155 | 13,584 | 11,322 | **11,317** | 1.00x | 0.86x | 0.83x |
| spread_mixed | posts | 319 | 393 | 674 | **683** | 1.01x | 2.14x | 1.74x |
| search_spread | reads | 8,468 | 18,942 | 16,408 | **16,695** | 1.02x | 1.97x | 0.88x |

- **`spread` lost 6-7%, and that one is this unit's.** Same-session tier 2, alternating: default spin 91,163 and 92,092, spin 0 87,199 and 85,870 at
  the same CPU per request (38.1-38.9 µs). `spread` misses and goes to the pool at c=16, and a worker asleep takes a wake-up where a spinning one
  took none. `DOTNET_ThreadPool_UnfairSemaphoreSpinLimit=46` brings it back (and costs posts at c=1 their 100 µs). Still 2.92x the port.
- `mixed` reads read 0.95x R2.3's tier 3, but the same-session A/B (`t2-mixed-spin-*`: 41.7k default, 42.5k spin 0) shows no loss; R2.3's 45.2k
  was a high window. `spread_mixed`, the cell R2.3 left behind, is unchanged (the scheduling it lost on is the pool's, and the solo rule does
  not apply with 17 connections).

## Checks

- **Statuses:** every response 2xx, 0 connection errors in all tier 3 runs (10 classic, 12 other-route cells, 12 realistic) and every tier 2 run.
- **Rows:** post rows written equal the 2xx answers in every phase.
- **Attack tests:**
  - `EventThreadWatchTests` (5): the first request of a connection waits out the window; a second connection on the thread starts it again
    for both; a thread is judged by its own connections only; a negative window is never solo; cheap paths match exactly.
  - The whole App suite behind the front server with every app request run in place: `CAMPFIRE_TEST_FRONT=1 CAMPFIRE_INLINE_SOLO_MS=0 dotnet
    test --project tests/Campfire.App.Tests` (libvips on `DYLD_FALLBACK_LIBRARY_PATH`): 234 passed, 1 skipped, 1 failed: the avatar-removal test, which fails the
    same way on the pool and predates R2.3 (Thruster's public cache keeps the old avatar). Uploads, the bot API, variants and the read-cache tests
    all pass on the event thread, so nothing in the app blocks on the thread that would complete its own read.
- **`bin/verify`:** 1,116 tests, 1,108 passed, 7 skipped, 1 failed: `FrontTests.closes idle and slow connections`, which fails the same way on
  R2.3's commit (`e29ee2b`): it read the idle timer's start from the first segment of a chunked answer and got the terminating chunk
  `0\r\n\r\n` (5 bytes) from the second. Fixed in the test (it reads the whole answer first); the Kit suite then passes.
- **Cable, tier 2:** level with spin 0 (above).
- **Cold start:** 224 ms, as R2.3.
- **Pixel parity:** `bin/pixel-parity --seeds default --only 'realtime/**,interactions/sidebar/**'` (the states that revisit pages after a change)
  on the image measured above: **116/116 screenshots pixel-equal**, 0 flaky, 0 errors, 1,233 s ([`pixel-parity.json`](oncrack-r2-c1/pixel-parity.json)).
- **Not run:** the full lean matrix on every seed (the round verifier's job); `bin/kit-differential http` (no change under the kit's adapter);
  the AOT image through its Dockerfile (measured mounted: a post 255 µs, 1.28 cores; `/up` c=16 177k).

## Deferred

1. `spread` (and any workload whose reads miss at c=16) pays for sleeping workers. A pool that spins only while the previous work item
   arrived within a few µs (adaptive, ours rather than the runtime's) would keep both; the runtime's own knob is a constant.
2. The three pool wakes per post (push job channel, `DeliverLater`'s `Task.Run`, a worker waking a worker): about 25 µs each, 71 µs of the
   255. Running the push job's read on the posting request's thread before the response would remove the first two for a read the job makes
   anyway, at the cost of moving that work onto the request's latency.
3. The c=16 post stall (R2.2), still hiding any change in that cell.
4. SQLite's mutex contention: `Conn.step` shows futex calls (about 5 a post) when the push job reads while the next post runs.

## Reproducing

All inside colima; `bin/clean-docker` and `bin/clean-parity` after the rebuild.

```sh
bin/publish-mounted /var/tmp/campfire-mounted
THREADS=1 PERFSTAT=1 bench/paths --mounted /var/tmp/campfire-mounted --conc 1 --secs 8 --warmup 12 POST /up /rooms/@ROOM@
bench/paths --mounted /var/tmp/campfire-mounted --env 'CAMPFIRE_INLINE_SOLO_MS=off DOTNET_ThreadPool_UnfairSemaphoreSpinLimit=46' --conc 1 POST   # R2.3's behavior
bench/c1-wakes --mounted /var/tmp/campfire-mounted POST          # futex calls per request, by call chain
bench/quick --routes post_message --concs '1 2 4 16 64' --reps 1 --mounted /var/tmp/campfire-mounted --out DIR   # the matrix
CAMPFIRE_REVISION=$(git rev-parse HEAD) parity/bin/candidate build
bench/quick --only oncrack:N --part K/2 --out bench/results/oncrack-r2-c1/tier3            # N = 1..3, K = 1..2
bench/quick --routes up,avatar,static_css,post_message --concs '1 16 64' --reps 1 --warmup 20 --out bench/results/oncrack-r2-c1/tier3-extra
bench/quick --real --only oncrack:N --out bench/results/oncrack-r2-c1/tier3-real
python3 bench/results/oncrack-r2-c1/review/table.py
CAMPFIRE_TEST_FRONT=1 CAMPFIRE_INLINE_SOLO_MS=0 dotnet test --project tests/Campfire.App.Tests -c Release
```
