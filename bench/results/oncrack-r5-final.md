# onCrack round 5, final run: gates, upstream's harness, the cable suite and PR #6's reliability profiles, 2026-10-12/13

The closing measurement of round 5 and of the project, on the code the round ends with (`ee5a2e9`; `git diff 6abc183 HEAD -- src` is empty, and `6abc183` is the round 5 verifier's last code commit). Upstream's harness (`once-campfire-verification`, local adapter commit `a05b344`; PR #6's reliability profiles merged locally as `eed4105`), one colima VM, fresh authorization (onCrack's default) as the headline.

- Report: `/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-final.md`
- Data and scripts: `/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-final/` (start with `RESULTS.md`, `cable/RESULTS.md`, `reliability/RESULTS.md`, `pixels.md`, `kloc/kloc.md`, `RUNLOG.md`).
- The rules were fixed before any session: `oncrack-r5-final/PLAN.md` (commit `ee5a2e9`).
- The page is not touched here; the next unit rebuilds it from this file and the data.
- Images: Rails `0aa339d`, Rust `f9dca47`, C `cd0cbe4`, the F# port `9954ad0`, onCrack `campfire-oncrack:app` (id `bfcbb4633485`, label `ee5a2e91795e`); harness `a05b344`, load generator `351a66af`, seed `34f66576` for every harness session (`env.txt`, each session's `summary.json`).

## Verdict

**Ready to publish on correctness; the speed claim has to be quoted as a range, because this round did not get a quiet host.** Fresh authorization, upstream's harness, 16 clients, medians of every round of every session (PLAN rule 3: no session dropped), geometric means over the routes:

| | sessions (rounds a cell) | over Rust `f9dca47` | over C `cd0cbe4` | over the F# port | over Rails `0aa339d` |
|---|---|---:|---:|---:|---:|
| Normal profile, five workloads | 3 (9) | **3.76x** | **2.40x** | 5.25x | 35.7x |
| Mixed profile, four reads | 3 (9) | **3.76x** | **2.26x** | 6.78x | 56.4x |
| Cached decision (opt-in), normal | 3 (9) | 4.19x | 2.68x | 5.85x | |
| Cached decision (opt-in), mixed | 3 (9) | 4.51x | 2.71x | 8.13x | |

- **The point values are not the result; the spread is.** Each session's own geometric mean over Rust runs 2.11x, 3.28x, 4.74x (normal) and 6.33x, 3.12x, 3.00x (mixed); over C 1.41x to 3.81x. Only normal-1 and mixed-1 passed the plan's noise rule (22% and 24% of host samples at or above 150% non-VM CPU); the other four were NOISY (54-65%) because of other projects' Erlang VMs, Go test binaries and Python workers on the same Mac. The plan allows a profile three sessions and both profiles spent them. The honest reading is **about 2x to 5x Rust and 1.4x to 3.8x C, ahead at the median in every cell, with CPU per request as the steadier number (below).** The two-session pool the plan was designed around (sessions 1 and 2) reads 3.19x Rust and 2.44x C (normal), 3.96x and 2.15x (mixed); the one quiet normal session alone reads 2.11x and 1.46x, because the onCrack post path and room page fell hardest in it (section 2).
- **CPU per request, from the container's cgroup, agrees with "about 3.5x Rust and 2.5-3x C" on a room page.** Hand re-runs, seven sets: Rust spends 3.79x onCrack's CPU for a room page and C 2.93x; in the three sets that were not NOISY, 3.75x and 2.68x (round 4: 3.25x and 2.02x). `src/` for the HTTP path did not change between round 4 and now (the only `src/` changes since `ea1f85b` are in `Campfire.Cable` and one hold setting in `Broadcasts.fs`), so the change is the Rust and C readings (their quiet-set room-page CPU is 75.6 and 54.1 us now, 70.1 and 48.4 in round 4) and onCrack's (20.2 against 22.4), on a different afternoon. I did not test that explanation.
- **Everything was validated.** 224,402,307 timed responses passed the full content contract, 2,762,229 acknowledged writes were audited against the messages, rich-text and search-index rows in the harness sessions (4,474,566 more in the hand re-runs), and there were 0 errors or invalid responses across 972 raw samples. I recomputed this from the 486 raw cells; `pool.py` reproduces `pooled.md` byte for byte.
- **The UI is identical: 944 of 944 screenshots pixel-equal** on every seed (0 different, 0 not captured, 0 flaky), and `bin/verify` passed 1,187 of 1,204 tests with 17 skipped and 0 failed (`bin/linux-tests Cable`: 118 of 120, 2 skipped, 0 failed).
- **Cable fan-out: ahead at 100-1,000 clients, level at 2,000.** Quiet session (7% noisy samples), onCrack delivers 1.65x, 1.24x, 1.17x and **1.01x** Rust's messages a second at 100, 500, 1,000 and 2,000 clients with 0.62x, 0.81x, 0.84x and 0.96x of its server CPU per delivery. At 2,000 clients it is level, not ahead: the ranges overlap and both servers are bound by the `sendmsg` syscall. Rust is clearly faster in one cell, paced latency at 100 clients (3.3 against 5.2 ms p50). **No message failed to reach any client in any of the 140 cable phases of three sessions**; round 4's "one message missing" was traced and fixed (section 3).
- **PR #6 reliability, 3 rounds for every app: onCrack at HEAD disconnected 0 of 1,000 clients and delivered every posted message in `cable_heavy` in all 3 rounds (710-741 messages a second), fresh and cached, against 902-959 clients cut for Rust and 833-860 for onCrack before R4.5.** This is a different policy from Rust's, not a free win: Rust takes 4,500-5,200 posts a second and cuts the readers who cannot keep up; onCrack holds the posters (843-904 posts a second, a 8-10 s p99 from a post to the slowest client) and keeps everyone, at about 1 GB of Pss against Rust's 125 MB.
- **What does not hold.** Memory: onCrack's Pss is 2.4-2.9x Rust's in the cable suite. Rust wins paced latency at 100 clients. The post path is the cell most exposed to a shared disk, and the climb chart's project suite shows 12-14% more CPU per post than round 3's final image (213.8 against 188.4 us) that I could neither confirm nor rule out (open item 2).

## 0. What was in the directory, and what I re-ran

Five runners had written to `oncrack-r5-final/`: gates (PLAN steps 1-5), HTTP (7 and 9), cable (6), reliability (8) and the climb log. I checked each step against `PLAN.md` before writing, from the raw files and not from the runners' summaries:

| PLAN.md step | State when I started | What I did |
|---|---|---|
| 1 Plan | Written and committed before any session (`ee5a2e9`). | Kept. |
| 2 Images | `campfire-oncrack:app` rebuilt from the clean measured worktree at `ee5a2e9`; reference, parity wrapper and candidate rebuilt; digests in `env.txt`, and every session's `summary.json` carries the same image ids and `dirty: False` for all six apps. | Kept. |
| 3 Pixel gate | 944 of 944 (`pixels/pixel-parity.json`: total 944 equal, 0 different, 0 not captured, 0 flaky; by seed 864 / 24 / 32 / 16 / 8). | Kept. |
| 4 `bin/verify`, seed required | 1,204 tests, 1,187 passed, 0 failed, 17 skipped; Linux Cable suite 120 tests, 118 passed. | Kept. |
| 5 KLOC | Counted by upstream's cloc method, calibrated. | Kept. |
| 6 Cable suite, one uninterrupted session | Three whole sessions: 1 incomplete and NOISY, 2 NOISY and guard-stopped, **3 complete and quiet (the headline)**. | Re-derived the phase validity from the stored json; nothing re-run. |
| 7 Harness, two sessions a profile | Six sessions (normal-1/2/3, mixed-1/2/3, each exit 0) and a seventh set aside whole. Normal-2 and mixed-2 were NOISY, so each profile ran its one allowed re-run. | **Recomputed all 486 cells (errors, invalid responses, audits) and re-ran `pool.py`**: identical to `pooled.md`. Added a subset cut (`pooled-subsets.md`, below). Nothing re-run: no step was missing or broken. |
| 8 PR #6 reliability, 3 rounds | `main/` (six apps, overload and cable, 3 rounds, one harness process) and `fsharp/` (cable profiles, 3 rounds). | **Spot-checked every `cable_heavy` row against `harness-output/*.json`** (disconnected, ready, posted, complete, messages a second): they match. |
| 9 Hand re-runs | Seven sets of four apps: 84 windows, 28 audits. | Kept. |
| Climb log | Four project-suite rows (round 3 and round 5 images, fresh and cached) in `oncrack-log.jsonl`. | Kept; read for the history. |

Corrections I made to the data's own files: `RESULTS.md`'s session table gave mixed-1's start as 22:42; its `summary` metadata says 02:28:19Z, 22:28 EDT. Fixed. Added `pool-subsets.py` and its output `pooled-subsets.md`. Nothing else in the directory was changed, and no measurement was re-run.

## 1. The checks

Run on `ee5a2e9` (`src/` equal to the verifier's last code commit `6abc183`) before the sessions.

| Check | Result | Where (under `oncrack-r5-final/`) |
|---|---|---|
| Full pixel gate, `bin/pixel-parity` on every seed (the full lean matrix: Chromium desktop and phone, light and dark; the smoke states on Firefox and WebKit; the breakpoint sweep), against the Rails reference | **944 of 944** pixel-equal: default 864, crowd 24, custom_styles 32, first_run 16, restricted 8; 0 different, 0 not captured, 0 flaky. Round 3's was 940: the 4 extra are Chromium cells of `search/results/order`, added by R3.3 after that gate. The room-page capture hash is identical on both sides and equals round one's (`ac7420e6d0a8`). | `pixels.md`, `pixels/` |
| `bin/verify` with `CAMPFIRE_REQUIRE_SEED=1` | Build 0 warnings; **1,204 tests: 1,187 passed, 0 failed, 17 skipped**. None of the skips was for want of the seed: 9 need Linux's `sendmsg` and `TCP_INFO`, the rest are the recorder, THP and TLS-ticket tests and 5 that need a Ruby-produced database or a manual switch. | `logs/verify.log` |
| `bin/linux-tests Cable` (extra: the 9 skipped Cable tests are the lost-frame tests this round is about) | **120 tests: 118 passed, 0 failed, 2 skipped** (the gated pin-stress reproducer and the recorder). | `logs/linux-cable.log` |
| KLOC by upstream's rules | Section 5. | `kloc/kloc.md` |

Three harness faults in the pixel gate, none a pixel difference, each passed on re-run: `auth/sign_in/error` not captured in slice B's three attempts (the harness's 30 s stylesheet wait on a freshly started server; a fourth run of that state alone captured all 4 cells, all equal); the compare crashing 50 cells into `realtime/**` with "Response has been disposed" in `parity/capture/network.ts` (re-run as three sub-slices of 40 + 40 + 24 cells); one compare hanging 40 minutes at 25 of 40 cells with the VM idle (killed, re-run with a 1,500 s watchdog, passed first try). Nothing in `src/` or the harness was changed for them. The Mac's free space also went under the 12 GiB floor during the gate (11.5 GiB, then 8.6 GiB while the compare hung); that was another project's `go test` filling `~/Library/Caches/go-build` (12 GB), cleaned with `go clean -cache` once no go process ran. The runner let units run through the first two dips because its driver checked space only at a unit's start; it is recorded in `pixels.md`.

The round's own attack suites and gates ran in its units (`oncrack-r5-verifier.md`): the lost-frame fix held under every attack, the memory bound's reader protocol had three defects that the verifier found and fixed with tests that fail on the code before. The durability kill -9 test was not repeated: the round changed nothing in the database, the writer or the post path's commit (section 7 lists what changed).

## 2. The numbers: upstream's harness

### Method

- Per session: `bin/benchmark --rounds 3 --duration 8 --concurrencies 16 --cpus 0-3 --client-cpus 4-7 --apps rails,rust,c,fsharp,oncrack,oncrack-cached`, **with `--routes room_show,messages_page,sidebar,search,post_message`** (normal; the same four reads and `--mixed-write-rate 10` for mixed) as rounds 2-4 ran them. PLAN.md's command line omitted `--routes`; the first normal session ran the harness's default eight routes by mistake and was set aside whole (`discarded-normal-1-all-routes/`, with a README; not pooled; it shows onCrack ahead on the three extra routes too).
- `oncrack` is the shipped default (`CAMPFIRE_FRESH_AUTH` on): the headline. `oncrack-cached` is the same image with `CAMPFIRE_FRESH_AUTH=0`: the opt-in, beside it. Both set `CAMPFIRE_RESPONSE_CACHE_MB=64`.
- Order of sessions, as planned: normal-1, mixed-1, normal-2, mixed-2, then one re-run of each NOISY one (normal-3, mixed-3). Pooling by `PLAN.md` rule 3: each cell's median over all rounds of all of its profile's sessions (9 rounds a cell). No session dropped, none adjusted.
- Tables from `pool.py` (`pooled.md`), `table.py` (each session, `normal-N/table.md`, `mixed-N/table.md`), `totals.py` (`totals.md`) and `noise.py`.

### Normal profile

Median requests/sec of 9 rounds (3 sessions x 3) [min-max], 16 clients. Sessions: normal-1, normal-2, normal-3

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| **onCrack, fresh authorization (default)** | 153,660 [59,273-161,968] | 155,205 [37,724-172,988] | 169,116 [50,451-183,123] | 164,928 [60,920-174,672] | 8,726 [850-13,732] |
| onCrack, cached decision (opt-in) | 154,260 [55,229-172,728] | 172,052 [19,458-184,859] | 180,585 [76,324-194,090] | 170,166 [53,961-187,215] | 12,289 [5,856-14,426] |
| Rust f9dca47 | 30,806 [11,516-48,636] | 35,696 [4,663-44,434] | 40,532 [7,412-55,386] | 34,833 [4,203-55,382] | 5,001 [1,099-6,392] |
| C cd0cbe4 | 67,947 [54,914-74,480] | 73,880 [14,224-76,997] | 69,074 [27,233-77,639] | 59,600 [39,698-80,266] | 3,517 [1,092-5,648] |
| F# port | 17,109 [2,989-33,393] | 26,722 [10,928-40,265] | 22,901 [8,130-34,742] | 23,587 [2,419-31,920] | 5,909 [864-8,332] |
| Rails 0aa339d | 4,005 [1,329-4,852] | 3,628 [891-4,796] | 4,298 [1,218-5,405] | 4,866 [2,624-5,383] | 328 [36-378] |

| Ratio of medians | Room page | Messages page | Sidebar | Search | Post a message | Geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 4.99x | 4.35x | 4.17x | 4.73x | 1.74x | **3.76x** |
| oncrack / c | 2.26x | 2.10x | 2.45x | 2.77x | 2.48x | **2.40x** |
| oncrack / fsharp | 8.98x | 5.81x | 7.38x | 6.99x | 1.48x | **5.25x** |
| oncrack / rails | 38.37x | 42.78x | 39.35x | 33.89x | 26.63x | **35.74x** |
| oncrack / oncrack-cached | 1.00x | 0.90x | 0.94x | 0.97x | 0.71x | **0.90x** |
| oncrack-cached / rust | 5.01x | 4.82x | 4.46x | 4.89x | 2.46x | **4.19x** |
| oncrack-cached / c | 2.27x | 2.33x | 2.61x | 2.86x | 3.49x | **2.68x** |
| oncrack-cached / fsharp | 9.02x | 6.44x | 7.89x | 7.21x | 2.08x | **5.85x** |
| c / rust | 2.21x | 2.07x | 1.70x | 1.71x | 0.70x | **1.56x** |

### Mixed profile (16 readers plus a writer at 10 posts/s)

Median requests/sec of 9 rounds (3 sessions x 3) [min-max], 16 clients. Sessions: mixed-1, mixed-2, mixed-3

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| **onCrack, fresh authorization (default)** | 121,851 [9,787-163,603] | 134,121 [32,681-176,140] | 163,133 [17,142-184,082] | 105,540 [28,056-182,873] |
| onCrack, cached decision (opt-in) | 129,493 [43,741-164,818] | 158,977 [23,038-181,520] | 171,920 [50,321-189,230] | 164,552 [10,636-186,291] |
| Rust f9dca47 | 34,150 [14,806-39,364] | 30,271 [11,186-43,301] | 38,675 [7,052-51,364] | 35,179 [6,055-50,054] |
| C cd0cbe4 | 50,283 [5,003-70,330] | 49,452 [11,144-74,314] | 69,949 [9,753-79,393] | 62,188 [10,403-78,362] |
| F# port | 15,648 [927-32,067] | 21,913 [3,396-40,791] | 21,506 [2,592-36,949] | 18,071 [2,788-34,192] |
| Rails 0aa339d | 2,287 [68-2,805] | 1,134 [256-3,306] | 3,185 [653-3,636] | 3,367 [794-3,819] |

| Ratio of medians | Room page | Messages page | Sidebar | Search | Geometric mean |
|---|---:|---:|---:|---:|---:|
| oncrack / rust | 3.57x | 4.43x | 4.22x | 3.00x | **3.76x** |
| oncrack / c | 2.42x | 2.71x | 2.33x | 1.70x | **2.26x** |
| oncrack / fsharp | 7.79x | 6.12x | 7.59x | 5.84x | **6.78x** |
| oncrack / rails | 53.28x | 118.28x | 51.22x | 31.34x | **56.40x** |
| oncrack / oncrack-cached | 0.94x | 0.84x | 0.95x | 0.64x | **0.83x** |
| oncrack-cached / rust | 3.79x | 5.25x | 4.45x | 4.68x | **4.51x** |
| oncrack-cached / c | 2.58x | 3.21x | 2.46x | 2.65x | **2.71x** |
| oncrack-cached / fsharp | 8.28x | 7.26x | 7.99x | 9.11x | **8.13x** |
| c / rust | 1.47x | 1.63x | 1.81x | 1.77x | **1.67x** |

Fresh over cached reads 0.90x and 0.83x here, which is not a result: the two share an image and differ by one lookup, the cells swing 3-10x within a session, and the hand re-runs (same-set alternation, server CPU) put them level (1.03x and 0.99x for reads; section 2, hand re-runs).

### Each session alone, and the pooling check

Geometric mean of the medians per session (`totals.md`), then the plan's pool and two cuts of it (`pooled-subsets.md`, from `pool-subsets.py`):

| Session | host samples at >= 150% | rule 2 | fresh/Rust | fresh/C | fresh/port | cached/Rust | cached/C | fresh/cached |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| normal-1 | 22% | ok | 2.11x | 1.46x | 2.73x | 3.50x | 2.42x | 0.60x |
| normal-2 | 56% (of the 9 of 16 minutes sampled) | NOISY | 3.28x | 2.99x | 5.23x | 3.31x | 3.02x | 0.99x |
| normal-3 (re-run of normal-2) | 65% | NOISY | 4.74x | 1.41x | 6.72x | 7.49x | 2.23x | 0.63x |
| mixed-1 | 24% | ok | 6.33x | 2.38x | 5.25x | 5.31x | 2.00x | 1.19x |
| mixed-2 | 54% | NOISY | 3.12x | 1.48x | 4.76x | 5.44x | 2.58x | 0.57x |
| mixed-3 (re-run of mixed-2) | 65% | NOISY | 3.00x | 3.81x | 11.13x | 4.10x | 5.22x | 0.73x |

| Profile | sessions pooled | rounds a cell | fresh/Rust | fresh/C | fresh/port | fresh/cached | C/Rust |
|---|---|---:|---:|---:|---:|---:|---:|
| Normal | all three (the headline) | 9 | **3.76x** | **2.40x** | 5.25x | 0.90x | 1.56x |
| Normal | first two (the plan's design) | 6 | 3.19x | 2.44x | 4.52x | 0.92x | 1.31x |
| Normal | the quiet one (1) | 3 | 2.11x | 1.46x | 2.73x | 0.60x | 1.45x |
| Mixed | all three (the headline) | 9 | **3.76x** | **2.26x** | 6.78x | 0.83x | 1.67x |
| Mixed | first two | 6 | 3.96x | 2.15x | 6.03x | 0.92x | 1.84x |
| Mixed | the quiet one (1) | 3 | 6.33x | 2.38x | 5.25x | 1.19x | 2.66x |

- The two quiet sessions disagree with each other (2.11x and 6.33x over Rust), so a quiet host did not make the figure steadier here; they were quiet by the 150% rule at the host level, and the swings are inside the apps' own cells (normal-1: onCrack's fresh room page 116,372 [59,273-159,841] and post 3,287 [1,975-12,449], its cached arm 166,566 and 12,489 on the same image).
- The noise is not symmetric. onCrack's reads need about 2.5 of the 4 client cores for 160k requests a second, so another project's load on the client cores lowers them more than it lowers Rust's or C's; the post path (disk) fell 10x under another project's fsyncs (normal-1 post 1,975 to 12,449).
- Round 3 found the same shape (2.68x and 3.33x in two sessions); round 4 had one quiet session (3.29x). Across all the normal sessions on record the figure over Rust is 2.11x to 4.74x. **Quote "about 3-4x Rust and 2.4x C on upstream's harness, with a per-session range of 2.1x to 4.7x", not 3.76x alone.**

### Hand re-runs: room page, mixed and post (review.py: 15 s warm-up, 10 s window, 16 clients, server CPU from the cgroup)

`review.py`, outside `bin/benchmark`: one container per app for the three phases, every response validated, every acknowledged post audited, server CPU read from the container's cgroup. Seven sets of four apps (fresh, cached, Rust, C): forward, reversed, forward, reversed, then one re-run of each NOISY set (the plan allows one).

| App | phase | req/s per run | CPU us/request per run | median req/s | median CPU us/request |
|---|---|---|---|---:|---:|
| **onCrack, fresh authorization (default)** | room_show | 128,460, 165,256, 152,129, 40,624, 118,961, 159,997, 113,456 | 25.7, 19.3, 21.5, 48.4, 27.0, 20.2, 24.9 | 128,460 | 24.9 |
| **onCrack, fresh authorization (default)** | mixed | 107,464, 139,234, 152,843, 40,311, 19,056, 159,676, 161,662 | 29.4, 24.0, 21.4, 51.7, 90.6, 20.1, 19.7 | 139,234 | 24.0 |
| **onCrack, fresh authorization (default)** | post_message | 2,321, 15,403, 12,880, 14,317, 1,838, 15,395, 9,437 | 1011.7, 194.9, 240.7, 211.3, 1227.3, 194.5, 287.1 | 12,880 | 240.7 |
| onCrack, cached decision (opt-in) | room_show | 72,695, 172,174, 137,703, 65,424, 54,570, 131,435, 153,775 | 31.8, 18.1, 24.3, 32.5, 37.2, 23.6, 19.2 | 131,435 | 24.3 |
| onCrack, cached decision (opt-in) | mixed | 11,030, 153,401, 137,187, 16,882, 22,350, 155,080, 169,290 | 150.0, 20.8, 24.3, 104.6, 60.8, 21.3, 18.6 | 137,187 | 24.3 |
| onCrack, cached decision (opt-in) | post_message | 2,914, 15,489, 7,516, 2,564, 4,347, 13,712, 9,485 | 769.5, 191.6, 388.2, 902.8, 577.8, 217.2, 312.1 | 7,516 | 388.2 |
| Rust f9dca47 | room_show | 7,986, 38,480, 6,478, 31,431, 8,479, 38,514, 36,411 | 235.6, 74.7, 278.4, 94.5, 232.3, 75.6, 81.7 | 31,431 | 94.5 |
| Rust f9dca47 | mixed | 13,107, 7,164, 27,196, 20,703, 42,526, 35,544, 39,528 | 187.2, 303.5, 114.5, 139.8, 69.0, 83.2, 74.6 | 27,196 | 114.5 |
| Rust f9dca47 | post_message | 1,824, 5,250, 3,385, 1,796, 3,840, 5,252, 5,940 | 1319.3, 524.7, 875.2, 1330.4, 755.2, 542.4, 489.0 | 3,840 | 755.2 |
| C cd0cbe4 | room_show | 27,244, 33,217, 45,434, 62,584, 25,148, 60,990, 66,297 | 94.3, 76.4, 73.0, 49.7, 84.4, 54.1, 49.0 | 45,434 | 73.0 |
| C cd0cbe4 | mixed | 46,493, 70,191, 39,320, 57,531, 3,478, 67,025, 53,779 | 67.9, 46.6, 84.4, 56.0, 787.8, 49.5, 61.6 | 53,779 | 61.6 |
| C cd0cbe4 | post_message | 1,134, 4,084, 3,217, 4,589, 2,407, 5,344, 5,341 | 2261.0, 798.6, 1045.1, 711.4, 1268.8, 625.4, 630.7 | 4,084 | 798.6 |

| CPU per request, ratio of medians over runs | room page | mixed reads | post |
|---|---:|---:|---:|
| all seven sets: rust / oncrack | 3.79x | 4.78x | 3.14x |
| all seven sets: c / oncrack | 2.93x | 2.57x | 3.32x |
| all seven sets: rust / oncrack-cached | 3.89x | 4.72x | 1.95x |
| all seven sets: c / oncrack-cached | 3.01x | 2.54x | 2.06x |
| all seven sets: oncrack / oncrack-cached | 1.03x | 0.99x | 0.62x |
| the three non-NOISY sets: rust / oncrack | 3.75x | 4.15x | 2.69x |
| the three non-NOISY sets: c / oncrack | 2.68x | 2.47x | 3.24x |
| round 4 (four sets, two quiet): rust / oncrack | 3.25x | 3.13x | 1.87x |
| round 4: c / oncrack | 2.02x | 2.11x | 2.18x |

- The quiet sets (`review-quiet-sets.md`, chosen by rule 2 before looking: review-rev, review-rev2-b, review-fwd2-b) give onCrack 20.2 us for a room page, 20.1 mixed and 194.9 per post; Rust 75.6, 83.2 and 524.7; C 54.1, 49.5 and 630.7. The cached decision reads 19.2, 20.8 and 217.2. **Fresh authorization costs nothing measurable against the cached decision on a read (20.2 against 19.2 us); on the post the quiet sets read 194.9 against 217.2 and the all-set median 240.7 against 388.2, i.e. noise.**
- Sets rev, rev2-b and fwd2-b were not NOISY (18% of samples at or above 150%); fwd, fwd2, rev2 and fwd-b were (65-88%): `review-noise.txt`. Of the 84 timed windows every one was valid; 28 audits all ok (4,474,566 acknowledged posts, rich-text rows equal, 0 search-index rows missing).
- The rows that swing (onCrack post 1,838 to 15,403 req/s, 194 to 1,227 us) swing with the host's disk, as they did in rounds 3 and 4.

### Sessions and validation

| Session | Timed responses validated | Acknowledged writes audited | Errors + invalid | Raw samples | Peak generator CPU % |
|---|---:|---:|---:|---:|---:|
| mixed-1 | 41,614,259 | 7,017 | 0 | 144 | 251.5 |
| mixed-2 | 31,779,395 | 7,034 | 0 | 144 | 246.0 |
| mixed-3 | 30,731,302 | 6,867 | 0 | 144 | 246.8 |
| normal-1 | 43,868,876 | 986,759 | 0 | 180 | 253.4 |
| normal-2 | 43,122,716 | 1,096,876 | 0 | 180 | 261.6 |
| normal-3 | 33,285,759 | 657,676 | 0 | 180 | 247.9 |
| **all** | **224,402,307** | **2,762,229** | **0** | **972** | |

Independently recomputed from the 486 raw cells: 0 cells with errors or invalid responses, 108 post-write audits all `verified`, the same two totals.

### The host

Sampled every 10 s (non-VM CPU, top four processes, load average). A session waited for three quiet samples (under 100%) or 10 minutes (`scripts/hostload-wait.sh`).

| Sampler | Samples during the run | At 150% or more | Max | Median | Plan rule 2 |
|---|---:|---:|---:|---:|---|
| normal-1 | 100 | 22 (22%) | 334% | 38% | ok |
| mixed-1 | 82 | 20 (24%) | 368% | 41% | ok |
| normal-2 | 54 | 30 (56%) | 558% | 180% | NOISY (sampler lost its last 8 minutes) |
| mixed-2 | 82 | 44 (54%) | 618% | 171% | NOISY |
| normal-3 | 106 | 69 (65%) | 493% | 220% | NOISY |
| mixed-3 | 88 | 57 (65%) | 604% | 196% | NOISY |
| discarded-normal-1-all-routes | | 48% | | | NOISY, not pooled |
| review-fwd / fwd-b / fwd2 / rev2 | 34 each | 88% / 85% / 68% / 65% | 403-918% | 258-309% | NOISY |
| review-rev / rev2-b / fwd2-b | 34 each | 18% each | 291-370% | 26-68% | ok |

- The load was another project's work: `beam.smp` (Erlang VMs at 100-490% each), Go test binaries, Python workers and Spotlight. Nothing of this project's ran beside a session (the top four processes are in each file).
- normal-2's sampler stopped for about 8 minutes (the foreground wait was moved to the background by the tool's timeout); the session itself exited 0, and its noise figure covers only the sampled 9 of about 16 minutes. Noted in the host-load file and in `RESULTS.md`.

## 3. The cable suite

`bench/run --apps rust,fsharp,oncrack --suites cable`: N signed-in clients each hold a WebSocket with the room's subscriptions; four posters post into the room, never more than 128 messages ahead of what every client has received; a message counts when the last client has it. The raw epoll client (`bench/loadgen/src/rawcable.rs`, 3 threads), 100 / 500 / 1,000 / 2,000 clients, 15 s saturated, fresh container per part, server on CPUs 0-3, load generator on 4-7. Three reps (rep 1 Rust, port, onCrack; rep 2 reversed; rep 3 as 1), then a sends pass per app that counts send syscalls. Rust is upstream's `f9dca47` image.

### Three sessions were run; the headline is session 3

| Session | What happened | Host samples >= 150% | Status |
|---|---|---:|---|
| 1 (`cable/session-1-incomplete/`) | Complete except Rust rep 3: `bench/run` read its memory file at the instant the sampler renamed it, aborted that part with no `rust-3.json`. `bench/run` now retries that read (no `src/` change). | 66% | NOISY and incomplete, not pooled, re-run |
| 2 (`cable/session-2/`) | All 9 reps complete; the sends pass was stopped by the 12 GiB disk guard (another project's Go cache), after Rust; the port and onCrack sends finished in a continuation. | 64% | NOISY and guard-stopped, not pooled, re-run |
| **3 (`cable/session-3/`)** | **All 12 parts, one uninterrupted session, no guard stop.** | **7%** | **Quiet. The headline.** |

The plan said "a session the guard or a failure interrupts is reported incomplete and re-run whole once"; this took two re-runs, because the first re-run was NOISY and guard-stopped too. The plan's limit of three sessions is respected. The reason not to pool is the spread: onCrack at 1,000 clients read 1,407 / 1,709 / 226 in session 1, 550 / 362 / 1,460 in session 2 and 1,925 / 1,995 / 2,002 in session 3. The headline therefore rests on session 3 alone, one session.

### Validation, every cable phase of the session (and of all three)

| app (session 3) | phases | all clients subscribed | every posted message reached every client (paced and saturated) | failed connects | closed mid-run | window stalls |
|---|---|---|---|---|---|---|
| Rust f9dca47 | 16 | 16/16 | 16/16 | 0 | 0 | 0 |
| F# port | 16 | 16/16 | 16/16 | 0 | 0 | 0 |
| onCrack | 16 | 16/16 | 16/16 | 0 | 0 | 0 |

All three sessions together: 140 phases in the stored json (44 + 48 + 48; Rust rep 3 of session 1 has no json, and its four phases read N / N in that session's log): 0 phases with a message short of any client, 0 closed mid-run, 0 odd frames, 0 markers past the cap, 0 window stalls (`phases.py`, `phases flagged: 0` in each `phases.md`). **Round 4's single phase in which one of 34,741 messages did not reach every client has not recurred.** Its cause is in section 7 and `oncrack-r5-lost-frame.md`.

### Delivered messages per second (each message to every client), median of 3 and the reps in run order

| clients | Rust | F# port | **onCrack** | **onCrack / Rust** | **onCrack / port** | port / Rust | reps in run order (Rust / port / onCrack) |
|---|---|---|---|---|---|---|---|
| 100 | 4,155 [2,990-4,224] | 3,407 [2,975-3,617] | **6,859** [5,992-6,923] | **1.65x** | **2.01x** | 0.82x | 2,990,4,155,4,224 / 3,407,2,975,3,617 / 5,992,6,923,6,859 |
| 500 | 2,625 [2,564-2,758] | 995 [924-1,005] | **3,251** [3,149-3,287] | **1.24x** | **3.27x** | 0.38x | 2,758,2,625,2,564 / 924,995,1,005 / 3,149,3,287,3,251 |
| 1,000 | 1,706 [1,249-1,724] | 464 [322-469] | **1,995** [1,925-2,002] | **1.17x** | **4.30x** | 0.27x | 1,249,1,706,1,724 / 322,469,464 / 1,925,1,995,2,002 |
| 2,000 | 1,054 [789-1,054] | 211 [205-212] | **1,067** [970-1,069] | **1.01x** | **5.05x** | 0.20x | 789,1,054,1,054 / 205,211,212 / 970,1,067,1,069 |

### Server CPU per delivery and cores, load generator cores, sends per delivery, Pss, latency (medians of 3)

(The container's cpu.stat over the saturated phase divided by messages x clients; the load generator's cores of 4; sends = send, sendmsg and write syscalls over 3 s of the saturated phase per delivery; Pss idle and saturated in MB; paced latency of a post to the last client / to a client, ms p50 / p99.)

| clients | | Rust | F# port | onCrack | onCrack / Rust |
|---|---|---|---|---|---|
| 100 | server CPU us / delivery | 7.17 | 8.58 | 4.44 | 0.62x |
| 100 | server cores busy | 2.96 | 2.99 | 2.99 | 1.01x |
| 100 | load generator cores busy | 1.43 | 1.30 | 1.58 | 1.10x |
| 100 | sends / delivery | 0.622 | 0.641 | 0.330 | 0.53x |
| 100 | Pss idle / saturated (MB) | 39 / 100 | 111 / 280 | 113 / 272 | 2.92x / 2.72x |
| 100 | paced post -> last client p50 / p99 | 3.3 / 4.6 | 5.0 / 15.5 | 5.2 / 15.2 | 1.55x |
| 100 | paced post -> a client p50 / p99 | 2.9 / 4.4 | 4.3 / 15.3 | 4.8 / 15.0 | 1.62x |
| 100 | saturated post -> last client p50 / p99 | 1.1 / 4.7 | 1.2 / 3.5 | 1.0 / 3.7 | 0.84x |
| 500 | server CPU us / delivery | 2.74 | 7.59 | 2.21 | 0.81x |
| 500 | server cores busy | 3.59 | 3.74 | 3.55 | 0.99x |
| 500 | load generator cores busy | 2.64 | 1.77 | 2.73 | 1.04x |
| 500 | sends / delivery | 0.214 | 0.441 | 0.157 | 0.73x |
| 500 | Pss idle / saturated (MB) | 103 / 106 | 280 / 561 | 272 / 285 | 2.64x / 2.70x |
| 500 | paced post -> last client p50 / p99 | 6.3 / 9.4 | 7.5 / 11.5 | 6.1 / 11.7 | 0.96x |
| 500 | paced post -> a client p50 / p99 | 4.3 / 7.6 | 4.7 / 9.7 | 4.6 / 11.5 | 1.07x |
| 500 | saturated post -> last client p50 / p99 | 5.7 / 20.2 | 6.1 / 23.0 | 6.5 / 23.1 | 1.15x |
| 1,000 | server CPU us / delivery | 2.25 | 8.30 | 1.90 | 0.84x |
| 1,000 | server cores busy | 3.80 | 3.88 | 3.76 | 0.99x |
| 1,000 | load generator cores busy | 2.83 | 1.58 | 2.91 | 1.03x |
| 1,000 | sends / delivery | 0.102 | 0.364 | 0.102 | 1.00x |
| 1,000 | Pss idle / saturated (MB) | 112 / 114 | 553 / 689 | 282 / 317 | 2.52x / 2.77x |
| 1,000 | paced post -> last client p50 / p99 | 10.6 / 13.4 | 12.9 / 20.1 | 9.1 / 12.5 | 0.86x |
| 1,000 | paced post -> a client p50 / p99 | 6.5 / 11.7 | 7.9 / 17.4 | 6.4 / 11.5 | 0.99x |
| 1,000 | saturated post -> last client p50 / p99 | 19.9 / 68.4 | 18.1 / 68.0 | 27.9 / 66.6 | 1.40x |
| 2,000 | server CPU us / delivery | 1.86 | 9.22 | 1.79 | 0.96x |
| 2,000 | server cores busy | 3.94 | 3.88 | 3.78 | 0.96x |
| 2,000 | load generator cores busy | 2.90 | 1.42 | 2.91 | 1.01x |
| 2,000 | sends / delivery | 0.043 | 0.312 | 0.079 | 1.81x |
| 2,000 | Pss idle / saturated (MB) | 125 / 133 | 724 / 934 | 311 / 369 | 2.48x / 2.77x |
| 2,000 | paced post -> last client p50 / p99 | 14.9 / 23.1 | 19.7 / 28.2 | 15.1 / 19.3 | 1.01x |
| 2,000 | paced post -> a client p50 / p99 | 8.4 / 18.9 | 13.5 / 26.7 | 8.8 / 17.5 | 1.04x |
| 2,000 | saturated post -> last client p50 / p99 | 101.5 / 156.3 | 48.4 / 160.6 | 72.3 / 133.8 | 0.71x |

Reading:

- **onCrack over Rust, messages a second: 1.65x, 1.24x, 1.17x, 1.01x**; server CPU per delivery 0.62x, 0.81x, 0.84x, 0.96x. Round 4: 1.59x, 1.24x, 1.16x, 0.94x. Throughput and CPU agree (1/0.62 = 1.61, 1/0.81 = 1.23, 1/0.84 = 1.19, 1/0.96 = 1.04). **At 2,000 clients it is level**: Rust's reps are 789 / 1,054 / 1,054 and onCrack's 970 / 1,067 / 1,069, both servers use 3.8-3.9 of 4 cores, and both are bound by `sendmsg` (the R5.3 profile put 75.8% of the server's CPU in that syscall at 2,000 clients). Do not read 1.01x as a win.
- Rust's rep 1 is its lowest at every count (2,990 / 2,758 / 1,249 / 789 against medians 4,155 / 2,625 / 1,706 / 1,054); it ran first after the wait, in the session's noisiest samples (29% at or above 150%). It stays in the median, as the plan says.
- **Where Rust is clearly faster**: paced latency at 100 clients, 3.3 against 5.2 ms p50 (1.55x), and saturated post latency at 1,000 clients (19.9 against 27.9 ms p50, 1.40x). Every app's latency is higher than in round 4 (Rust 3.3 against 1.6 ms at 100 clients) because the host was busier at the session's start. Not investigated.
- **Memory**: onCrack's saturated Pss is 2.7-2.8x Rust's at every count (369 against 133 MB at 2,000 clients) and 40% of the port's (934 MB) at 2,000. R5.3 attributed it after 2,000 clients: about 89 MB of runtime mappings, 24.6 MB of anonymous memory outside the managed heap and a 217.6 MB managed heap, of which 112 MB is live (96 MB in gen2, about 48 KB per connection) and about 94 MB committed but free; a split by type needs a heap dump (`dotnet-gcdump` is not in the VM). No change was made.
- Sends per delivery: onCrack 0.330 / 0.157 / 0.102 / 0.079 against Rust's 0.622 / 0.214 / 0.102 / 0.043. Rust batches into fewer syscalls at 2,000 clients; onCrack's CPU per delivery is still level (1.79 against 1.86 us).
- The port (0.20-0.82x of Rust) and onCrack against the port (2.0-5.1x) hold round 4's picture.

### Host noise per part

Session 3: 201 samples, 7% at or above 150%, median 30%, max 390%, max load average 8.3; the noisiest part was Rust rep 1 (29%) and onCrack rep 1 (24%); onCrack rep 2 and 3 (5%, 0%). Sessions 2 and 1: 64% and 66%, parts at 80-90%. Per part: `cable/RESULTS.md`.

## 4. PR #6 reliability profiles

`bin/reliability` (PR #6, branch `pr6-reliability`, local `eed4105` with the working-tree change that adds the onCrack apps), through `bench/reliability/run` (descriptor limit 65,536, Pss sampler, load generator rebuilt from the harness, sha `4568f79e1ce2`). **overload** (64 and 256 clients on four read routes, 8 s) and **cable** (1,000 clients, 4 posters; then **cable_heavy**: 64 closed-loop posters with no limit, the harness waiting up to 60 s for every client to have every message). **3 rounds for every app**, as the plan says: Rails, Rust, C, onCrack HEAD (`oncrack`), `oncrack-cached`, and onCrack before R4.5 (`oncrack-prev`: `campfire-oncrack:r45-before`, built from `21791e2`) in one harness process (`reliability/main/`); the F# port on the cable profiles alone, 3 rounds (`reliability/fsharp/`). The port cannot take overload: the harness's contract preparation stops at `search: differs from seed SQL` (kept in `fsharp-overload-check/`; the port keeps Rails `90b3300`'s search order, upstream's contract wants message id order).

### cable_heavy: 1,000 clients, 64 closed-loop posters with no limit

| App | Rounds | Subscribed | Disconnected | Delivered to every client / posted | Messages/s | p99 post to last client, ms | Pss peak, MB |
|---|---:|---|---|---|---|---|---|
| Rails 0aa339d | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 705 of 705 / 545 of 545 / 356 of 356 | 17.4 / 24.3 / 18.5 | 37,519 / 13,754 / 15,876 | 3,259 / 3,357 / 2,864 |
| Rust f9dca47 | 3 | 1,000 / 1,000 / 1,000 | 944 / 902 / 959 | 65 of 76,602 / 64 of 68,190 / 65 of 77,958 | 4.3 / 4.3 / 4.3 | 430 / 391 / 408 | 125 / 126 / 125 |
| C cd0cbe4 | 3 | 116 / 110 / 238 | 809 / 848 / 821 | 67 of 66,217 / 24 of 58,385 / 15 of 51,202 | 4.5 / 1.6 / 1.0 | 231 / 54 / 39 | 71 / 71 / 71 |
| F# port | 3 | 1,000 / 1,000 / 1,000 | 0 / 229 / 5 | 6,305 of 6,305 / 3,375 of 5,757 / 2,092 of 6,081 | 412.4 / 222.7 / 137.0 | 666 / 831 / 749 | 2,651 / 2,591 / 2,693 |
| onCrack before R4.5 (`21791e2`) | 3 | 1,000 / 1,000 / 1,000 | 860 / 833 / 844 | 1 of 78,325 / 51 of 69,389 / 117 of 49,412 | 0.1 / 3.4 / 7.8 | 13 / 484 / 631 | 632 / 690 / 706 |
| **onCrack, fresh authorization (HEAD)** | 3 | 1,000 / 1,000 / 1,000 | **0 / 0 / 0** | **13,571 of 13,571 / 12,737 of 12,737 / 13,608 of 13,608** | **738.3 / 710.0 / 741.0** | 9,773 / 8,008 / 9,339 | 996 / 1,068 / 947 |
| onCrack, cached decision (opt-in) | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 11,761 of 11,761 / 13,725 of 13,725 / 12,988 of 12,988 | 628.5 / 737.9 / 705.4 | 10,568 / 10,215 / 9,363 | 922 / 983 / 954 |

### cable: 1,000 clients, 4 posters (the default posting load)

| App | Rounds | Subscribed | Disconnected | Delivered to every client / posted | Messages/s | p99 post to last client, ms | Pss peak, MB |
|---|---:|---|---|---|---|---|---|
| Rails 0aa339d | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 428 of 428 / 301 of 301 / 420 of 420 | 27.5 / 19.7 / 27.7 | 1,511 / 1,806 / 738 | 3,003 / 2,910 / 3,244 |
| Rust f9dca47 | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 7,608 of 7,608 / 7,799 of 7,799 / 7,605 of 7,605 | 506.7 / 519.5 / 506.8 | 49 / 45 / 41 | 100 / 100 / 99 |
| C cd0cbe4 | 3 | 344 / 285 / 95 | 918 / 940 / 876 | 43 of 62,699 / 122 of 56,812 / 181 of 79,494 | 2.9 / 8.1 / 12.1 | 49 / 165 / 36 | 73 / 71 / 71 |
| F# port | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 5,021 of 5,021 / 3,892 of 3,892 / 4,471 of 4,471 | 334.5 / 259.1 / 297.7 | 90 / 122 / 89 | 570 / 586 / 551 |
| onCrack before R4.5 (`21791e2`) | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 8,682 of 8,682 / 8,934 of 8,934 / 8,751 of 8,751 | 578.4 / 595.1 / 583.0 | 43 / 48 / 172 | 281 / 279 / 304 |
| **onCrack, fresh authorization (HEAD)** | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 9,282 of 9,282 / 9,182 of 9,182 / 9,141 of 9,141 | 618.5 / 611.7 / 608.9 | 39 / 42 / 44 | 283 / 289 / 286 |
| onCrack, cached decision (opt-in) | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 8,025 of 8,025 / 9,294 of 9,294 / 8,400 of 8,400 | 531.6 / 619.3 / 559.7 | 138 / 39 / 49 | 284 / 284 / 294 |

- **Nobody is cut.** onCrack at HEAD, fresh and cached: 0 disconnected, every posted message delivered to every client, 0 refused posts, in all 12 `cable` and `cable_heavy` runs. `oncrack-prev` (R4.5 undone) reproduces round 4's finding in a new session: 833-860 disconnected in `cable_heavy`. Rust cuts 902-959. On the default 4-poster `cable` profile onCrack runs 609-619 messages a second against Rust's 507-520 (1.21x on the medians), p99 39-44 ms against 41-49.
- **This is a difference of policy, and the table does not make it free.** Rust accepts 4,500-5,200 posts a second in `cable_heavy` and cuts the readers who cannot keep up. onCrack's pressure gate holds the posters (843-904 posts a second) and keeps everyone: an 8-10 s p99 from a post to the slowest client and about 1 GB Pss (947-1,068 MB; bounded by `CAMPFIRE_CABLE_HUB_BYTES` 1 GiB) against Rust's 125 MB. Rails keeps everyone too, at 17-24 messages a second and 2.9-3.4 GB. The port keeps all but 229 and 5 clients in two rounds and ends with posts undelivered.
- **C**: the load generator subscribed only 95-344 of the 1,000 clients on the default `cable` profile and 110-238 in `cable_heavy`; the rest are recorded as disconnected (the count includes clients closed while connecting). C also returned 195 invalid responses over three rounds at 256 clients in overload (every other app: 0). Noted as observed, **not investigated**; the C rows say nothing about cutting slow clients.
- **The F# port** on the cable profiles: 0 / 229 / 5 clients disconnected in `cable_heavy`, 3,375 of 5,757 and 2,092 of 6,081 delivered to every client in rounds 2 and 3; Pss 2.6-2.7 GB.

Overload: median requests/sec at 64 clients, 8 s per route, over 3 rounds; errors / invalid responses summed

| Implementation | Room page | Messages page | Sidebar | Search | Errors / invalid |
|---|---:|---:|---:|---:|---|
| Rails 0aa339d | 4,876 | 4,711 | 4,127 | 4,623 | 0 / 0 |
| Rust f9dca47 | 36,795 | 35,932 | 44,661 | 54,680 | 0 / 0 |
| C cd0cbe4 | 97,557 | 99,112 | 107,748 | 102,467 | 0 / 0 |
| onCrack before R4.5 | 165,545 | 220,230 | 216,686 | 207,246 | 0 / 0 |
| **onCrack, fresh (HEAD)** | 211,367 | 225,413 | 250,343 | 238,609 | 0 / 0 |
| onCrack, cached decision | 215,544 | 238,084 | 258,824 | 247,413 | 0 / 0 |

At 256 clients, same form:

| Implementation | Room page | Messages page | Sidebar | Search | Errors / invalid |
|---|---:|---:|---:|---:|---|
| Rails 0aa339d | 5,087 | 4,498 | 4,928 | 5,269 | 0 / 0 |
| Rust f9dca47 | 35,985 | 35,420 | 56,294 | 48,064 | 0 / 0 |
| C cd0cbe4 | 89,202 | 96,323 | 109,829 | 104,824 | 0 / 195 |
| onCrack before R4.5 | 169,272 | 179,716 | 216,873 | 196,527 | 0 / 0 |
| **onCrack, fresh (HEAD)** | 196,107 | 218,411 | 257,084 | 242,023 | 0 / 0 |
| onCrack, cached decision | 199,882 | 233,804 | 269,079 | 247,644 | 0 / 0 |

- Round 4's overload rows for onCrack HEAD were lower than the previous image's and I read that as the host. This session has HEAD above the previous image (211k against 166k at 64 clients on the room page), 3 rounds each, on a host at 10% noisy samples.
- **Host noise (rule 2):** `main` 38 of 375 samples (10%) at or above 150%, `fsharp` 5 of 38 (13%): both under the 25% line. Round 4's reliability session was 85% noisy and incomplete; this one is neither.
- **One disturbance, recorded in `reliability/RESULTS.md`.** At 04:09:32 the VM's disk guard (the Mac at 11.9 GiB; another project's Go build cache at 7 GiB) killed the session's wrapper subshell but not the harness (`ruby bin/reliability`), which ran on, as in round 4. The runner took the session for stopped, ran `go clean -cache` (no go process running) at 04:09:39, tried to start a second session (the harness's benchmark lock refused it; nothing ran) and attached a new guard to the harness's own pid. The session lost two minutes of its wrapper's host-load loop and its automatic JSON copy (copied by hand). `go clean -cache` ran during Rust's round 2 overload. `main/` is rounds 1-3 as one harness process wrote them; nothing was dropped or re-run. `session.sh` now stops the harness when its guard fires.
- Setup: round 4's three fixes plus a fourth: the harness workspace needs `once-campfire-oncrack-prev` as a symlink to the `oncrack-r45-before` worktree.

## 5. Size

KLOC by upstream's rule (`docs/performance-review.md`, "Application source size": nonblank, noncomment backend application code, executable template code included, `cloc 2.10 --by-file --skip-uniqueness`; tests, vendored code, generated files, benchmark and parity tooling, static data and build scripts are out). `cloc` is upstream's own `cloc-2.10.pl`; Rust's inline `#[cfg(test)]` code is stripped with `syn 2.0.119`; Rust's templates go through upstream's `template_code.rb`.

| Implementation | Revision | Backend code | Template code | **KLOC** | KLOC with static data left in |
|---|---|---:|---:|---:|---:|
| Rails | `0aa339d` | 4,443 | 1,054 | **5.5** | 5.5 |
| Rust | `f9dca47` | 30,090 | 873 | **31.0** | 35.1 |
| C | `cd0cbe4` | 94,910 | 0 | **94.9** | 108.4 |
| F# port | `2e6c08e` | 38,180 | in the code | **38.2** | 42.5 |
| onCrack | `ee5a2e9` | 41,898 | in the code | **41.9** | 46.2 |

- Both F# counts include the html5ever tokenizer port (`src/Campfire.RichText/Html5ever`, 3,582 lines), first-party F# where Rust takes `html5ever` as a vendored crate (not counted for Rust). Without it the port is 34.6 and onCrack 38.3.
- onCrack is 3.7 KLOC (9.7%) larger than the port (the caches, the writer, the Cable log and its bounds, the fresh-check pool), 35% more than Rust's 31.0 and 44% of C's 94.9. The port is 23% more than Rust's.
- **Calibration**: the method reproduces upstream's published Rails figure to the line (4,443 backend, 1,054 template) and the Rust templates exactly (873); Rust's backend lands +1.0% (30,085 against 29,784 at `6838ead`) and C's +0.1% (94,910 against 94,816 at `ddaafaf`). Read Rust's and C's counts as within 1% of upstream's own tooling, not exact. The F# counts apply the same exclusions to the same kinds of file; they are my selection.
- **Definition change.** Round 3 counted every handwritten F# line (onCrack 44.6, port 42.5). The headline now excludes the static-data tables upstream's rule excludes (6 F# files; 4 Rust; C's Marcel table) and shows the all-code figure beside it. onCrack's all-code count grew 1.6 KLOC in rounds 4 and 5 (44.6 to 46.2); the port's did not change. This also closes round 4's open item 5.

## 6. Deviations from PLAN.md, stated

1. **Sessions per profile.** The plan says two; rule 2 re-runs a NOISY session once. Normal-2 and mixed-2 were NOISY, so each profile ran three, all pooled (rule 3). The headline therefore carries four NOISY sessions out of six; the per-session table is the check, and the two-session cut is shown beside it.
2. **`--routes`** was omitted from PLAN.md's command (above); the first normal session ran eight routes, was set aside whole and re-run with the five.
3. **normal-2's sampler gap** (rule 1 asks for samples every 10 s; 45% of that session has none).
4. **Cable: three sessions, not one**, and the headline is session 3 alone (section 3).
5. **Pixel gate**: three harness faults and a breach of the Mac's 12 GiB floor (section 1).
6. **Reliability**: the guard killed the wrapper and not the harness once (section 4).
7. **Climb log**: the cached rows are third attempts. The first two attempts of each cached configuration ran while other projects loaded the host (load average 40-100); the selection rule, fixed before attempt 3, was to log the attempt with the fewest noisy-host flags (then the fewest unsettled warm-ups). The unlogged attempts stay in `oncrack-r5-climb/`. The climb spec said to log the round 4 final image; the task text said round 5 HEAD; no round 4 image was measured. The round 5 image is the existing `campfire-oncrack:app`, since `git diff ee5a2e9..3e6a300` over `src`, the Dockerfile, `global.json` and the props files is empty.
8. **Disk**: three more breaches of the 12 GiB floor across the gate, cable session 2, reliability and the climb, each from another project's `~/Library/Caches/go-build` (3-12 GB, regrowing about 3 GB in minutes). Each time `go clean -cache` ran only when no go process was running; nothing of this project's was deleted outside its own build output and the VM's images.

## 7. What round 5 changed, and what it did not

Round 5 started from round 4's Open list. Nothing in `src/` changed for the HTTP read path, the database, the writer or the post's commit; the changes since round 4's measured commit `ea1f85b` are `Campfire.Cable` (`Pubsub.fs`, `Socket.fs`, `Connection.fs`, `Config.fs`, `Trace.fs`, `BenchFlip.fs`) and one bench-only hold setting in `Broadcasts.fs`.

- **The message that did not reach every client (round 4, open item 1): found, fixed, covered.** The cause was on the server and it was not a lost frame: one client got a frame of the right length whose payload was NULs and pieces of other objects. Round 4's gathered write (`Sendmsg.pin`) pinned each payload with one `fixed` local and recursed in tail position; F# compiled that to a loop with one pinned slot, so during `sendmsg` only the last payload of each batch was pinned and a compacting gen1 collection could move the others under the kernel. `Sendmsg.pinFrom` pins eight payloads per stack frame with a non-tail recursive call. A test forces a compacting collection just before the `sendmsg`: on round 4's code 620 of 640 payloads moved, on the fix 0, and with the call put back in tail position 480 of 640. 105 target phases after the fix lost or corrupted nothing; the cost is 1.004x CPU per delivery (the 1,000-client throughput comparison was inconclusive under host load, so the claim that gathered writes still beat copying is not made here).
- **The memory bound (round 4, open item 8): closed.** The hub's total now counts what some subscriber has yet to read, in every chunk of every log, including a group's newest; over it `Hub.Shed` compacts every log, then cuts the subscribers with the most unread bytes. A client that reads is never cut. The tests that show the old gap (37,177,056 bytes retained at a 32 MiB total, nothing cut; 193 groups still alive after 20 s) run against round 4's code. 1,000 clients, 6 rotated rounds: 1,626 against 1,431 messages a second, 2.34 against 2.58 us per delivery, Pss 292.5 against 295.5 MB, median per-round CPU ratio 0.958 (host busy; read it as "no regression").
- **The round 5 verifier** found three defects in the reader protocol R5.2 introduced (an emptied slot read as a null frame; a reader crossing into a new chunk read as a whole chunk further behind, 1.2% of looks on macOS, 5,313 of 10.4 million on Linux; an unordered store on ARM64) and a leak of up to 256 held messages in the gather scratch after a failed write. All fixed, each with a test that fails before. It also fixed the Cable suite's timing: none of 10 full Linux runs were green before; macOS 10 of 10 afterwards and Linux 2 of 3.
- **The fan-out at 2,000 clients (round 4's 0.94x): R4.5 did not cost the lead; there was no lead to lose.** R5.3 ran the A/B three ways (per-arm restarts; an in-process flip switch; a Rust control) and profiled with perf: 75.8% of server CPU at 2,000 clients is the `sendmsg` syscall (copy 23.4%, loopback receive softirq 19.2%, page and memcg charge 13.5%), reading the log costs about 3% in user space. Default and old ring order are unresolved to about 10%. `MaxWriteBatch` 128 equals 64; `CAMPFIRE_CABLE_HOLD_US` 3000 gave +12-21% at 2,000 clients in 5 of 6 clean pairs, nothing at 1,000, and 6-52% slower at 100: no single value wins everywhere, so no default changed. A hold scaled to the number of subscribers is the lead with an effect beyond the spread, and is untried.

## 8. The climb chart's project suite (rounds 3 and 5, tier 3, 3 reps, over pinned Rust `ccece30`)

Four rows logged in `oncrack-log.jsonl` with `mode` and `round`; one session each, c=16 requests a second (CPU us per request in brackets):

| Workload | round 3 fresh | round 5 fresh | round 3 cached | round 5 cached |
|---|---|---|---|---|
| room page | 147.9k (21.2) | 166.3k (19.3) | 176.9k (17.5) | 172.1k (18.2) |
| messages page | 154.7k | 173.5k | 185.3k | 184.6k |
| sidebar | 166.1k | 187.7k | 197.1k | 194.4k |
| search | 161.1k | 184.1k | 191.4k | 190.7k |
| post a message | 11.5k (188.4) | 9.9k (213.8) | 8.1k (180.9) | 11.1k (205.5) |

- Fresh reads gained 1.12-1.14x at c=16 from round 3 to round 5; cached reads are level within 3%. So the gain is fresh authorization getting cheaper (R4.3's held read transaction), not the cached path getting faster. This matches the harness: fresh/cached in the hand re-runs is 1.03x for a room page.
- **Post a message went the wrong way in all four rows** (CPU 213.8 against 188.4 us fresh; 205.5 against 180.9 cached). Two post-only cross-checks do not settle it: in the quieter one round 5 read 188.8 us against round 3's 187.4; in the other, host noise hit round 5 (519 us). The hand re-runs' quiet sets read 194.9 us. Rounds 4 and 5 touched the post path (R4.4's WAL-frame counters, R4.5's pressure gate and log); I did not attribute a cost. Open item 2.
- `bench/progress/climb.py` reads one mode (`CLIMB_MODE`, default cached; rows without `mode` count as cached). The page rebuild must pick fresh explicitly, or fresh and cached rows of the same commit merge into one dot.

## Open

1. **No quiet repeat of the harness headline.** 3.76x (both profiles) pools four NOISY sessions of six; per-session figures run 2.11x-4.74x over Rust (normal) and 3.00x-6.33x (mixed), 1.41x-3.81x over C. The plan's session budget is spent. A reading that cannot be disputed needs a Mac with nothing else on it (the Erlang VMs and Go tests of other projects are what made these sessions noisy); until then quote the range and the CPU per request.
2. **Post path: 12-14% more CPU per post than round 3 in the climb suite, unresolved.** Needs a quiet-host in-process A/B of the post path between `37c5988` and HEAD. The pooled post throughput (8,726 req/s, range 850-13,732) is dominated by the shared disk, not by the app.
3. **Fan-out at 2,000 clients is level with Rust (1.01x), and paced latency at 100 clients is 1.55x Rust's.** Both servers are bound by `sendmsg`. A hold that scales with the subscriber count is the one untried lever; the 100-client latency was not investigated.
4. **Memory is 2.4-2.9x Rust's in the cable suite and about 1 GB in `cable_heavy`** (bounded by the 1 GiB total). The managed heap at 2,000 clients holds about 94 MB committed and free; a split by type needs `dotnet-gcdump` in the VM.
5. **The memory bound's known limits**: the total is checked at most every 10 ms (what is published between can exceed it); a cut frees the log at once but the socket closes up to 1 s later; a group's fixed cost and each connection's pending batch sit outside the total; frames are still copied once per identifier variant. Payload sharing between variants was considered and not taken (it leaves a floor per group and changes the gather path the lost-frame fix just repaired).
6. **"No lost messages" is statistical.** 140 cable phases, 105 post-fix target phases, 31 verifier phases and 12 `cable`/`cable_heavy` runs delivered everything to everyone; the deterministic test (Linux only, in `bin/linux-tests Cable`) is what guards a regression. The Linux Cable suite was green in 2 of 3 verifier runs and once in the gate (118 of 120); a timing test may still flake.
7. **Not investigated**: C's connection counts on the cable profiles (95-344 of 1,000 subscribed) and its 195 invalid responses at 256 clients; the F# port still fails the overload contract (search order), so it has no overload row.
8. **The pixel gate's harness faults** (the 30 s stylesheet wait, the "Response has been disposed" crash, the 40-minute hang) are upstream harness behaviors; each passed on re-run and none was a pixel difference, but a clean first-pass gate was not obtained.
9. **Durability** was not re-measured: the default is Rails-equivalent (WAL, `synchronous=NORMAL`, every write committed before it is answered), and nothing in the database or writer changed in round 5. The last kill -9 runs are round 3's (4 runs, 0 lost, 0 duplicated).
10. **Publishing is the operator's**: nothing was pushed. The page was rebuilt from this file and the data (round 5 final review, below); the repo, its About section, Pages and the PR are not done.

## Review (round 5 final)

A skeptical read of the gates, the sessions and the reports, after the run.

- **What I checked from raw files.** The 486 harness cells: 0 errors and 0 invalid responses; 108 audits, all `verified`; 224,402,307 responses and 2,762,229 acknowledged writes recomputed and equal to `totals.md`; `pool.py` reproduces `pooled.md`. Image ids and `dirty: False` for every app in each session's metadata (the same `bfcbb4633485` for `oncrack` and `oncrack-cached`). Every `cable_heavy` row and the onCrack throughput cells against `reliability/*/harness-output`. The cable phases for 140 phases. `git diff 6abc183 HEAD -- src` empty. All R5 final commits since `5895335` carry the required `Co-Authored-By: Claude Opus 5.5` trailer and none has a claude.ai link or session trailer.
- **What I corrected**: the mixed-1 start time in `RESULTS.md`; the headline wording. The runners' summaries called the headline a point value ("3.76x"); the data supports a range, so the verdict says so and shows the first-two-session cut, which the task's wording asked for ("over two sessions each") and PLAN rule 3 does not provide.
- **The fresh-over-cached ratios (0.90x, 0.83x) are noise**, not a finding: same image, one lookup apart, and the hand re-runs put them level.
- **The CPU-per-request explanation is untested.** The runner and I both read "round 4's Rust and C numbers came from a quieter host"; round 4's quiet sets did give lower Rust and C CPU (70.1 and 48.4 us) than this round's quiet sets (75.6 and 54.1), which is consistent with it, but a same-host rerun of round 4's code was not made.
- **Reliability is a policy comparison.** Rust's cut clients are a choice of what to protect (post throughput), not a failure to finish; the table shows both sides (posts a second, p99, Pss).
- **The pooled post number is not a regression finding**; the hand re-runs' quiet sets and the climb suite disagree by 12-14% in one direction without a clean A/B (open item 2).
- **Not reviewed again**: the source of the lost-frame fix and the memory bound; the verifier covered them and its report is `oncrack-r5-verifier.md`.

## Final review (round 5, the project's last)

A last skeptical pass over round 5's commits (`c16820f..HEAD`), this report's numbers and the rebuilt page.

- **Correctness.** Read the round's `src/` diff: only `Campfire.Cable` (`Pubsub.fs`, `Socket.fs`, `Connection.fs`, `Config.fs`, `Trace.fs`, `BenchFlip.fs`) and the bench-only hold in `Broadcasts.fs`; nothing in the database, the writer, the read cache or authorization, so durability and cross-user isolation are round 3's and round 4's, unchanged. `Sendmsg.pinFrom` keeps eight `fixed` locals a frame with the recursive call out of tail position (the JIT does not tail-call a method with pinned locals either). The verifier's reader protocol (one absolute slot, written with release after the frame is read; `Compact` frees only below the lowest slot seen with acquire; an emptied slot reads as the cut) cannot hand a reader a frame it has not reached, nor skip or reorder one. `BenchFlip` reads nothing unless its variable is set. **"No lost messages" is now supported**: the cause is understood from the IL, a deterministic test fails on round 4's code and passes now, and about 120 onCrack phases at the default settings after the fix (R5.2's 45, the verifier's 31, the final cable sessions' onCrack phases) lost nothing where round 4's code lost a message in 3.6% of phases (0 in 120 at that rate has a probability near 1%), with 0 moved-array reports in 60 verify-on phases against 52 of 52 before. It stays a statistical claim plus a regression test (open item 6).
- **Numbers, two cells spot-checked from the harness's own files.** The pooled headline recomputed from each session's `summary.json` / `mixed-summary.json` (not the converted per-app files `pool.py` reads): normal 3.76x Rust, 2.40x C, 5.25x port; mixed 3.76x, 2.26x, 6.78x, 9 rounds a cell. Cable session 3 from `t3/*.json`: 1,000 clients Rust 1,249 / 1,706 / 1,724 and onCrack 1,925 / 1,995 / 2,002; 2,000 clients Rust 789 / 1,054 / 1,054 (1,054.5) and onCrack 970 / 1,067 / 1,069. Both match. **The point estimate is the weakest number here**: it rose from round 4's 3.29x with no HTTP-path change, and the quiet normal session reads 2.11x; the range and CPU per request (3.75x Rust, 2.68x C on the quiet sets) are the claim.
- **Page corrections** (`site/build.py`, sourcing check passes, 1,263 ledger rows): the climb caption and round three's beat now say round three's two dots were measured in round five and placed at round three's close (the clock under them is round three's, not when they ran); the caption names the dotted fresh join as not a measurement and the fork as the port's final re-baseline (the port's line has a later dot); the fan-out "every rep above every rep" names the one quiet session; "Memory is bounded" became "Cable's backlog is bounded", with the cut rule; the Check-it tiles say the 13 attack tests and the 3.04 load-generator cores are round one's. Checked in cmux at 1280 and 375 px, light and dark.
- **Commit trailer**: the page commit carried a Sonnet trailer; amended (unpushed) to the required Opus 5.5 trailer.

## History: every round's headline and what changed in it

For the page's iteration beats. Ratios are not comparable across rows without their column: rounds 1 and 2's early figures divide by the pinned Rust `ccece30` on this project's own suite; from round 2's final run they divide by current Rust `f9dca47` and C `cd0cbe4` on upstream's harness. Numbers are each round's own closing report, as written then.

| Stage (dates) | What changed | Headline at its close | Gate |
|---|---|---|---|
| **Port, phases 0-5** (2026-10-05/06) | The Rust workspace translated crate by crate to F# on ASP.NET Core and Falco: scaffold and plan (0); Ruby, RailsCompat, Routes, Assets (1); Db, RichText, Storage (2); Kit core, front server, Cable (3); the views (4); the app: boot, account controllers, the hot path, channels and integrations (5). | Phase 5b baseline: 0.68-0.79x Rust on the four reads at 16 connections, 1.02x on posts, 20-92x Rails. | ported vectors and tests per crate; the image boots under the parity candidate |
| **Port, phases 6-7** (10-06/07) | Parity loop, then tuning units 7.1-7.5 against Rust's profile (signed-cookie requests, identity bodies, Db row reads, rich text, plain-frame Cable fan-out). Phase 8 (Datastar) dropped; published as ckluis/once-campfire-fSharp (PR #1, fork point `0ae3436`). | `phase7-final`: **1.24-1.33x Rust** at 16 connections (1.22-1.31x at 64, 1.07-1.29x at 1) with 0.77-0.92x of Rust's CPU per request; Cable fan-out 0.60-0.80x. | parity harness |
| **onCrack round 1** (10-07/08) | The brief: same pixels, unhinged work per request. C0 instruments; C1 versioned read cache (per-room and per-user counters bumped by TEMP triggers, page cache, authentication through the cache); C2 group commit (up to 64 writes, one COMMIT) and a post broadcast in commit order; C3 Content-Length on gzipped answers (search was already cached); C4 Native AOT, shipped as an opt-in; four verifier findings fixed. | **3.84x Rust, 2.89x the port** at c=16 (2.06x at c=1, 4.54x at c=64), a 100%-cache-hit result. | 940 / 940 pixels |
| **onCrack round 2** (10-08/09) | R2.0 made the benchmark honest (realistic workloads that write while they read); R2.1 Cable writes its own socket (probe and pong, WakeBatch); R2.2 posting work cut with Rails' durability kept; R2.3 a front-server fast path; R2.4 one connection; R2.5 memory and cold start; the verifier's seven findings fixed (a critical one; the WAL index watch). Ended against upstream's own harness and current Rust, C, Rails. | **3.25x Rust, 2.37x C, 3.93x the port** (normal), 3.64x / 2.36x on mixed reads, with the cached decision (not upstream's contract). | 940 / 940 round 1; a 252-screenshot targeted gate after the fixes |
| **onCrack round 3** (10-09) | R3.1 the full gate on the final code; R3.2 **fresh authorization on every cache hit became the default** (upstream's contract; the cached decision kept as an opt-in); R3.3 search ordered by message id as upstream's; R3.4 the WAL-restart stall traced to the VM's disk (default unchanged; a 250 ms checkpoint of a quiet WAL). | Fresh: **2.59x Rust, 1.86x C, 3.82x port** (normal, two sessions pooled; sessions 2.68x and 3.33x); mixed 3.31x / 2.06x; CPU per room page 2.72x Rust, 1.89x C. | 940 / 940 |
| **onCrack round 4** (10-10) | R4.0 the one failing attack test was the test browser's cookie jar; R4.1 a raw epoll cable client that measures the server (and a window, since a client that keeps up laps the rings); R4.2 gather writes (`sendmsg`); R4.3 the fresh check holds a read transaction (-7.7% CPU on a room page); R4.4 WAL volume (nothing shipped); R4.5 Cable reliability: a byte-bounded shared log, publish order across streams, stall rather than slowness, a posting gate; the verifier's four defects (one member could stall every poster 2 s; no total memory bound; revoked clients got later frames; untested gate). | **3.29x Rust, 2.40x C, 4.01x port** (one session); CPU per room page 3.25x Rust, 2.02x C; fan-out 1.59 / 1.24 / 1.16 / **0.94**x Rust (the "ahead at every count" sentence withdrawn); PR #6 incomplete: onCrack the only app to keep all 1,000 clients in `cable_heavy`. Two open defects: one message of 34,741 missing; a memory gap. | 102 targeted screenshots |
| **onCrack round 5** (10-10..13) | R5.1 the missing message traced to the server (corrupted payload, not a lost frame); R5.2 the gather pinned only the last payload per batch: `pinFrom` fixes it, and the hub's total now reaches every chunk and cuts the furthest behind; R5.3 the 2,000-client fan-out profiled (75.8% in `sendmsg`), the hold and batch knobs kept nothing; the verifier fixed three reader-protocol defects and a scratch leak and made the Cable suite's timing honest; the final gates and runs (this report). | **3.76x Rust, 2.40x C, 5.25x port** (normal), 3.76x / 2.26x / 6.78x mixed, across sessions of 2.1x-4.7x; CPU per room page 3.79x Rust, 2.93x C; fan-out 1.65 / 1.24 / 1.17 / **1.01**x Rust; PR #6: 0 of 1,000 clients cut in 3 of 3 rounds; 41.9 KLOC (Rust 31.0, C 94.9, port 38.2). | **944 / 944**; `bin/verify` 1,187 passed, 0 failed |

Beats worth telling from this: the benchmark was made honest twice (round 2's writing workloads, round 4's load generator that stopped being the limit), and each time onCrack's number moved down before it moved up; the round-1 multiple was a 100%-hit result; the default stopped being the fast mode in round 3 (fresh authorization) and the cost of that was then bought back in round 4; and the one correctness doubt that survived round 4 (a message that did not reach a client) was a compiler turning a recursion into a loop, found by reading the IL.

## Commits

All on branch `crack`, nothing pushed: `ee5a2e9` plan; `db9f576`, `61bab8f`, `7101059`, `826acd7` gates; `9f25013` to `e285a1a` the harness sessions and hand re-runs; `567431d` to `2b3ab3f` the cable sessions; `f423aeb`, `cb1f952`, `3e6a300` reliability; `d75740b`, `86a09fa` the climb log; and this report with `pool-subsets.py`, `pooled-subsets.md` and the `RESULTS.md` correction.
