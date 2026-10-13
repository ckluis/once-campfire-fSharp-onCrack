# onCrack R4.2: gather writes for Cable fan-out, 2026-10-10

Plan: [`plans/r4-fanout.md`](../../plans/r4-fanout.md). Baseline: [`oncrack-r4-fanout-baseline.md`](oncrack-r4-fanout-baseline.md). Raw data and scripts:
[`oncrack-r4-fanout/`](oncrack-r4-fanout/).

**Result.** Lever 1 (gather writes) is built, tested and kept, on by default (`CAMPFIRE_CABLE_GATHER=off` copies). It removes the 15.9% of the
server's CPU that was `Memmove` into the pooled send buffer and replaces the `sendto` by one `sendmsg` over the frames' own arrays. The measured
gain is smaller and noisier than the plan's -12 to -15%: -9% to -30% CPU per delivery at 1,000 clients in three alternating tier 2 pairs, +13% msgs/s
and -12% CPU at 2,000 clients in a same-session A/B on the rebuilt image, and no difference at 100, 500 and 1,000 clients in that A/B. The host was
busy with other sessions the whole time (load 3 to 5 against 1.5 in the baseline), so every absolute number is 20-100% worse than the baseline's, and
only same-session pairs are read. Tier 3 (Rust f9dca47, the F# port, onCrack, 3 reps): onCrack delivers **1.84x, 1.35x, 1.17x, 1.14x** Rust's messages a
second at 100, 500, 1,000 and 2,000 clients, with 0.53x, 0.67x, 0.83x, 0.85x of Rust's server CPU per delivery. Lever 2 is half done and lever 3 is not
started (see Deferred).

## What was built

- `Socket.fs`: `Writer.Send` on a detached connection on Linux (`Sendmsg.available`) fills a thread-static `GatherScratch` (each frame's header, header
  length and payload array), then makes one non-blocking `sendmsg(MSG_DONTWAIT | MSG_NOSIGNAL)` over header and payload pairs. Each payload is
  pinned by a `fixed` local in a recursion one level per frame; no GC handle, no copy. A partial send or `EAGAIN` copies the unsent rest (walking
  headers and payloads from the byte `sent` ends in) into a pooled buffer and goes through the existing `FinishSend`, with its 30 s timeout and abort. Any
  other errno raises `IOException`, and the connection ends as a failed `SendAsync` ends it. Batches over 256 frames copy (the cap is 64).
- `Config.GatherWrites` (`CAMPFIRE_CABLE_GATHER`, read in `Boot.fs` and in `bench/cable/fsharp/Program.fs`). `Writer`'s sixth constructor argument.
- Other platforms (macOS) always copy: the code path is `Sendmsg.available = Linux && (arm64 || x64)`. The two Linux-only tests skip elsewhere.

## Discarded: .NET's own gather send

First version: `Socket.Send(IList<ArraySegment<byte>>, flags, out error)` with `Blocking <- false` at `Detach` (the plan's way). Tier 2 alternating pairs
(`pairs/a1-off`, `b1..b6`, 1,000 clients, off/on): CPU per delivery 2.12 / 2.12 us on / off in two pairs (2.12, 2.14 against 2.12, 2.20 at 2,000), msgs/s
3.5% lower. Profile (`perf`, same run shape): `HndCreateHandle`, `TableFreeSingleHandleToCache`, `TableAllocSingleHandleFromCache` and
`GCHandleStore::CreateHandleOfType` together about 8-9% of the samples, because .NET pins every segment with a GC handle on every call: as much as the
memmove it replaced. The plan's contingency (P/Invoke `sendmsg`) is the version that was kept. That version also made `ProtocolTests` "unknown channels
and malformed commands get no reply" time out in about one full-suite run in three on macOS with the switch on and never with it off (6 of 16 against 0 of 16,
interleaved): a frame the server had sent (its own log said `Success`, 92 of 92 bytes) was read by the test client late or not at all. I did not find the
mechanism (a test client race that only this timing exposes is possible: it reads with an abandoned-read hand-off). Removing the managed path removes
the symptom on the platform that matters (Linux, where `bin/linux-tests Cable` passed 84 tests), and macOS now always copies. Recorded as an open question, not a
conclusion.

## Tests (the plan's two)

In `tests/Campfire.Cable.Tests/SocketTests.fs`:
1. `gathered writes put the copied writes' bytes on the wire` and `... through partial sends`: random batches (1-80 frames, payloads of 1, 125, 126, 127, 65,535,
   65,536 and 70,000 bytes, half compressible, deflate on and off) go out through a detached gathering `Writer` on a loopback pair and through a copy-path
   `Writer` into a `MemoryStream`; the bytes must be equal. The partial version sets the server's `SendBufferSize` and the client's `ReceiveBufferSize` to 4 KB and reads
   small chunks with sleeps, and asserts that `PartialGathers()` rose (that the partial path ran).
2. `a gathered write to a peer that never reads returns at once and times out`: an 8 MB `Send` to a peer that never reads returns a pending `ValueTask` in under
   100 ms, then raises `TimeoutException` and calls `abort` at the (short) write timeout.

Mutation: dropping the offset into the partially sent segment in the remainder copy is caught by both byte tests on Linux (`bin/linux-tests Cable --filter-method
"*gather*"`: 2 failed, 1 passed). Not run: the second mutation in the plan (reusing the scratch header buffer before the remainder is copied; in the final code the remainder is copied
in the same call, before `Send` returns).

Runs: `bin/linux-tests Cable`: 83 passed, 1 skipped (the reference recorder). macOS `bin/verify Cable`: 81 passed, 3 skipped (the gather ones that need Linux, and the recorder).
`bin/verify` (everything, macOS): 1,139 of 1,150 passed with 10 skipped and **1 failed**, `Campfire.Db.Tests.DatabaseTests.the wal stays bounded under sustained writes`
("the WAL never restarted"), a timing test of a project this change does not touch; it passed 3 of 3 alone straight afterwards. `DirectTests` and `FanOutTests`
are in the Cable run. `CAMPFIRE_TEST_GATHER=off` (a switch added to `Support.testConfig`) runs the suite with copying writes on macOS.

`bin/pixel-parity --fast --only 'realtime/**'` on the image built from the commit: **PASSED, 26 of 26 screenshots pixel-equal** (the default seed; the other four seeds
have no realtime screens), 419 s. The plan's "104 cells" is the full matrix; `--fast` is Chromium, light, no breakpoint sweep. The full matrix and the interactions slice
were not run.

## Tier 2: the switch, alternating (same build, `pair.sh`, 1,000 and 2,000 clients, raw client, window 128)

Native `sendmsg` build, `c1..c6` (on, off, on, off, on, off). Host load before the run 1.3-1.5, after 2.4-3.8.

| pair | 1,000 clients on / off: CPU us per delivery | msgs/s | 2,000 clients on / off: CPU us | msgs/s |
|---|---|---|---|---|
| 1 | 3.37 / 3.71 | 1,153 / 1,030 | 2.81 / 2.80 | 688 / 693 |
| 2 | 3.02 / 4.31 | 1,266 / 891 | 2.47 / 4.22 | 773 / 452 |
| 3 | 3.72 / 4.14 | 1,028 / 933 | 2.72 / 2.94 | 705 / 651 |

On is better at 1,000 clients in all three pairs (-9%, -30%, -10% CPU; +12%, +42%, +10% msgs/s), level to better at 2,000. Pair 2 is host drift as much as the
switch. The managed first version's pairs (`b1..b6`) are in `pairs/`, as above.

## Same-session A/B on the rebuilt image (`ab-image.sh`: off, on, on, off, off, on; 100/500/1,000/2,000 clients; medians of 3)

Host load before 1.3-1.5, after 3.6-4.2. CPU per delivery is 2-3 times the baseline's here; the host was at its worst.

| clients | CPU us per delivery off / on | msgs/s off / on |
|---|---|---|
| 100 | 8.98 / 8.73 | 3,561 / 3,643 |
| 500 | 5.03 / 5.12 | 1,503 / 1,433 |
| 1,000 | 4.28 / 4.39 | 898 / 858 |
| 2,000 | 4.56 / **4.02** | 422 / **478** |

So the gain is not reproducible at 100-1,000 clients in this host state (within the pair spread, which was about 20%), and at 2,000 clients it is -12% CPU and
+13% msgs/s with every one of the three on-runs better than every off-run. Nothing was worse in a way that held in both sets, so it stays on. Paced p50/p99
(posts one at a time) did not move (`table.py` prints them).

## Profile after (`perf-gather-on/`, 1,000 clients, 8 s saturated, `KEEP_SCRIPT=1`; shares of samples, perf costs a few percent)

| | before (plan) | after |
|---|---|---|
| `Memmove` into the pooled send buffer | 15.9% | **0.0%** |
| the send syscall's whole subtree | 60.5% | 75.3% (now counts the `sendmsg` frames, which the old figure kept in two rows) |
| `copy_from_user` (per byte) | 18.4% | 24.5% |
| `Writer.Send` | 77.6% | 74.1% |
| GC | 1.5% | 1.7% |

Shares of a total that changed (posting is 17.5% db, 10.8% controller, 8.5% views here); read the memmove row, not the others. The kernel's per-byte copy is unchanged,
as the plan said (point 4). The syscall census over 3 s: 301,037 `sendmsg`, 0 `sendto`, 376 `write`, 23,373 `futex`, 2,606 `epoll_pwait` (`syscalls-oncrack-1000.csv`):
the change does what it says. `breakdown.py` here matches `__syscall_cancel` as the send because `Sendmsg` is inlined into `SendGather`.

## Memory (`SMAPS=1 bench/mem cable:1000 idle:5`, mounted build, off / on, twice each)

| | Pss after cable:1000 | anon | LOH gen at end (MB) | GC pause total (ms) |
|---|---|---|---|---|
| off | 293, 290 | 198, 195 | 9, 9 | 316, 323 |
| on | 290, 286 | 202, 198 | 2, 1 | 289, 290 |

Pss -1% (3-4 MB): the large pooled send buffers are gone from the LOH (9 MB to 1-2 MB) and the managed heap is otherwise the same size. It is not the lever for the memory gap
(Rust's saturated Pss at 1,000 clients is 114 MB; onCrack's is 296 MB).

## Tier 3, one session (`session.sh`, image `campfire-oncrack:app` built from commit `2352dfa`, Rust = upstream f9dca47, 3 reps, `t3/`, `sends/`; table: [`session-table.md`](oncrack-r4-fanout/session-table.md))

Every cable phase of the session (16 per app): all clients subscribed, every posted message reached every client, 0 failed connects, 0 closed mid-run, 0 window stalls.
Server cores 3.1-3.9 of 4 for all apps; the load generator 1.1-2.6 of 4. **The host was loaded** (load 3-4.8 at the start of each part, other sessions' work), so absolute
numbers are below the baseline's (Rust at 100 clients 2,302 against 2,628, onCrack 4,244 against 6,160). The run order was Rust, port, onCrack in each rep (my loop did not
reverse rep 2; `bench/run`'s alternation only applies inside one invocation), so onCrack always ran last in a rep, on a host that was drifting. This is a weakness of the comparison
and the same-session A/B above is the cleaner evidence for the change itself.

Delivered messages per second (median of 3, range):

| clients | Rust f9dca47 | F# port | onCrack | onCrack / Rust | baseline (R4.1) onCrack / Rust |
|---|---|---|---|---|---|
| 100 | 2,302 [2,134-2,314] | 1,747 | **4,244** [4,217-6,799] | **1.84x** | 2.34x |
| 500 | 1,512 [1,418-1,681] | 868 | **2,038** [1,625-2,219] | **1.35x** | 1.62x |
| 1,000 | 1,040 [952-1,154] | 363 | **1,214** [948-1,298] | **1.17x** | 1.23x |
| 2,000 | 546 [499-566] | 163 | **623** [457-700] | **1.14x** | 1.06x |

Server CPU per delivery (us), onCrack / Rust: 100: 7.43 / 13.94 (0.53x); 500: 3.32 / 4.99 (0.67x); 1,000: 3.14 / 3.77 (0.83x); 2,000: 3.04 / 3.59 (0.85x). The baseline's
1,000 and 2,000 points were 2.55 / 3.17 (0.80x) and 2.64 / 2.86 (0.92x). Against the baseline, the lead over Rust fell at 100-1,000 clients and rose at 2,000; with onCrack
always last in the order and a host drifting upward, I do not read that as an effect of the change, and I do not claim the plan's goal ("beat Rust clearly at 1,000 and 2,000
clients on msgs/s and CPU per delivery") as met: it is ahead on both, by 14-17% on msgs/s, with onCrack's range overlapping Rust's at 1,000 and 2,000. Sends per delivery
(onCrack, Rust): 100: 0.202, 0.603; 500: 0.114, 0.110; 1,000: 0.080, 0.043; 2,000: 0.062, 0.043 (a perf-stat pass of its own; the baseline had 0.065 and 0.031 at 1,000 clients).
Pss saturated: 296 MB at 1,000 and 350 at 2,000 for onCrack, against Rust's 114 and 132 (unchanged).

## Deferred

- **Lever 3** (batch-size knobs: `CAMPFIRE_CABLE_HOLD_US` 1000 against 3000, `MaxWriteBatch` 64 against 128): not started. The unit ran well past 2 hours on the flake above, and the host was
  too noisy for a 0 to +5% effect to show in pairs.
- **Lever 2** (memory attribution): only the JIT image at `cable:1000`, off and on, was run (above). Not run: `cable:2000`, the AOT image, `CAMPFIRE_MEM_LOG_MS=500` phases.
- **A tier 3 with the apps' order reversed in rep 2** (and a fourth rep), on a quiet host; the same-session A/B should be repeated there at 100-1,000 clients to see whether the 2,000-client gain
  shows lower down.
- **Why the macOS managed-gather path made `ProtocolTests` time out** (above): an open question; a test client read race is the leading suspect.
- **The page**: `site/build.py` now sources the fan-out picture and tables from `t3/` (Rust f9dca47, the port and onCrack; Rails dropped: it was not run, and round 1's Cable numbers came from
  another client), with a 2,000-client tab. The build and its sourcing check pass; the new tab's layout was not looked at in a browser.
- From the plan: smaller frames (R4.3), the post path beside the fan-out, a profile at 2,000 clients, the 100-client paced p99 of 14-26 ms.
