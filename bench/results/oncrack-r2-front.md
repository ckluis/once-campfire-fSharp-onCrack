# onCrack unit R2.3: a front-server fast path, and where a cached hit's time went

Date 2026-10-08, branch `crack`, code commit `09415ba`. Image `campfire-oncrack:app` `sha256:390e390e43fa` (label `09415ba`);
`campfire-fsharp:app` (the port) untouched. Raw data in [`oncrack-r2-front/`](oncrack-r2-front/); every table below is printed by
[`review/table.py`](oncrack-r2-front/review/table.py) from the raw runs, or quoted from a file named next to it.

onCrack is scored on its own terms (plan rule 4). It is not a like-for-like port result.

## Verdict

- **Five workloads, tier 3** (rebuilt image, 3 reps, `bench/quick`). The ratios use round 1's same-session Rust and port medians
  (`oncrack-round1-final/`):
  - Geometric mean at c=16: **4.91x Rust, 3.70x the port**. Round 1 was 3.84x and 2.89x.
  - Geometric mean at c=1: **3.60x Rust, 3.11x the port**. Round 1 was 2.06x and 1.77x.
- **Read pages:**
  - c=16: 174-197k req/s, 1.41-1.50x round 1's onCrack, at 14.8-17.7 µs of CPU per request (round 1: 26.7-30.1).
  - c=1: 26-27.5k req/s, 1.75-1.94x round 1, at 17.5-19.3 µs (round 1: 127-144).
- **Posts:**
  - c=1: 4,876, 1.77x Rust and 1.61x the port.
  - c=16: 10,664, below R2.2's 12,010. The WAL-restart stall R2.2 left open is still in the window: the reps read 10,362, 10,664 and
    12,293. I could not separate a change in that cell from the stall.
- **Realistic workloads, tier 3** (3 reps):
  - `mixed`: reads 45,187, 1.30x R2.2's tier 3.
  - `spread`: 93,619, 3.13x the port. R2.0 measured 28,547.
  - `search_spread`: 16,408, level with the fast path off.
  - **`spread_mixed` lost:** reads 11,322 against R2.2's 13,129 (-14%), posts 674 against 753 (-10%). The cause is the scheduling
    change (below), and it is the first deferred item.
- **Correct:**
  - Every response was 2xx, with 0 connection errors in 30 classic runs and 12 realistic runs.
  - Post rows equal the answers in every phase.
  - Decoded bytes are equal to Rust's on every probed route.
  - Nine new attack tests, each guard caught by a mutation.
  - The whole App suite also passes behind the front server.
  - Targeted pixel parity: 116/116 screenshots pixel-equal.

## Where a cached hit's 30 µs went

`bench/breakdown perf`, sidebar at c=16, on round 1's image ([`perf-before/`](oncrack-r2-front/perf-before/)): 26.7 µs per request
unprofiled, and 29.7 µs on the room page.

| Layer (scaled to unprofiled µs per request, room page) | µs |
|---|---|
| Kestrel and ASP.NET Core HTTP (the send is 15% of all samples, under `SysSend`) | 13.4 |
| Runtime with no Campfire frame (thread-pool spin and parking: `ThreadNative_SpinWait` 10.4%, `LowLevelLifoSemaphore::Wait`) | 5.6 |
| Kit adapter, `Ctx`, params, response | 3.6 |
| Cookies, session, HMAC (the `session_token` signature, the Rails session cookie's decryption) | 2.4 |
| Allocation | 1.8 |
| Route table (one regex per request) | 1.1 |
| Controllers, authentication, read cache key and lookup, request log | 1.4 |

By resource: kernel 8.2 µs, managed code 13.4, CLR runtime 5.6, libc 1.6, OpenSSL 0.9. `getrandom` for the request id was 1% (one
system call per request).

After the fast path ([`perf-fast/`](oncrack-r2-front/perf-fast/), sidebar, 22.5 µs):
- The app's own layers fell to about 1 µs: front 0.4, kit 0.5, log 0.2.
- What remained was Kestrel and the kernel (12.2 µs) and the thread pool (9.0 µs, with `ThreadNative_SpinWait` alone at 24% of all
  samples).
- So the thread pool was the next target, and is the scheduling change below.

## What changed

### 1. The fast path (`Campfire.Kit.FastCandidate`, `FastStore` in `Front/Handler.fs`)

**Offer.** A read cache hit (`ReadCache.page`) authenticated by its session cookie offers its answer to the front server. The offer
says two things:
- What the answer depends on: the page's counters (global as the user was read, the user's, the room's or every room's of the user),
  plus the sessions counter's value the session was read under (`SessionReadAt`, new).
- Until when it holds: the session's next activity refresh (`last_active_at` + 1 hour, minus a second), capped by the earliest `exp`
  of the signed and encrypted cookies the request verified. The cap is new: `ExpiryWatch` in `Metadata.fs` notes each envelope's
  `exp`, and `CookieJar.VerifiedUntil` keeps it.

**What the adapter adds.** The body it sent (the frozen page's gzip member, or its plain bytes), and the cookie jar's verdict. Only
plain cookie values are kept. A permanent cookie's expiry is recorded so it can be worked out again. A signed or encrypted cookie
written in the request cancels the offer, as does any expiring cookie that isn't permanent.

**Store.** The front server keeps the response as it went out, header lines and body. It keeps it only when:
- the answer is a 200, sent straight to the connection (not recorded for Thruster's cache, not compressed by the front), and
- exactly the candidate's body was sent.

**Key.** Every byte of the request the app can read: protocol, scheme, local port, the raw target, and every header except three.
- `X-Request-Start`: the front's own.
- `X-Request-Id`: made again for each request.
- `X-Forwarded-For`: no page reads the client's address on a GET; the log line still does.

So a different cookie, Accept, Accept-Encoding, Turbo-Frame, User-Agent, Referer, If-None-Match or Host is a different entry. The key
is built only for targets the app has offered an answer for, and only for a GET with cookies and no body.

**Replay.** A replay runs before the proxy headers, routing, the kit adapter, the cookie jar, authentication and the read cache. It
writes the stored header lines and makes three of them again: `X-Request-Id`, `X-Runtime`, and a permanent cookie's `expires=`
(20 years from now). The room page sets `last_room` on every request that doesn't carry it, so this covers it. Then it writes the
body. The request log line is written as for any request.

**What a replay never does is decide.** Every input to the answer it repeats is the same request bytes and unchanged state:
- A sign-out, ban or deactivation moves the sessions or global counter.
- A post, edit or membership change moves a room or user counter.
- A session due for its hourly refresh stops being replayed a second before, so the refresh, a write, still happens on the first
  request after it falls due.
- `CAMPFIRE_FAST_PATH=off` turns it off, and `CAMPFIRE_FAST_PATH_MB` bounds it (32 MB in two generations).

**Why `spread` tripled.** The store keeps only the bytes that go out (the gzip member: 6-24 KB a page). The read cache, by contrast,
budgets twice the plain body. So the 2,112 pages of `spread` fit in the fast path's 32 MB, while they thrash the read cache's 64 MB.
- The fast path is a second, compact tier. It adds at most 32 MB of retained bodies.
- Peak memory under the realistic workloads did not move beyond noise: 688 MB median at tier 3 (683-826), against 678 MB with the
  fast path off, 716 MB on the pool and 668 MB with `replays` in the same-build tier 2 runs (one each). The classic runs peaked at
  733 MB, with anon 181 MB.
- With the cache's budget raised to 512 MB, R2.0 measured 127k on `spread`, so the gain is the store's density, not new work avoided.

### 2. Replays on the socket's event thread (`CAMPFIRE_INLINE`, `replays` by default)

Kestrel normally hands each connection's requests to the thread pool. At 15-20 µs of real work per replay, the hand-off was a third
of the CPU: workers spinning or parking between requests.
- `CAMPFIRE_INLINE=replays` reads every request on its socket's event thread. It uses Kestrel's `UnsafePreferInlineScheduling` and
  the runtime's inline socket completions; `Program.main` sets `DOTNET_SYSTEM_NET_SOCKETS_INLINE_COMPLETIONS=1` unless given.
- A replay is answered there.
- Anything else is handed to the thread pool (`Task.Yield`) before the app sees it, so a slow request never holds an event thread.
- `all` runs the app on the event thread too. `off` is Kestrel's default.
- This is scheduling only: no durability or correctness effect.

### 3. Request ids without a system call

`SecureRandom.uuid`'s port, `Guid.NewGuid`, made one `getrandom` call per request. Request ids now come from a per-thread 4 KB block
of `RandomNumberGenerator` bytes, the same version-4 bits, one refill per 256 ids. `CAMPFIRE_REQUEST_ID_BLOCK=off` restores
`Guid.NewGuid`.

### Tried, measured, not shipped

| Setting (tier 2, fast path on, [`t2-paths.txt`](oncrack-r2-front/t2-paths.txt)) | room / sidebar c=16 | c=1 | Decision |
|---|---|---|---|
| baseline: thread pool | 153.1k / 168.1k (24.2 / 22.7 µs) | 16.7k / 19.0k (117 / 107 µs) | |
| `DOTNET_ThreadPool_UnfairSemaphoreSpinLimit=0` | 109.1k / 120.3k (17.1 / 14.6 µs, 1.9 cores busy) | 15.9k / 16.6k (41 / 38 µs) | no: workers asleep cost the wake-up; the CPU per request shows what a hit really costs |
| inline socket completions alone | 151.6k / 176.4k | 17.1k / 18.9k | no: Kestrel still hands off to the pool |
| completions + spin 0 | 116.9k / 132.8k | 17.5k / 17.7k | no |
| Kestrel inline + completions (`all`) | 174.5k / 195.6k (17.9 / 15.1 µs) | 25.3k / 26.9k (20 / 18 µs) | as `replays`, but the app runs on event threads (below) |
| `replays` | 174.7k / 196.9k (17.9 / 15.0 µs) | 25.1k / 26.4k (20 / 18 µs) | **shipped** |
| `SO_BUSY_POLL`, other socket options | not run | | busy polling needs a NAPI device; every bench connection is loopback, which has none, and a non-root container can't raise it past `net.core.busy_read` |

**One write per response and preassembled headers** were already in place for a hit before this unit: C3 and C4 brought each
response down to one `sendmsg` (`perf trace -s`, `oncrack-c4.md`). A replay appends its stored header lines in their stored order,
which is the work a preassembled block would save, inside Kestrel's own serialization (1.4% of samples). Replacing Kestrel's
response writer was not attempted: below the event-thread change, Kestrel and the kernel are 12 µs of the remaining 15-18.

**Which scheduling (tier 2, one rep each, same build):**

| | pool | `all` | `replays` | fast path off (pool) |
|---|---|---|---|---|
| posts c=1 / c=16 / c=64 | 4,518 / 12,177 / 18,549 | 4,970 / 9,898 / 21,098 | (tier 3: 4,876 / 10,664 / -) | |
| `mixed` reads / posts | 37,232 / 1,381 | 36,190 / 1,593 | **45,807** / 1,380 | 34,791 / 1,403 |
| `spread` | 86,130 | 90,764 | **94,497** | 32,754 |
| `spread_mixed` reads / posts | **12,793** / 745 | 12,194 / 631 | 11,291 / 671 | 12,910 / 744 |
| `search_spread` | 16,138 | 15,384 | **16,732** | 15,792 |

`replays` wins every workload but `spread_mixed`, where its reads lost 12% and its posts 10% against the pool. Those posts go into
rooms of 526 members, so its reads are mostly misses that hop to the pool. I did not find why the hop costs more there than the
pool's own hand-off (CPU per request rose from 284 to 324 µs). `CAMPFIRE_INLINE=off` gives `spread_mixed` back.

One result had to be explained before the decision. The first fast-path-off control read `search_spread` at 21,010, which looked
like the fast path costing it 23%. That control had left out `spread_mixed`, which runs before `search_spread` in the full set and
adds posts to the rooms searched. Re-run with all four, it read 15,792. The fast path costs `search_spread` nothing.

## Tier 3: the five workloads

`bench/quick`, 3 reps, `campfire-oncrack:app` `sha256:390e390e43fa`, the default seed, `SERVER_CPUS=0-3 LOADGEN_CPUS=4-7`,
warm-up to flat. Rust and the port are round 1's same-session medians (`oncrack-round1-final/`, the same harness and seed); req/s
with CPU µs per request in brackets.

| Workload | c | Rust | F# port | onCrack round 1 | **onCrack R2.3** | **/ Rust** | **/ port** | / round 1 | p99 ms (round 1) |
|---|---|---|---|---|---|---|---|---|---|
| room page | 1 | 6,395 (143.8) | 7,555 (210.5) | 13,428 (144.2) | **26,080 (19.3)** | **4.08x** (CPU 0.13x) | **3.45x** (CPU 0.09x) | 1.94x | 0.05 (0.10) |
| room page | 16 | 28,582 (122.5) | 39,459 (90.3) | 123,942 (30.1) | **174,412 (17.7)** | **6.10x** (CPU 0.14x) | **4.42x** (CPU 0.20x) | 1.41x | 0.21 (0.41) |
| messages page | 1 | 6,684 (140.6) | 8,155 (201.4) | 13,623 (142.3) | **25,963 (18.9)** | **3.88x** (CPU 0.13x) | **3.18x** (CPU 0.09x) | 1.91x | 0.05 (0.10) |
| messages page | 16 | 30,158 (114.2) | 42,404 (83.7) | 123,252 (29.8) | **184,722 (16.4)** | **6.13x** (CPU 0.14x) | **4.36x** (CPU 0.20x) | 1.50x | 0.20 (0.43) |
| sidebar | 1 | 6,134 (149.0) | 7,838 (184.0) | 14,987 (133.7) | **26,723 (18.1)** | **4.36x** (CPU 0.12x) | **3.41x** (CPU 0.10x) | 1.78x | 0.05 (0.10) |
| sidebar | 16 | 28,378 (122.5) | 38,001 (95.0) | 138,182 (26.7) | **197,204 (14.8)** | **6.95x** (CPU 0.12x) | **5.19x** (CPU 0.16x) | 1.43x | 0.18 (0.35) |
| search | 1 | 5,509 (162.2) | 5,734 (328.9) | 15,700 (126.8) | **27,500 (17.5)** | **4.99x** (CPU 0.11x) | **4.80x** (CPU 0.05x) | 1.75x | 0.05 (0.09) |
| search | 16 | 26,396 (124.6) | 33,773 (108.2) | 136,032 (27.3) | **192,332 (15.3)** | **7.29x** (CPU 0.12x) | **5.69x** (CPU 0.14x) | 1.41x | 0.19 (0.37) |
| post a message | 1 | 2,759 (408.7) | 3,034 (636.0) | 3,395 (585.2) | **4,876 (391.6)** | **1.77x** (CPU 0.96x) | **1.61x** (CPU 0.62x) | 1.44x | 0.39 (0.53) |
| post a message | 16 | 7,082 (388.1) | 8,780 (354.8) | 13,215 (230.0) | **10,664 (186.2)** | **1.51x** (CPU 0.48x) | **1.21x** (CPU 0.52x) | 0.81x | 4.60 (5.34) |

Geometric means: c=1 **3.60x Rust, 3.11x the port** (1.75x round 1); c=16 **4.91x Rust, 3.70x the port** (1.28x round 1).
Against the stored phase7-final medians (`tier3/vs-stored.md`): the read pages 4.32-5.65x the port and 6.09-7.23x Rust at c=16.

**Read the c=16 read pages as a cache-hit benchmark, now answered by the replay.**
- The server kept 3.1 of its 4 cores busy (`bench/paths`), and the load generator 2.5 of its 4.
- Neither is saturated: at about 175-200k req/s with 16 connections, each request's round trip on loopback is the limit.
- R2.0 put the load generator's ceiling at 170-210k req/s.
- So these four cells are at or near what the harness can show, and any further gain there will show as CPU per request, not req/s.

**Post c=16.** The three reps read 10,362, 10,664 and 12,293 (R2.2's tier 3: 12,010). The warm-up windows swing between 6k and 16k
in every run, the old and new scheduling alike (`t2-post-*`): the WAL restart's stall, which R2.2 measured and left open. The
replays mode hands a POST from the event thread to the pool, which the pool's own hand-off did before. I could not separate a change
in this cell from the stall in one unit.

## Tier 3: the realistic workloads

`bench/quick --real`, 3 reps, crowd seed, 16 reading connections. Rust and the port are R2.0's same-session baseline
(`oncrack-r2-bench/`).

| Workload | lane | Rust | F# port | onCrack R2.0 | onCrack R2.2 | **onCrack R2.3** | **/ Rust** | **/ port** |
|---|---|---|---|---|---|---|---|---|
| mixed | reads | 18,597 | 24,232 | 43,283 | 34,805 | **45,187** | **2.43x** | **1.86x** |
| mixed | posts | 688 | 753 | 1,079 | 1,424 | **1,355** | **1.97x** | **1.80x** |
| spread | reads | 25,655 | 29,902 | 28,547 | - | **93,619** | **3.65x** | **3.13x** |
| spread_mixed | reads | 13,155 | 13,584 | 13,229 | 13,129 | **11,322** | **0.86x** | **0.83x** |
| spread_mixed | posts | 319 | 393 | 337 | 753 | **674** | **2.11x** | **1.71x** |
| search_spread | reads | 8,468 | 18,942 | 17,802 | - | **16,408** | **1.94x** | **0.87x** |

R2.2's tier 3 did not run `spread` or `search_spread`. `search_spread` is below the port with the fast path on or off (15,792 off,
same build). That is the state R2.2 left after `spread_mixed`'s posts, not this unit's doing.

## Checks

- **Statuses:** every response 2xx, 0 connection errors, in all 30 classic and 12 realistic tier 3 runs and every tier 2 run.
- **Rows:** post rows written equal the 2xx answers in every phase.
- **Bytes:** decoded bytes equal Rust's on every probed route (`bench/lib/probe.py`, gzip and identity). The replays' bytes are
  checked against the app's own answer by the attack tests.
- **Attack tests**, `tests/Campfire.App.Tests/FastPathTests.fs`, 9 tests, every app behind the front server
  (`Support.startFronted`):
  - A replay equals the app's answer (status, headers but the four that differ by design, body).
  - Request ids are fresh v4 UUIDs, and a client's id is echoed.
  - The gzip member, Turbo-Frame, If-None-Match, HEAD and GET-with-body each get their own answer or none.
  - A post, edit and delete show at once.
  - Two users never share a replay.
  - Sign-out stops the replay of the old cookie byte for byte.
  - A ban and a removed membership stop it.
  - The permanent `last_room` cookie is dated per replay.
  - A session due for its refresh is refreshed, not replayed.
  - Six readers racing a poster never get a replay missing the last acknowledged post.
- **Mutations:** each guard has a mutation that a test catches:
  - Ignoring the counters fails 5 tests.
  - Dropping the sessions counter fails the sign-out test.
  - Dropping the time bound fails the refresh test.
- **The whole App suite behind the front server** (`CAMPFIRE_TEST_FRONT=1`): 234 of 236 passed. The two that didn't:
  - The read cache tests' "served from the cache" checks first failed because a replay never asks the read cache. They now count
    replays.
  - The avatar removal test fails behind the front server with the fast path off too. Thruster's public response cache, which the
    front server copies, keeps the old avatar until it expires, as Thruster does in front of Rails. That predates this unit.
- **`bin/verify`:** 1,111 tests, 1,102 passed, 7 skipped, 2 failed.
  - Both failures were Cable timing tests that hit their timeouts while the pixel-parity capture loaded the machine.
  - Re-run alone, `Campfire.Cable.Tests` passed 80 of 81, 1 skipped.
- **Pixel parity:** `bin/pixel-parity --seeds default --only 'realtime/**,interactions/sidebar/**'`, the states that revisit pages
  after a change, on the image measured above: **116/116 screenshots pixel-equal**, 0 flaky, 0 errors, in 1,221 s
  ([`pixel-parity.json`](oncrack-r2-front/pixel-parity.json)).
- **Not run:**
  - The full lean matrix on every seed (the round verifier's job).
  - `bin/kit-differential http`: the replay is not in the kit's test app, and the adapter's answers are unchanged apart from the
    request id's source.
  - The Cable suite.
  - The AOT image.

## Deferred

1. `spread_mixed` under `replays`: reads -12% and posts -10% against the pool. A request that isn't a replay costs about 40 µs more
   there. The next step is a profile of that workload with each mode.
2. The c=16 post stall (R2.2's first deferred item), which still hides any change in that cell.
3. A replay for read cache **misses** that render the same bytes. Today only a hit offers, so the first two requests after a change
   go through the app.
4. Below Kestrel. What a replay still pays is Kestrel's parse and response writer and the kernel's loopback send: 12 µs of the
   remaining 15-18. Going below it means a connection-level server, or Kestrel's raw transport, for the plain HTTP listener.
5. `SO_BUSY_POLL` on a real NIC (no loopback NAPI here).

## Reproducing

All inside colima; `bin/clean-docker` after the rebuild.

```sh
bench/breakdown perf --apps oncrack --routes room_show,sidebar --conc 16 --out bench/results/oncrack-r2-front/perf-before   # round 1's image
bin/publish-mounted /var/tmp/campfire-mounted
bench/paths --mounted /var/tmp/campfire-mounted --env "CAMPFIRE_INLINE=replays" --conc '16 1' /rooms/@ROOM@ /users/me/sidebar
ONCRACK_EXTRA_ENV='CAMPFIRE_INLINE=off' bench/quick --real --mounted /var/tmp/campfire-mounted --reps 1 --out DIR
CAMPFIRE_REVISION=$(git rev-parse HEAD) parity/bin/candidate build
bench/quick --only oncrack:N --part K/2 --out bench/results/oncrack-r2-front/tier3       # N = 1..3, K = 1..2
bench/quick --real --only oncrack:N --out bench/results/oncrack-r2-front/tier3-real
python3 bench/results/oncrack-r2-front/review/table.py
CAMPFIRE_TEST_FRONT=1 dotnet test --project tests/Campfire.App.Tests -c Release   # the whole App suite behind the front server
```
