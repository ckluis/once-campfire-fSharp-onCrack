# R4.5: Cable reliability, 2026-10-10

Plan: `plans/r4-reliability.md`. Code: `src/Campfire.Cable/Pubsub.fs` (the log), `Connection.fs` (publish order), `Socket.fs` (stall), `src/Campfire.App/Channels/Broadcasts.fs`
and `Controllers/Messages.fs` (the pressure gate). Tools: `bench/reliability/{run,summarize,sampler.py}`. Raw data and logs: `bench/results/oncrack-r4-reliability/`.

## Result

Upstream's `bin/reliability` `cable_heavy` (1,000 clients with six subscriptions each; 64 closed-loop posters with no limit; the harness waits up to 60 s for every
client to have every message), one session each, onCrack's after-run two rounds:

| app | subscribed | disconnected | delivered to every client / posted | messages/s | p99 post to last client | Pss peak |
|---|---|---|---|---|---|---|
| Rails 0aa339d | 1,000 | 0 | 552 / 552 | 21.7 | 24,084 ms | 3,136 MB |
| Rust f9dca47 | 1,000 | **899** | 64 / 65,151 | 4.3 | 357 ms (of the 64) | 127 MB |
| C cd0cbe4 | 224 | 829 | 15 / 35,967 | 1.0 | 39 ms | 73 MB |
| onCrack before R4.5 (`21791e2`) | 1,000 | **945** | 88 / 127,210 | 5.9 | 417 ms (of the 88) | 686 MB |
| onCrack before, cached decision | 1,000 | 869 | 0 / 78,103 | 0.0 | - | 714 MB |
| **onCrack** (`campfire-oncrack:app`, this unit) | 1,000 / 1,000 | **0 / 0** | **10,638 / 10,638, 10,521 / 10,521** | **574.1, 566.8** | 11,248, 12,165 ms | 906, 963 MB |
| onCrack, cached decision | 1,000 / 1,000 | 0 / 0 | 11,689 / 11,689, 12,520 / 12,520 | 633.2, 670.6 | 10,584, 10,387 ms | 966, 967 MB |

Before R4.5, a saturated room cut about nine clients in ten (Rust does the same): they were closed after falling 256 frames behind, and the harness's clients do not reconnect, so they miss every
later message. Now nobody is cut, every posted message reaches every client, and the server delivers 570 to 670 messages a second to a thousand clients while 64 posters hammer one room.
Rails also loses nobody, because its posters are so slow (22 messages a second) that its per-connection queues never grow; what it pays is 3.1 GB. The `cable` profile (4 posters,
the default load) is unchanged: 0 disconnected and every message delivered in every row (onCrack 437 messages/s against 439 before; the runs are 5,900 to 8,400 messages and the host was shared).
The overload profile (64 and 256 clients on four read routes) had 0 errors and 0 invalid responses for `oncrack` and `oncrack-cached` before and after
(`probes/baseline-fdlimit-invalid/` and `after-r1/`): no change 5.

What is not better: the p99 of a post to the last client is 11 s, not 0.4 s. The 0.4 s of the "before" row is over the 88 messages every client received before most were cut; the
11 s is over 10,600 messages, each waiting behind up to two thousand others in the slowest of a thousand clients' sockets, on a host where the load generator and the server share eight cores.
Peak memory is 0.9 to 1 GB against 0.7 GB for the cut run (which held no backlog and delivered nothing) and 3.1 GB for Rails.

## What the first baseline got wrong

`bench/results/oncrack-r4-reliability-baseline.md` (the other session, started 12:04) was meant to supply the "before" rows. It could not:

1. **Its `cable_heavy` rows are invalid for every app.** The VM shell's descriptor limit is 1,024, which holds 1,000 clients and four posters but not 64 posters beside them: their connections
   failed at once, 18 million refused posts and 13 delivered (Rails, Rust, C and both onCrack builds alike: `probes/baseline-fdlimit-invalid/`). `bench/reliability/run` raises the limit.
2. **Its load generator had no `disconnected` counter** (the binary of round 3, built before the harness's reliability change; the harness printed an empty field). I rebuilt `loadgen/` from the harness's
   branch (`rust:1.98.1-trixie`, `RUSTFLAGS=-C target-feature=+crt-static`, `--locked`; the old binary is kept beside it as `loadgen.old`).
3. **It died at 12:19** at the F# port's contract preparation (`contracts.rb`), after Rails, Rust and C round 1; onCrack was never reached. Nothing in this unit depends on the port.
4. **The harness did not know `oncrack-cached`'s runtime** in `reliability.rb` (`runtimes`, as `compare.rb` has it): fixed in the working tree and in the VM's copy (local to this checkout, not committed there).

C's Cable server accepted 124 to 224 of the 1,000 clients in this setup (the rows say so). I did not look into why; its row is a measurement of that environment and not a verdict on C.

## What changed

Each change is one commit; the numbers beside them are from this unit's runs, host load 3 to 11.

1. **A shared, byte-bounded log replaces the 256-frame ring** (`c9b00ad`). `LogGroup`: chunks of `Config.StreamCapacity` (256) frames, each subscriber a cursor (chunk, index), chunks nobody is
   in left to the GC; `Hub.RetainedBytes`, `RetainedPeakBytes`, `CutCount`. The oldest subscribers are cut when the log held behind the oldest exceeds `CAMPFIRE_CABLE_LAG_BYTES`: marked, removed from the group, woken,
   and their sockets aborted a second later if they have not said goodbye. `CAMPFIRE_CABLE_LOG=ring` is the old ring. *Deviations from the plan:* no per-chunk reader counts; the group finds the oldest subscriber's chunk with one pass over the
   subscribers (once per chunk, or when over budget, or from the heartbeat), which needs no `Interlocked` pair on the read path and cannot race a crossing against a cut. Accounting is by chunk, so the log can exceed the budget by one chunk.
   The cut waits a second (`Wake.CutGrace`) for a connection that is reading to send its `reconnect: true` and close, and aborts it after that.
2. **Publish order across a connection's streams** (`7c4ef84`). A hub-wide number per frame; `Connection.Merge` takes the lowest. `CAMPFIRE_CABLE_ORDER=stream` is the old order.
3. **No progress, not one slow write** (`f635d85`). `FinishSend` gives the write a fresh `CAMPFIRE_CABLE_STALL_MS` (30,000) whenever the kernel's acknowledged-byte count moved (Linux `TCP_INFO`, read every eighth of the time),
   or a send completed. Where the count is not available (macOS) only a completed send counts, as before.
4. **Not done: catch up in batches of 256.** The drain after posting stops is bounded by the kernel copy of 10 KB frames to a thousand sockets, not by syscalls; the backlog is now bounded instead (below).
5. **Not in the plan: a gate on posters** (`7e83a8d`). See below.
6. **Not in the plan: the budget is 256 MB** (`f5429fc`), not 64 MB.

### Two things the plan had wrong, and what they cost

**A message's Cable frame is about 10 KB, not 1.4 KB.** (The R4.1 notes say "10 KB frames"; I did not look.) So 64 MB held 6,500 messages, not 45,000, and the 64 posters, which onCrack serves faster than it can fan out,
filled it in seconds. Probes, all `cable_heavy` with the same image and one run each unless a second is listed (`probes/`):

| budget | gate on posters | disconnected | delivered to every client / posted | messages/s | drain after the last post | Pss peak |
|---|---|---|---|---|---|---|
| 64 MB | off | 884; 900 | 1,100 / 69,597; 655 / 56,825 | 73.3; 43.6 | 0 s | 1,283; 1,258 MB |
| 256 MB | off | 895; 895 | 3,958 / 40,331; 2,770 / 43,468 | 222.1; 165.0 | 2.8 s; 1.8 s | 1,406; 1,356 MB |
| 1 GiB | off | 0; 0 | 21,632 / 21,632; **37,848 / 44,171** | 416.9; 504.1 | 35.5 s; 60.05 s (the harness gave up) | 1,205; 1,614 MB |
| 64 MB | on | 3 | 3,488 / 10,459 | 159.4 | 6.4 s | 966 MB |
| **256 MB** | **on** | **0** | **10,822 / 10,822** | **578.7** | 3.6 s | 985 MB |

With a budget big enough that nobody is cut (1 GiB), the second run still failed the harness's test: 44,171 posts in 15 s, 6,300 of them not yet at every client when the harness stopped waiting after 60 s. A server that
takes posts faster than it can send them on has to slow the posters or cut the clients. The plan marked slowing the posters "not chosen, revisit only if complete < posted with no client cut"; that is this row, so it is built:
`Hub.Congested` says whether more than half of a room's subscribers are more than `CAMPFIRE_CABLE_PRESSURE_FRAMES` (2,048) frames behind the newest, and `Broadcasts.AwaitRoom` makes `MessagesController#create` wait, before it writes, while
they are, for at most `CAMPFIRE_CABLE_PRESSURE_MS` (2,000) per post. `CAMPFIRE_CABLE_PRESSURE=off` never waits. **It is on by default, against the plan**, because with it off the default configuration
fails the profile this unit exists for, and because nothing waits unless a room's fan-out is behind by seconds: the R4.1 cable suite (window 128) never gets near it. A post that waits has written nothing yet.
At 64 MB with the gate, three stragglers (the load generator serves 1,000 clients on three threads) still passed 6,500 messages and were cut, so the default budget is 256 MB (about 26,000 messages); it bounds what one stalled or
very slow client can pin per group, and is not a tuning of normal traffic.

**The first R4.5 probe, with the shipped plan's 64 MB and no gate, is the "after" the plan promised and it fails** (884 disconnected). That is why the table above is a table.

## R4.1 cable suite: no regression

`bench/results/oncrack-r4-reliability/cable-ab.sh`: the suite at 1,000 and 2,000 clients, raw client, window 128, the image `campfire-oncrack:app`, switches `CAMPFIRE_CABLE_LOG=ring` (R), `CAMPFIRE_CABLE_ORDER=stream` (L: the log, the old
order) and the default (D), alternated R L D D L R and then D L L D. `python3 bench/results/oncrack-r4-fanout/table.py cable-ab/*`. The Mac was shared throughout (load shown in each `load.txt`).

| clients | variant | runs | messages/s delivered to every client, median (each run) | server CPU per delivery, median (each run) |
|---|---|---|---|---|
| 1,000 | R, the ring | 2 | 1,385 (1,028; 1,742) | 2.86 us (3.59; 2.13) |
| 1,000 | L, the log, old order | 4 | 1,671 (1,777; 1,919; 1,565; 1,538) | 2.25 us (2.09; 1.95; 2.40; 2.48) |
| 1,000 | D, the shipped default | 4 | 1,645 (1,899; 1,403; 1,778; 1,513) | 2.30 us (1.99; 2.56; 2.13; 2.47) |
| 2,000 | R, the ring | 2 | 912 (797; 1,026) | 2.03 us (2.27; 1.79) |
| 2,000 | L, the log, old order | 4 | 886 (787; 954; 942; 830) | 2.09 us (2.32; 1.93; 1.83; 2.26) |
| 2,000 | D, the shipped default | 4 | 840 (782; 746; 898; 937) | 2.20 us (2.32; 2.44; 2.08; 1.88) |

Every run: `posted == complete`, `closed_midrun == 0`, no window stall. The spread inside one variant (25 to 35%) is larger than any difference between variants, so the log, and the publish order on top of it,
cost nothing I can resolve. The medians put D 2 to 5% behind L (the merge of a connection's streams is the difference between them) and level with R at 2,000 clients; two R runs are too few to say more, and
the first (3.59 us) was the first run of the session. Pss at 1,000 clients saturated: 300 MB in all three; at 2,000: 381, 413, 403 MB. A fresh pair of D and L runs would be needed to rule out a 2 to 5% cost of the order; I
did not make more.

## Tests

Cable tests (`tests/Campfire.Cable.Tests`): 98, of which on macOS 93 pass and 5 skip (the gather, stall and `record_reference` tests need Linux or a reference); `bin/linux-tests Cable` runs 97 and skips one:
three runs in a row passed twice and failed once on `pings every three seconds with a unix timestamp` (3.47 s against its 3.1 s limit; the host was loaded), and an earlier run failed two tests whose names I did not keep.
`bin/verify` (Release build, warnings as errors, every project): 1,176 tests, 0 failed, 12 skipped, none of them new.

New in this unit, `PubsubTests.fs` unless noted:
- the ring's two lag tests kept under `ring:`; a reader 100,000 frames behind reads every frame in order and then finds nothing; reads exact at 0, 1, 7, 8, 9, 15, 16, 17, 255, 256, 257, 511, 512, 513 frames with chunks of 8 and 256;
  one publisher and eight readers that stall at random on threads for two seconds lose and reorder nothing;
  chunks nobody can read are freed (a `WeakReference` to the first chunk dies after `GC.Collect`) and `RetainedBytes` comes back to one chunk; the oldest subscriber leaving frees the log behind it;
  a subscriber over the byte budget is cut (lagged, out of the group, woken, its connection aborted after the grace, a retired connection left alone) while the others read on and the log stays within budget plus a chunk;
  a subscriber that never reads is cut once 70 MB have gone past a 64 MB budget.
  **Mutations** (run once by hand): dropping the cursor move at a chunk crossing fails 7 of the 19 then-existing tests (the readers loop without end, now a failure by a 5-million-frame guard); starting the next chunk at index 1 fails 6.
- `merge:` three streams, 10,000 frames in a random interleaving, drained in 64-frame batches, come out in publish order and complete; a frame published after 1,000 frames of another stream is in batch 16, and in batch 32 with the old order;
  a lagged stream is reported and a stopped one dropped.
- `congested:` the verdict at the half-way point as subscribers drain and frames are published; a ring never says it.
- `SocketTests.fs` (Linux): a peer that reads nothing is cut between 450 and 1,500 ms at a 500 ms stall time; a peer that reads 2 MB at about 640 KB/s against a 600 ms stall time is never cut and gets every byte
  (disabling the progress check fails it: "Connection reset by peer" after 0.85 s).
- `ProtocolTests.fs`: the lagging-client test now sets `LagBytes = 1`.
- Not tested: `Broadcasts.AwaitRoom` and the gate in `MessagesController#create` have no test of their own; the profile above is their evidence.

## Not done, and why

- **The after-change run with three rounds** (deferred by the plan): two rounds of onCrack and the cached mode, one round of the others.
- **`SO_SNDBUF` per stalled socket**, and `ss -tm` totals in a stall test: not measured; the stall is cut at half a minute and the log no longer pins memory for it.
- **The 40-client stall check in `bench/cable`** (a quarter stop reading, 1,000 frames published): replaced by the two `Writer` tests on Linux and the lagging-client protocol test; the pass of 40 real connections is not built.
- **`Hub.RetainedPeakBytes` is not exported**: the tests check it, the benchmark could not read it. Pss is the memory number.
- **Why the saturated room's peak Pss is 0.9 to 1 GB**: the 64 posters' renderings and the server GC's gen0 budget (64 MB per heap, four heaps) are my guess; the 64 MB and 1 GiB probes have the same peak, so it is not the log.
- **C's Cable server taking 124 to 224 clients.**
- **Pixel parity on the whole matrix**: `bin/pixel-parity --fast --seeds default --only 'realtime/**'` (the states that change with Cable): 26 of 26 screenshots pixel-equal to Rails', 326 s, light scheme, Chromium only. The full lean matrix and the other seeds were not run: no HTML, CSS or frame content changed, only when frames are sent and which clients are cut.

## Reproduce

```sh
# images (colima): before = a worktree at 21791e2 with reference/ copied in, then docker build -f Dockerfile ... -t campfire-oncrack:r45-before ; after = parity/bin/candidate build (campfire-oncrack:app)
export RUST_IMAGE=campfire-rust-upstream:f9dca47 C_IMAGE=campfire-c-upstream:cd0cbe4 RAILS_IMAGE=campfire-rails-upstream:0aa339d \
  RAILS_BENCH_ENV='{"WEB_CONCURRENCY":"4","RAILS_MAX_THREADS":"1","RAILS_MIN_THREADS":"1"}' \
  ONCRACK_IMAGE=campfire-oncrack:r45-before ONCRACK_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64"}' \
  ONCRACK_CACHED_IMAGE=campfire-oncrack:r45-before ONCRACK_CACHED_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64","CAMPFIRE_FRESH_AUTH":"0"}'
bench/reliability/run bench/results/oncrack-r4-reliability/before-r1 --apps rails,rust,c,oncrack,oncrack-cached --profiles cable --rounds 1
export ONCRACK_IMAGE=campfire-oncrack:app ONCRACK_CACHED_IMAGE=campfire-oncrack:app
bench/reliability/run bench/results/oncrack-r4-reliability/after-r1 --apps oncrack,oncrack-cached --profiles overload,cable --rounds 2
python3 bench/reliability/summarize --write bench/results/oncrack-r4-reliability/before-r1 bench/results/oncrack-r4-reliability/after-r1
colima ssh -- bash -c 'cd REPO && ORDER="R L D D L R" bench/results/oncrack-r4-reliability/cable-ab.sh'
python3 site/build.py     # the reliability panel; it fails on a number it cannot source
```
