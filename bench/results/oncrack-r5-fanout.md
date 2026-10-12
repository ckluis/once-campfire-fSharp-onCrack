# onCrack round 5, unit R5.3: Cable fan-out at 2,000 clients, 2026-10-12

Plan: `plans/r4-fanout.md` (levers 2 and 3 were deferred there). Build measured: `db83b63` plus this unit's bench-only switches (the app's behaviour is unchanged with
the switches off), published with `bin/publish-mounted` over `campfire-oncrack:app`. Data and scripts: `bench/results/oncrack-r5-fanout/` (this file calls it `data/`).
Raw client, window 128, `SERVER_CPUS=0-3 LOADGEN_CPUS=4-7`, the cable suite's phases; "msgs/s" is each message delivered to every client, "CPU/del" the server's
CPU per delivery from the cgroup over the saturated phase.

## Verdict

1. **R4.5 did not cost the fan-out lead.** Alternating the publish order inside one running process (the new `CAMPFIRE_CABLE_FLIP_FILE`), the default order (publish
   order across streams, the shared log) is as fast as the old stream-at-a-time order or faster at 1,000 clients (median 1,691 against 1,569 msgs/s) and at 2,000
   (972 against 858; ahead in 5 of 6 pairs). The rounds-1-to-4 ring is level or ahead of the log in the 3 undisturbed in-process pairs at 1,000 clients (0 to 23%) and behind
   it at 2,000. Across container restarts, the first three rounds put the default 8-18% behind on CPU per delivery (3 of 3) and the next three did not repeat it (default first or equal in 2
   of 3, the third starved by the host). Round 4's final 0.94x at 2,000 clients was that session, not the code (section 4 has a same-session Rust control).
2. **Nothing in the profile at 2,000 clients is left for the application to win.** 75.8% of the server's CPU is the `sendmsg` syscall (kernel TCP: copy per byte, the
   loopback receive softirq per skb, page and memcg charge, per-send bookkeeping); the whole cable layer in user space is under 8%. Detail in section 2.
3. **Lever 3 (batch size, hold) kept nothing.** `MaxWriteBatch` 128 is no different from 64. `CAMPFIRE_CABLE_HOLD_US` 3000 beat 1000 by 12-21% at 2,000 clients in 5 of 6
   clean pairs (4% behind in the sixth), did nothing at 1,000, and cost 6-40% at 100 clients in 3 of 3 pairs, so the default stays 1000. 6000 is no better than 1000 at 2,000.
4. **Lever 2 (memory) is attributed, not changed.** After 2,000 clients on a fresh container, Pss is 316-331 MB: about 89 MB runtime mappings (what Rust does not have),
   24.6 MB anon outside the managed heap and 217.6 MB managed heap, of which 112 MB is live (96 MB in gen2, about 48 KB per connection) and the rest committed and free.
5. **The host was never quiet.** The Mac's 1-minute load average sat at 4-40 (median 11-14) through every session here, from other sessions' test lanes and builds.
   Runs starved to 60-90 msgs/s happen on it. That is why this unit alternates inside one process and carries the host probe on every run.

## 1. Was R4.5 the cost of the lead?

Three ways, from weakest to strongest. The rule of the plan: keep a change only if it wins beyond the spread with CPU per delivery agreeing.

### 1a. Restarting the app per arm (`scripts/arms.sh`, `data/ab12-table.txt`)

`bench/run` cable suite (1,000 then 2,000 clients) in a fresh container per arm, arms rotated each round, VM load before and after in each directory. `default` is the
shipped behaviour, `ring` is `CAMPFIRE_CABLE_LOG=ring` (rounds 1-4's ring; it also turns the publish order off), `stream` is `CAMPFIRE_CABLE_ORDER=stream` (the log,
one stream at a time). `ab1` is rounds 1-3 (default, ring, stream rotating); `ab2` is rounds 1-3 again with the list reversed.

1,000 clients, msgs/s (CPU/del us) per round, ab1 r1-r3 then ab2 r1-r3:

| arm | r1 | r2 | r3 | r4 | r5 | r6 (starved) | median of 6 | median of 5 |
|---|---|---|---|---|---|---|---|---|
| default | 1,290 (2.90) | 1,466 (2.58) | 1,230 (2.95) | 1,716 (2.21) | 1,819 (2.09) | 679 (5.28) | 1,378 (2.74) | 1,466 (2.58) |
| ring | 1,461 (2.58) | 1,566 (2.42) | 1,490 (2.49) | 1,646 (2.32) | 1,726 (2.19) | 1,593 (2.36) | 1,580 (2.39) | 1,566 (2.42) |
| stream | 1,414 (2.68) | 1,608 (2.36) | 1,485 (2.52) | 1,411 (2.58) | 1,840 (2.07) | 294 (11.83) | 1,449 (2.55) | 1,485 (2.52) |

At 2,000 clients the medians of 6 are default 829 (2.28), ring 840 (2.25), stream 778 (2.38), with rounds from 474 to 981. Every cell is valid (`posted == complete`, 0
closed, 0 window stalls). Reading: the first three rounds put the default last on all three; the second three put it first or level on two and starved it on the
third. That is a result of the host, and the rounds say nothing beyond a spread of about plus or minus 10% at 1,000 clients and 20% at 2,000.

### 1b. Alternating inside one process (`bench/cable/flip`, `data/flipA1000-table.txt`, `data/flipA2000-table.txt`)

New and bench-only: `CAMPFIRE_CABLE_FLIP_FILE` (`src/Campfire.Cable/BenchFlip.fs`). A connection reads the file when it starts; `bench/cable/flip` writes the arm's
settings (`order=stream`, `log=ring`, `batch=N`, `hold=US`) before each load generator run, so the arms alternate seconds apart in one warm process. `log=ring` applies
to the groups made from then on. The tool rotates the arm order each rep and records the host probe (`bench/lib/hostprobe.py`, 1.0 is the quietest ever seen)
before and after each run; a rep with a run under 60% of its best or a probe over 1.3 is marked disturbed. Unset (the default, and in tests) the switch reads nothing.

1,000 clients, 6 reps, msgs/s (CPU/del us, host probe before/after):

| rep | default (publish order, log) | stream order, log | ring (rounds 1-4) |
|---|---|---|---|
| 1 | 1,686 (2.19) h1.23/1.08 | 1,683 (2.24) h1.09/1.10 | 1,948 (1.94) h1.09/1.05 |
| 2 | 1,695 (2.21) | 1,572 (2.41) | 1,693 (2.24) |
| 3 | 1,598 (2.33) | 1,566 (2.38) h1.71/1.07 | 1,959 (1.94) |
| 4 | 1,754 (2.16) | 1,433 (2.60) | 546 (6.29) |
| 5 | 518 (6.73) h1.07/1.94 | 1,611 (2.28) | 1,307 (2.79) h1.14/2.07 |
| 6 | 1,734 (2.16) | 1,351 (2.68) h1.11/1.23 | 1,172 (3.12) h1.13/1.54 |
| median | 1,691 [518-1,754] (2.20) | 1,569 [1,351-1,683] (2.40) | 1,500 [546-1,959] (2.52) |

Stream / default, msgs/s per rep: 1.00 0.93 0.98 0.82 3.11 0.78 (the 3.11 is the default's starved run); CPU/del 1.02 1.09 1.02 1.20 0.34 1.24. The default is as fast as or faster than
the stream order in all five reps in which it was not starved. Ring / default: 1.15 1.00 1.23 in the three undisturbed reps (CPU/del 0.89 1.01 0.83), then
disturbed (0.31 2.53 0.68). An earlier unprobed session of default against stream only (`data/flip1.log`, 6 reps, same build) read 1,553 against 1,564 msgs/s, median per-rep ratio 0.993.

2,000 clients, 6 reps:

| rep | default | stream order | ring |
|---|---|---|---|
| 1 | 1,017 (1.90) | 979 (1.89) | 694 (2.46) h1.14/1.43 |
| 2 | 990 (1.86) | 923 (2.09) | 864 (1.98) |
| 3 | 895 (2.13) h1.07/1.95 | 812 (2.35) h1.08/2.31 | 780 (2.35) |
| 4 | 962 (1.93) | 771 (2.40) | 245 (7.39) h1.09/2.19 |
| 5 | 983 (1.91) | 903 (2.07) h1.08/2.19 | 922 (2.03) |
| 6 | 778 (2.39) h1.15/1.92 | 807 (2.35) | 926 (2.07) |
| median | 972 [778-1,017] (1.92) | 858 [771-979] (2.22) | 822 [245-926] (2.21) |

Default over stream: 1.04 1.08 1.10 1.25 1.09 0.96 (5 of 6 ahead, CPU/del 0.99 1.12 1.10 1.24 1.08 0.98 the other way round). Default over ring is ahead in 5 of 6 as well.

**Reading.** The publish-order merge (R4.5) costs nothing measurable in steady state. Why the stream order is the slower one at 2,000 is not explained here; the
loadgen-side parse of grouped against interleaved frames is a candidate, and this unit did not chase it. The shared log against the ring is not resolved to better than
plus or minus 10% at 1,000 clients (ring ahead in 5 of 8 undisturbed pairs from 1a and 1b, level in 1, behind in 2; msgs/s ratios 1.13 1.07 1.21 0.96 0.95 and 1.15 1.00 1.23, median 1.10; the pairs share the host) and
shows no cost at 2,000. The log is what keeps every subscriber, so no setting here would trade it away; the profile below finds no code in it worth the cost.

### 1c. The host

`data/host-load-*.txt` samples the Mac every 10 s: ab1 1-minute load average 8-23 (median 13.6), ab2 4-28 (10.6), the in-process sessions 5-41 (12.7-13.6), with other
sessions' Elixir/Go test lanes, Python and builds taking a median of 190-365% CPU outside the VM and up to 980%. `data/chain-storm/` kept the first in-process session, which hit a load-40 stretch:
runs of 66, 89 and 158 msgs/s with 20-47 us CPU/del in the same process as runs of 1,430-1,530. Nothing in 1b was read without its probe after that.

## 2. The profile at 2,000 clients (`data/perf1/`, `scripts/perfdiff.py`)

`bench/cable/perf` (perf in the VM, `KEEP_SCRIPT=1`, 8 s of the saturated phase at 999 Hz, `breakdown.py` of R4.2), default settings: 968 msgs/s under perf.

| where | share of the app's samples at 2,000 clients | at 1,000 clients (same session) | R4.2 at 1,000 |
|---|---|---|---|
| cable connection loop (`Connection.run`) | 82.1% | 71.8% | 77.6% (`Writer.Send`) |
| `sendmsg` syscall | 75.8% | 67.1% | 60.5% |
| - `copy_from_user`, per byte | 23.4% | 18.0% | 18.4% |
| - loopback receive softirq, charged to the sender, per skb | 19.2% | 18.0% | 16.8% |
| - page and skb allocation, memcg charge | 13.5% | 11.4% | 10.7% |
| - the rest of the syscall (entry, `lock_sock`, bookkeeping), per send | 11.4% | 12.1% | 6.6% |
| - transmit path, per skb | 8.3% | 7.6% | 8.0% |
| publishing (`Group.Publish`, `WakeBatch`, `BroadcastOrder`) | 3.5% | 3.4% | 2.4% |
| reading the log (`Merge.Drain`, `TryPeek`, self time) | 3.0% | 3.1% | 1.6% (`drain`) |
| GC | 1.3% | 1.8% | 1.5% |
| everything outside the connection loop (the posts) | 17.9% | 28.2% | 19.3% |

- **Sends per delivery fall from 0.116 at 1,000 clients to 0.084 at 2,000** (`perf stat`, sendmsg per 3 s over deliveries): a send carries about 12 messages. The per-send
  share of the kernel work is 11-12% of the samples at both counts here (R4.2's profile read 6.6% with its own version of the breakdown script), so a send that
  carries more messages is the one thing that cuts it; that is what the hold knob of section 3 tries.
- **What the publish-order merge costs in user space, from the profile:** `Merge.Drain` plus `LogGroup.TryPeek` read 0.08 us of the 2.55 us per delivery at 1,000
  clients, against 0.057 us for `drain` plus `TryRead` in the stream order (`scripts/perfdiff.py default-1000 stream-1000`): about 0.03 us, 1%. The other
  difference between those two runs (1,504 against 1,758 msgs/s in single runs) is spread over the kernel's send path in proportion and is the host.
- **Wire:** one run in the stream arm measured 10,652 octets and 0.311 TCP segments per delivery (`netab1.txt`, `scripts/netab.sh`); its two default-arm twins were starved
  by the host (619 and 769 msgs/s) and are not quoted.
- **The user-space cable code is not the lever.** `Connection.run` outside `Writer.Send` is 5.9% at 2,000 clients; a faster merge (a fused peek-and-read, or only the streams
  with something ready) could save a fraction of 2 points of CPU, below what 12 pairs can see, so none was built. What is left is bytes per frame (30% of the kernel work is per byte,
  25% per skb; R4.2's deferred list: whitespace, `\"` escapes, the inline SVG), which carries pixel risk and needs its own unit.

## 3. Lever 3: batch size and hold (`data/tail/flipB2000*`, `data/final/flipH*`)

In-process alternation as 1b (`batch=N` and `hold=US` are read from the flip file; hold at most every 20 ms in `BroadcastOrder`). `b64` is the shipped batch cap, `h1000` the
shipped hold. The rule: both msgs/s and CPU per delivery better in every pair, and paced latency at 100 clients not worse.

| setting | clients | reps | msgs/s per pair against the shipped setting | CPU/del per pair | verdict |
|---|---|---|---|---|---|
| `batch=128` | 2,000 | 3 | 1.67 (disturbed) 0.92 1.11 | 0.63 1.00 0.89 | no difference; the cap rarely binds (a write averages about 24 frames) |
| `hold=3000` | 2,000 | 3 + 4 | 1.68 (disturbed) 1.12 1.13; 0.96 1.19 1.14 1.21 | 0.61 0.87 0.85; 1.05 0.85 0.88 0.88 | +12-21% in 5 of 6 clean pairs, -4% in one |
| `hold=3000` | 1,000 | 3 | 0.95 0.97 1.08 | 1.04 1.03 0.83 | none |
| `hold=3000` | 100 | 3 | 0.94 0.48 0.62 | 1.04 1.30 1.46 | worse in 3 of 3 (5,395 / 3,032 / 3,867 against 5,747 / 6,369 / 6,223) |
| `hold=6000` | 2,000 | 4 | 0.94 1.16 0.96 1.00 | 1.09 0.85 1.10 1.01 | none |
| `hold=6000` | 1,000 | 3 | 1.04 1.11 1.32 | 0.97 0.88 0.76 | +11%, 3 of 3 |

**Nothing kept.** The hold that helps at 2,000 clients hurts at 100 (the saturated phase there posts 6,000 a second and a longer hold stalls the 128-message window), and the
one that helps at 1,000 does nothing at 2,000. No single value wins at every client count, which is what the default has to do. The 2,000-client effect of `hold=3000`
is the best lead of the unit (seven pairs, one disturbed, five clean wins) and needs a session of its own with a count-dependent rule (a hold scaled by the room's
subscribers) before it can be shipped.

## 4. Lever 2: memory attribution (`data/tail/mem-cable2000.txt`)

`SMAPS=1 bench/mem idle:3 cable:2000 idle:5` with `CAMPFIRE_MEM_LOG_MS=1000`, a fresh container (no 100-client posting phase before it), JIT image mounted.

| phase | Pss | anon | managed heap (GC view, committed / heap / fragmentation MB) | gen0 / gen1 / gen2 / LOH MB | GCs gen0 / 1 / 2 |
|---|---|---|---|---|---|
| idle:3 (boot) | 87 | 16 | - | 0/0/0/0 | 0/0/0 |
| cable:2000 (end of the phase) | 316 (peak 330) | 227 (peak 242) | 194 / 137 / 20 | 7 / 36 / 89 / 3 | 34 / 10 / 4 |
| idle:5 after | 331 | 242 | 206 / 112 / 5 | 4 / 6 / 96 / 3 | 35 / 11 / 4 |

At the end: managed heap 217.6 MB anon, anon elsewhere (glibc, SQLite, libvips, stacks, runtime) 24.6 MB, file-backed mappings about 89 MB of Pss (the
`doublemapper` JIT memfd 23 MB, CoreLib 14 MB, libcoreclr 5.4 MB, libcrypto 4.5 MB, libclrjit 3.5 MB, FSharp.Core 3.3 MB). Reading:

- **About 89 MB is the runtime** and is what the Native AOT image removes (R2.5: idle 53 MB against 85); Rust has none of it.
- **The heap holds 112 MB live after the load, 96 MB of it in gen2**, with 2,000 idle connections; 16 MB at boot. That is about 48 KB a connection, more than R4.2's
  20 KB a connection from 1,000 to 2,000 (which was Pss in the suite's container, after earlier phases had raised the high-water mark). A split by type needs a heap
  dump (`dotnet-gcdump` is not in the VM's tools; `dotnet-counters`, `-trace` and `-symbol` are). The candidates, from R4.2: the connection loop's async state machine, the
  `Channel<Received>` and its reader, six `Subscription`s each carrying its identifier twice, the retained `HttpContext`, the `Merge` head array.
- **About 94 MB of the heap is committed and free** (committed 206 against live 112); gen0/gen1 budgets and the high-water mark of the posts decide that, and R2.5 found no GC
  setting that moved it without costing a write phase.

No change was made. Next step: a gcdump of the container after `cable:2000`, and a `cable:1000` run in a fresh container to see whether the 48 KB is per connection or fixed.

## 5. Against Rust f9dca47 in the same session

`scripts/control.sh` (data: `final/control/`): `bench/run` cable suite, raw client, window 128, 15 s saturated, a fresh container per app and round, Rust upstream
`f9dca47` (`campfire-rust-upstream:f9dca47`) and onCrack (this unit's mounted build, switches off), round 1 Rust first and round 2 onCrack first, 2 rounds only (the time box).
Every cell valid; the VM's load average 1.4-3.5 around the runs; the Mac's load as in 1c.

| clients | | round 1 Rust | round 1 onCrack | round 2 onCrack | round 2 Rust |
|---|---|---|---|---|---|
| 1,000 | msgs/s | 1,288 | 1,713 | 1,769 | 1,570 |
| 1,000 | CPU/del us | 2.76 | 2.23 | 2.16 | 2.36 |
| 2,000 | msgs/s | 723 | 938 | 920 | 979 |
| 2,000 | CPU/del us | 2.49 | 2.02 | 2.08 | 1.99 |

onCrack over Rust, msgs/s: **1.33x and 1.13x at 1,000 clients** (CPU/del 0.81x and 0.92x); **1.30x and 0.94x at 2,000** (CPU/del 0.81x and 1.05x). So onCrack is ahead at 1,000
clients in both pairs and level with Rust at 2,000 within a spread of 0.94-1.30x; Rust itself moved 723-979 msgs/s between rounds there. Two rounds do not establish a ratio at 2,000
clients and none is claimed. It does say that round 4's 0.94x was one draw from this spread: round 4 final's three reps at 2,000 ranged 686-875 for onCrack against 769-886 for Rust.
Pss saturated: onCrack 294 MB at 1,000 clients and 373-382 MB at 2,000, Rust 112-113 and 133 MB (2.6-2.9x), as in round 4.

## Open

1. **`hold=3000` at 2,000 clients** (+12-21% in 5 of 6 clean pairs; 100 clients worse). A hold scaled to the number of subscribers, measured in the same alternation, is the one
   lead here with an effect beyond the spread.
2. **Log against ring at 1,000 clients** (about 8%, ring ahead, not resolved). If it is real it is not in the reading code (0.03 us a delivery in the profile); candidates are
   the per-group lock held while `WakeAll` runs in `LogGroup.Publish` and the hub-wide `Interlocked` publish number and byte counter, both once per frame and not per delivery.
3. **Per-connection heap** (48 KB live, section 4).
4. **A quiet host.** Every number here carries the Mac's load; `bench/lib/hostprobe.py` ratios were 1.04-1.23 before the kept runs and up to 2.3 after some. A rerun when the Mac's other sessions are idle would
   tighten sections 1 and 3 more than any further code.
5. **The picture** the request mentioned did not reach this unit (only its text did), so nothing was read from it.

## Review

- The only source changes are the bench-only flip (`BenchFlip.fs`, three reads in `Connection.run` at connection start, one in `Hub.Subscribe` when a group is made, a 20 ms-gated
  read in `BroadcastOrder.TakeHeld`), all inert unless `CAMPFIRE_CABLE_FLIP_FILE` is set; `PubsubTests` holds that. R4.5's keep-every-subscriber behaviour, the publish order and
  R5.2's lost-frame and memory-bound fixes are untouched.
- Every cable result in this unit is valid by the suite's checks (`posted == complete`, no client closed mid-run, no window stall), including the starved ones; starvation shows as rate, not loss.
- Tests: `dotnet test tests/Campfire.Cable.Tests` on macOS passes (115: 108 passed, 7 skipped, the Linux-only ones). `bin/linux-tests Cable` run as a whole fails one to three tests
  a run, a different set each time (`DirectTests` "many connections, each sees every frame once and in order", `TraceTests` "off, a connection has no trace...", `GoldenTests`
  "replays reference frames", and once `PubsubTests` "total: the client furthest behind..." on the base), with the Mac at load 4-9. The same suite on the base commit `b65d116` (a scratch
  worktree, since removed) failed 3 and 4 tests in two runs, `DirectTests` "many connections" and `TraceTests` "off..." among them both times; every one of them passes when run
  alone (`--filter-method`). They are timing tests that do not survive this host, not a regression of this unit; `bin/verify` (the whole suite) was not run in the time box.
- The restart-level A/B (1a) is the weaker evidence, and said so; 1b is the evidence this verdict rests on.

## Commits

All on branch `crack`, nothing pushed: `e1e8bbe` the bench-only flip file (`BenchFlip.fs`, `bench/cable/flip`) with the unit's scripts and the AGENTS.md paragraph; this report with its data (`bench/results/oncrack-r5-fanout/`) in the commit after it.
