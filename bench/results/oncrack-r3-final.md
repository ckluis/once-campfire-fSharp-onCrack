# onCrack round 3, final run: upstream's harness against current Rust and C, on the final code, 2026-10-09

The closing measurement of round 3. It runs the checks and the numbers on the code the round ends with (`191c468`; `git diff 191c468 HEAD -- src` is empty), with upstream's harness (`once-campfire-verification`, local adapter commit `a05b344`), in the one VM boot that has run the whole round (up since 10:44 EDT). Nothing was pushed.

- Report: `/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r3-final.md`
- Data and scripts: `/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r3-final/`
- The rules for the headline were fixed before any session ran: `oncrack-r3-final/PLAN.md` (commit `8c16a7e`).
- Page: `/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/index.html`, from `python3 site/build.py`. Its sourcing check passes (889 numbers in the ledger).

## Verdict

**Fresh authorization, upstream's harness, 16 clients, the final code.** Fresh is onCrack's default and the only mode that meets upstream's contract. Geometric means of the pooled medians, six rounds per cell (two sessions of three):

| | over Rust `f9dca47` | over C `cd0cbe4` | over the F# port |
|---|---:|---:|---:|
| Normal profile, five workloads | **2.59x** | **1.86x** | **3.82x** |
| Mixed profile, four reads | **3.31x** | **2.06x** | **4.95x** |
| Cached decision (opt-in), normal | 2.97x | 2.13x | 4.37x |
| Cached decision (opt-in), mixed | 3.95x | 2.46x | 5.89x |

- **The pooled normal figure is below both sessions'** (2.68x and 3.33x over Rust): the second session ran every engine at about half speed, and a six-round median lands between the two regimes at a different point per engine (section 2, "Each session alone"). It understates. The quiet session alone gives 2.68x Rust and 1.85x C. **The mixed figure leans the other way:** its quiet session reads 3.10x Rust and 1.83x C against the pooled 3.31x and 2.06x. *(Added by the final review.)*
- **CPU per request agrees and is the steadier number.** Each engine's CPU per request times its throughput comes to 2.6-3.4 busy cores of the 4 in all 60 hand re-run windows, so the two measures are consistent. From the container's cgroup, median of five hand re-runs each: a room page costs onCrack 23.0 us, Rust 62.6 and C 43.5, so Rust spends 2.72x and C 1.89x onCrack's CPU. Mixed reads: 21.7 against 62.3 and 49.5 (2.87x, 2.28x). A post: 200 us against 494 and 673 (2.47x, 3.36x).
- **Against R3.2** (2.83x Rust, 2.07x C, 3.67x the port; mixed 3.39x, 2.04x): the same mode on an earlier build, on a different and differently busy afternoon. The gap (2.59x, 1.86x) is inside the spread this host gives, so I claim no change in either direction. Round 2's cached-decision headline was 3.25x and 2.37x; that mode reads 2.97x and 2.13x here on the same noise.
- **Everything was validated.** 156,621,852 timed responses passed the full content contract, 1,899,793 acknowledged writes were audited against the messages, rich-text and search-index rows, and there were 0 errors or invalid responses across 648 raw samples. The hand re-runs add 60 validated windows and 5,030,671 audited posts.
- **The checks pass, with one thing I could not close:** a single failure of the verifier's A7 attack test in 18 full runs, not reproduced (see "Open").

## 1. The checks

Run on `191c468` before the sessions (commit `8c16a7e`). The attack suite was run again afterwards, after two test fixes.

| Check | Result | Where (under `oncrack-r3-final/`) |
|---|---|---|
| `bin/verify`, `CAMPFIRE_REQUIRE_SEED=1` | 1,144 tests, 0 failed | `logs/verify-part1.log`, `logs/verify-part2-app.log` |
| `bin/db-differential` | 4 of 4; schema identity; the reference reads the F#-written database; rollback ok | `logs/db-differential.log` |
| The round 2 verifier's `foreign.py`, both modes | Identical in fresh and cached: 15 of 17 cases true at once and after 1.5 s (renames, body, creator, boosts, timestamps, session deleted and rotated, membership deleted, stale `If-None-Match`, a search edit Kevin can find). The other two read false in Rails and Rust too and are not defects: `user_deactivated` (status edited alone) and `search_body_edit` (it searches a word no message contains) | `foreign-fresh.jsonl`, `foreign-cached.jsonl` |
| `memflood.py` | 20,000 distinct 7 KB URLs, 40,000 requests, 0 non-200; anonymous memory 22 to 101 MB (round 2: 103) | `memflood.jsonl` |
| `killtest.py`, kill -9 under load, 4 runs (the 4th with `CAMPFIRE_WAL_DEFER=on`) | 7,735 / 34,888 / 105,415 / 84,057 acknowledged posts; 0 lost, 0 duplicated, 0 acknowledged without a search-index row; the room page after restart shows the newest post; WAL mode | `logs/killtest.log` |
| Attack suite (11 tests) after the test fixes | Cached mode 11 of 11. Fresh mode 10 of 11 in the kept log (A7, one failure, below). 16 more full runs (6 fresh, 4 cached, 6 fresh under CPU saturation): 11 of 11 each | `logs/attack-tests-r3-default.log`, `logs/attack-tests-r3-cached.log`, `logs/attack-repeat/` |
| `bin/pixel-parity --fast --only`, the search and posting states | 82 of 82 pixel-equal (posting/default 66, search/default 14, search/custom_styles 2); 0 different, 0 not captured | `pixels-fast.json`, `logs/pixel-posting.log`, `logs/pixel-search.log` |
| Full pixel gate, run in R3.1 on the code before R3.2-R3.4 | 940 of 940 | `bench/results/oncrack-r3-pixels.md` |

The pixel states are the ones round 3 touched: search (R3.3's order) and posting (the post path under fresh authorization and R3.4's writer work). I did not re-run the full gate; the units after it changed authorization checks, one query's order and the writer's checkpoint policy, and the targeted gate covers the pages those reach.

### Two stale attack tests, fixed (test code only)

The first pass of the round 2 suite on the final code failed two tests. Both asserted round 1's design, not a defect:

- **A2** (version cells for room ids nobody has) reflected on a `ConcurrentDictionary` that round 2 replaced with a fixed array of 65,536 stripes. It now sends 40,000 distinct ids that share one stripe, asserts the table grew by under 1,000 cells (it grew by 1: 0 to 1) and never exceeds the stripe count.
- **A6** (ETags stay per user) expected no 304 for another user's ETag on the messages pages. Round 2 gave those pages Rack::ETag's content digest, as upstream has (`oncrack-r2-verifier.md`, finding 3), so two members who see the same page share its ETag. The test now allows that for the content-ETag pages only, and adds the guard that matters: David's real ETag sent for a room that does not exist must not answer 304 or 200. It passes (authorization runs before the 304).

The edits are in `bench/results/oncrack-verifier/AttackTests.fs`. They change nothing the harness or the app reads.

## 2. The numbers

### Method

- Per session: `bin/benchmark --rounds 3 --duration 8 --concurrencies 16 --cpus 0-3 --client-cpus 4-7 --apps rails,rust,c,fsharp,oncrack,oncrack-cached`. Normal routes `room_show,messages_page,sidebar,search,post_message`; mixed adds `--mixed-write-rate 10` with the four read routes.
- `oncrack` is the shipped default (`CAMPFIRE_FRESH_AUTH` on): the headline. `oncrack-cached` is the same image with `CAMPFIRE_FRESH_AUTH=0`: the opt-in, shown beside it. Both set `CAMPFIRE_RESPONSE_CACHE_MB=64`.
- Four sessions in one VM boot, the same images, seed and load generator in all (`tables.md` has every digest: seed sha256 `4381b911d1c5`, load generator `351a66af1ea1`, onCrack image `69deaa8cdf60` labelled `191c468cf72a`, built from the clean worktree `/Users/clank/Desktop/projects/oncrack-measured`). Times (EDT): normal-1 15:54-16:11, mixed-1 16:21-16:35, mixed-2 16:48-17:02, hand re-runs A-E 17:08-17:52, normal-2 19:55-20:27.
- Pooling, by `PLAN.md`: each cell's median over all rounds of both sessions of its profile. No session is dropped.
- Disk guard (stop a session under 12 GB free on the Mac): the lowest free space during a session was 13, 13, 13 and 21 GB. Before this report `bin/clean-docker` and `bin/clean-parity` ran; the Mac then had 19 GB free.
- Tables: `pool.py` (pooled, `pooled.md`), `table.py` (each session alone, in upstream's document form with median, min-max, responses validated, writes audited, generator CPU, p50 and p99, and image digests: `tables.md`) and `totals.py` (`totals.md`).

### Normal profile, pooled

Median requests/sec of 6 rounds (2 sessions x 3) [min-max], 16 clients. Sessions: normal-1, normal-2

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| **onCrack, fresh authorization (default)** | 101,854 [52,285-134,892] | 109,301 [83,220-139,167] | 121,627 [90,646-161,502] | 116,437 [81,896-158,686] | 9,498 [4,385-14,966] |
| onCrack, cached decision (opt-in) | 125,900 [42,017-172,818] | 126,534 [98,510-178,751] | 147,264 [88,120-194,138] | 133,576 [94,078-186,747] | 9,382 [3,458-14,587] |
| Rust f9dca47 | 45,222 [22,315-50,525] | 36,259 [12,304-47,362] | 38,336 [19,601-55,424] | 43,320 [24,036-56,556] | 4,676 [2,290-6,484] |
| C cd0cbe4 | 57,925 [33,540-75,643] | 60,225 [29,140-78,426] | 63,723 [31,041-82,479] | 66,887 [30,426-81,908] | 4,494 [1,894-5,806] |
| F# port | 21,347 [6,660-35,778] | 24,754 [11,402-42,208] | 23,936 [11,153-38,323] | 22,998 [10,627-32,536] | 6,330 [3,100-9,192] |
| Rails 0aa339d | 4,904 [3,098-5,293] | 4,762 [2,191-5,060] | 5,032 [3,547-5,436] | 3,561 [2,360-5,428] | 320 [254-380] |

| Ratio of medians | Room page | Messages page | Sidebar | Search | Post a message | Geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 2.25x | 3.01x | 3.17x | 2.69x | 2.03x | **2.59x** |
| oncrack / c | 1.76x | 1.81x | 1.91x | 1.74x | 2.11x | **1.86x** |
| oncrack / fsharp | 4.77x | 4.42x | 5.08x | 5.06x | 1.50x | **3.82x** |
| oncrack / rails | 20.77x | 22.95x | 24.17x | 32.70x | 29.67x | **25.68x** |
| oncrack / oncrack-cached | 0.81x | 0.86x | 0.83x | 0.87x | 1.01x | **0.87x** |
| oncrack-cached / rust | 2.78x | 3.49x | 3.84x | 3.08x | 2.01x | **2.97x** |
| oncrack-cached / c | 2.17x | 2.10x | 2.31x | 2.00x | 2.09x | **2.13x** |
| oncrack-cached / fsharp | 5.90x | 5.11x | 6.15x | 5.81x | 1.48x | **4.37x** |
| c / rust | 1.28x | 1.66x | 1.66x | 1.54x | 0.96x | **1.39x** |

### Mixed profile, pooled

Median requests/sec of 6 rounds (2 sessions x 3) [min-max], 16 clients. Sessions: mixed-1, mixed-2

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| **onCrack, fresh authorization (default)** | 122,314 [95,860-132,852] | 140,255 [124,520-144,262] | 146,126 [134,538-152,031] | 142,576 [92,917-153,951] |
| onCrack, cached decision (opt-in) | 140,225 [114,850-157,060] | 168,572 [157,228-183,498] | 176,433 [171,762-180,975] | 172,525 [165,735-182,067] |
| Rust f9dca47 | 40,086 [36,138-44,111] | 38,007 [32,884-41,826] | 44,834 [38,964-53,838] | 43,451 [41,185-53,540] |
| C cd0cbe4 | 63,643 [44,981-70,243] | 65,492 [54,012-71,568] | 68,254 [57,876-79,417] | 69,494 [46,980-78,659] |
| F# port | 25,832 [21,542-32,532] | 29,333 [22,808-40,009] | 28,207 [20,902-36,142] | 27,876 [23,414-31,550] |
| Rails 0aa339d | 1,872 [1,422-2,772] | 2,337 [2,056-3,628] | 3,565 [2,500-4,408] | 3,012 [2,316-3,607] |

| Ratio of medians | Room page | Messages page | Sidebar | Search | Geometric mean |
|---|---:|---:|---:|---:|---:|
| oncrack / rust | 3.05x | 3.69x | 3.26x | 3.28x | **3.31x** |
| oncrack / c | 1.92x | 2.14x | 2.14x | 2.05x | **2.06x** |
| oncrack / fsharp | 4.73x | 4.78x | 5.18x | 5.11x | **4.95x** |
| oncrack / rails | 65.33x | 60.03x | 40.98x | 47.34x | **52.52x** |
| oncrack / oncrack-cached | 0.87x | 0.83x | 0.83x | 0.83x | **0.84x** |
| oncrack-cached / rust | 3.50x | 4.44x | 3.94x | 3.97x | **3.95x** |
| oncrack-cached / c | 2.20x | 2.57x | 2.58x | 2.48x | **2.46x** |
| oncrack-cached / fsharp | 5.43x | 5.75x | 6.25x | 6.19x | **5.89x** |
| c / rust | 1.59x | 1.72x | 1.52x | 1.60x | **1.61x** |

### Hand re-runs: room page, mixed and post

`review.py`, outside `bin/benchmark`: one container per app for the three phases, a 15 s warm-up then a 10 s window at 16 clients, every response validated, every acknowledged post audited, and the server's CPU read from the container's cgroup. Five alternations, A to E. A: fresh, cached, Rust, C. B, D, E: C, Rust, cached, fresh. C: as A. `review.jsonl` has every window and audit.

| App | phase | req/s per run | CPU us/request per run | median req/s | median CPU us/request |
|---|---|---|---|---:|---:|
| **onCrack, fresh authorization (default)** | room_show | 136,506, 149,479, 139,180, 117,827, 149,482 | 24.0, 20.5, 23.0, 26.9, 20.6 | 139,180 | 23.0 |
| **onCrack, fresh authorization (default)** | mixed | 144,816, 144,640, 144,445, 128,533, 149,018 | 21.7, 21.5, 21.9, 26.0, 20.7 | 144,640 | 21.7 |
| **onCrack, fresh authorization (default)** | post_message | 15,077, 15,044, 14,882, 11,672, 15,924 | 200.2, 200.2, 201.6, 260.5, 188.2 | 15,044 | 200.2 |
| onCrack, cached decision (opt-in) | room_show | 172,373, 164,987, 161,405, 150,594, 174,839 | 18.2, 19.5, 19.6, 22.2, 17.7 | 164,987 | 19.5 |
| onCrack, cached decision (opt-in) | mixed | 169,035, 169,147, 173,444, 154,291, 173,864 | 18.5, 18.2, 17.6, 21.3, 17.7 | 169,147 | 18.2 |
| onCrack, cached decision (opt-in) | post_message | 15,172, 12,700, 12,627, 13,619, 15,755 | 196.5, 235.5, 236.1, 217.8, 187.7 | 13,619 | 217.8 |
| Rust f9dca47 | room_show | 46,777, 50,618, 39,875, 39,112, 50,765 | 62.6, 56.3, 69.1, 74.0, 56.8 | 46,777 | 62.6 |
| Rust f9dca47 | mixed | 45,128, 46,716, 47,943, 38,569, 48,358 | 65.8, 62.3, 60.8, 76.1, 60.6 | 46,716 | 62.3 |
| Rust f9dca47 | post_message | 5,888, 6,371, 4,547, 5,317, 6,423 | 494.0, 459.6, 575.2, 546.2, 453.9 | 5,888 | 494.0 |
| C cd0cbe4 | room_show | 75,796, 77,041, 50,471, 67,195, 75,956 | 43.4, 41.9, 57.6, 49.4, 43.5 | 75,796 | 43.5 |
| C cd0cbe4 | mixed | 67,760, 71,662, 57,986, 61,661, 72,000 | 49.5, 46.5, 57.5, 54.0, 46.9 | 67,760 | 49.5 |
| C cd0cbe4 | post_message | 5,514, 4,886, 4,527, 3,656, 5,806 | 608.1, 672.7, 726.3, 887.7, 580.8 | 4,886 | 672.7 |

| CPU per request, median over runs | room page | mixed reads | post |
|---|---:|---:|---:|
| rust / oncrack | 2.72x | 2.87x | 2.47x |
| c / oncrack | 1.89x | 2.28x | 3.36x |
| rust / oncrack-cached | 3.21x | 3.43x | 2.27x |
| c / oncrack-cached | 2.23x | 2.72x | 3.09x |
| oncrack / oncrack-cached | 1.18x | 1.19x | 0.92x |

Set D ran while 56% of its host samples were at 150% or more. Without D the medians barely move: room page 21.8 / 18.9 / 59.7 / 43.4 us for fresh, cached, Rust and C (Rust 2.74x and C 1.99x onCrack's CPU); mixed 21.6 / 17.9 / 61.6 / 48.2; post 200.2 / 216.0 / 476.8 / 640.4.

**What fresh authorization costs.** A room-page hit takes 1.18x the CPU of the cached decision (23.0 against 19.5 us; R3.2 measured 1.40x on an earlier build). In the harness fresh runs at 0.87x of cached on the normal profile and 0.84x on the mixed one. Posts are the same in either mode: 9,498 and 9,382 req/s pooled, 200 and 218 us.

### Each session alone, and the spread

| Session | Timed responses validated | Acknowledged writes audited | Errors + invalid | Raw samples | Peak generator CPU % |
|---|---:|---:|---:|---:|---:|
| normal-1 | 47,268,174 | 1,329,979 | 0 | 180 | 261.6 |
| normal-2 | 25,396,892 | 555,460 | 0 | 180 | 300.9 |
| mixed-1 | 41,577,354 | 7,176 | 0 | 144 | 260.3 |
| mixed-2 | 42,379,432 | 7,178 | 0 | 144 | 246.3 |
| **all four** | **156,621,852** | **1,899,793** | **0** | **648** | |

| Geometric mean of the medians | fresh/rust | fresh/c | fresh/port | cached/rust | cached/c | fresh/cached |
|---|---:|---:|---:|---:|---:|---:|
| normal-1 | 2.68x | 1.85x | 3.18x | 3.27x | 2.26x | 0.82x |
| normal-2 | 3.33x | 2.31x | 5.07x | 3.30x | 2.29x | 1.01x |
| mixed-1 | 3.56x | 2.30x | 5.33x | 4.12x | 2.66x | 0.86x |
| mixed-2 | 3.10x | 1.83x | 4.64x | 3.74x | 2.21x | 0.83x |

Hand re-runs (review.jsonl): 60 timed windows (every one valid: True), 60 warm-ups, 20 database audits (every one ok: True, rich-text rows equal acknowledged: True, search-index rows missing: 0), 5,030,671 acknowledged posts audited.

The sessions are far apart, and the pooled normal multiples do **not** sit between them (corrected in the final review; this paragraph first said they did). onCrack over Rust is 2.68x in normal-1 and 3.33x in normal-2 but 2.59x pooled; the cached decision is 3.27x and 3.30x but 2.97x pooled. normal-2 ran in another regime: every engine at roughly half its normal-1 speed, posts included (onCrack's room page 76/52/76k against 128/135/132k, Rust's 46/22/23k against 48/51/44k). A median of six rounds then falls between the two regimes, at a different point for each engine (Rust's first normal-2 round was near its normal-1 level, onCrack's were not), so the pooled ratio can land outside both sessions'. Here it lands below both, so it understates the gap rather than overstating it. The plan fixed the pooled figure as the headline before any session ran, and it stays the headline. normal-1, the session the plan's rule reads as quiet, gives 2.68x Rust and 1.85x C, which agrees with the CPU per request (2.72x, 1.89x). normal-2 also reads fresh at 1.01x of cached, which cannot be right for a mode that does strictly more work per hit; that figure shows how much of the spread is the host. With a host this busy every harness multiple is good to about +/-25%.

The mixed profile goes the other way. The pooled multiples (3.31x Rust, 2.06x C) sit between the sessions but lean on mixed-1, the noisy one (3.56x, 2.30x). mixed-2, the quiet one, reads 3.10x Rust and 1.83x C, and the hand re-runs' mixed windows read 3.10x and 2.13x by throughput. So quote onCrack's mixed lead over C as about 1.8-2.1x, not 2.06x.

### The host

Sampled every 10 s into `host-load-*.txt` (the sum of non-VM CPU, the top four processes, the load average). A session waited for three quiet samples (under 100%) or 10 minutes.

| Sampler | Samples during the run | At 150% or more | Max | Median | Plan rule 2 |
|---|---:|---:|---:|---:|---|
| mixed-1 | 82 | 45 (55%) | 882% | 160% | NOISY |
| mixed-2 | 82 | 14 (17%) | 839% | 85% | ok |
| normal-1 | 100 | 19 (19%) | 795% | 36% | ok |
| normal-2 | 100 | 45 (45%) | 762% | 145% | NOISY |
| review-A | 32 | 0 (0%) | 137% | 16% | ok |
| review-B | 32 | 3 (9%) | 589% | 30% | ok |
| review-C | 32 | 2 (6%) | 318% | 50% | ok |
| review-D | 32 | 18 (56%) | 282% | 157% | NOISY |
| review-E | 32 | 0 (0%) | 131% | 17% | ok |

- **Plan rule 2** (a session is NOISY when more than 25% of its host samples during the run show 150% or more) flags normal-2 (45%), mixed-1 (55%) and hand re-run set D. Normal-1 reads 19% by the rule as written, which counts samples after its 440 s wait for quiet. Counting its whole file including the wait gives 55 of 145 (38%), which is how the resume brief described it. I ran normal-2 either way and pooled both; a noisy session is never dropped (rule 3). Mixed-1 was noisy, so mixed-2 was run.
- The load was another session's Erlang and Go builds (`beam.smp` at 280% and `spoor.test` at 474% in single samples), with whole-host peaks of 762-882% for short stretches.
- The VM's four server and four client CPUs are not pinned to physical cores, so Mac-side work reaches the benchmark without being on its CPUs. Every engine fell between the two normal sessions. Messages-page medians, normal-2 against normal-1: Rust 19,024 against 47,291, C 36,194 against 76,860, the port 14,817 against 40,007, onCrack fresh 83,782 against 138,863.

### Size

KLOC by upstream's rules (cloc 2.10, backend language only), recounted for onCrack and the port in `kloc.json`; Rails, Rust and C as upstream published them:

| Implementation | Backend KLOC |
|---|---:|
| Rails | 4.4 |
| Rust | 29.8 |
| C | 94.8 |
| F# port | 42.5 |
| onCrack | 44.6 |

Both F# counts include the html5ever tokenizer port (3,582 lines), which Rust takes as a crate (`kloc.json` has the counts without it: 40,863 and 38,893).

## 3. The page

`index.html` now reads this run, not R3.2's:

- The hero (fresh mode headline, cached decision as the last column, labelled opt-in) and the "Round three: their contract" panel read `oncrack-r3-final/normal-1`, `normal-2`, `mixed-1`, `mixed-2` and `review.jsonl`. The mixed table is now pooled over two sessions.
- A validation row for the four sessions (responses, writes audited, errors, samples, generator CPU) is new; the KLOC table uses the recount.
- The pixel panel said the full gate was "for the code before R3.3" and named one later unit. Three units changed `src/` after it (R3.2, R3.3, R3.4). It now says so and reports the final targeted gate (82 of 82).
- `site/build.py` fails if any visible number lacks a source file. It passes.

## Open

1. **A7, one unreproduced failure (explained in round 4: the test browser's cookie jar dropped a cookie whose signature held "1970"; the app was right; `oncrack-r4-a7.md`).** The verifier's A7 attack test (a message posted straight to the database, then David's room page, in 30 fresh apps) failed once in fresh mode: round 27, both requests answered 302 to `/session/new`, so that app instance treated David's seeded session cookie as unauthenticated. It is in `logs/attack-tests-r3-default.log`. Since then: 6 isolated runs of A7 (180 rounds), 16 full-suite runs (6 fresh, 4 cached, 6 fresh with every core saturated) and the cached-mode pass, all clean. One failure in 18 full runs (30 rounds each). I read `ReadCache.session`, `findSessionByCookie` and `resumeSession` and found no path that returns no session for a valid cookie without an error, and each test boots its own copy of the seed, so I did not find the cause. The failure happened on the first run after a compile. I am not calling it a flake with a cause; it is a one-off I could not explain, and a signed-in user bounced to sign-in is the kind of thing worth a later look with the app's log captured (the test harness keeps `CapturingLoggers` but does not print them).
2. **The mixed multiples are the less certain ones.** Rust's and C's mixed medians sit under round 2's on the same images. Mixed-1 was noisy by the plan's rule.
3. **The harness multiples swing 2.68x to 3.33x** between the two normal sessions. The CPU-per-request ratios (2.72x Rust, 1.89x C for a room page) are the figures I would quote for the size of the gap.
4. **The hand re-runs' set D** was noisy; the medians do not depend on it (shown above).
5. **The full pixel gate was not repeated on the final code.** The targeted gate (82 of 82) covers what R3.2-R3.4 could reach.

## Final review (round 3)

I read `git log d708910..HEAD` for behaviour changes and the data above skeptically. I re-ran no benchmark, because nothing pointed to a cell that a re-run on this host would settle.

**Correctness: no defect found, so no code changed.**
- **Fresh authorization.** Every request reads its session and user rows. A kept room or messages page is served only after `FreshAuth.membership` finds the row, and when it doesn't the action runs and answers as it would uncached. A replay runs `FreshAuth.replay` with the token, session id and user id captured when the answer was made, and any failure (`ValueNone` or an error) sends it to the app, so every failure path ends at the app's own answer. The page key still starts with the user's id, and the version counters still guard content.
- **The checks' own connections** (`Database.CheckNow`) are read-only, opened on demand up to 16, and never wait. Every statement on them is reset after its step (`Sql.fs` `finish`), so none holds a read snapshot that could see a deleted session as live. `FreshAuthTests` cover sign-out, a removed membership, a ban, the direct queries and starvation of the readers.
- **Search order.** `ORDER BY idx.rowid DESC LIMIT 100` is message id order, as Rails `dbc7620`. The join to the memberships is unchanged, so the order changed and what a user can reach did not.
- **The WAL.** By default the writer takes the same path as R2.2's restart (`forced` is true whenever `CAMPFIRE_WAL_DEFER` is off). The new 250 ms PASSIVE checkpoint of a quiet WAL only syncs earlier. The checkpointer stops cleanly with the timed wait. `synchronous` is unchanged. One overclaim, corrected in `oncrack-r3-wal.md`: the opt-in deferred restart keeps crash durability (the 4th kill -9 run used it, with 0 lost), but under power loss it can hold more acknowledged, unsynced commits while a checkpoint is stuck. That is not the default.
- **A7** (one 302 to sign-in in 18 full runs) stays open. It fails closed: a valid user was refused, and no data was served to anyone who should not see it. Each test copies the seed whole, so it is not shared state between tests. The cause is unknown.

**Numbers: two write-up corrections, now in the verdict, section 2 and the page.**
1. The pooled normal multiples are below both sessions' (2.59x against 2.68x and 3.33x over Rust; 2.97x against 3.27x and 3.30x for the cached decision). The report said the pooled medians sat between the sessions. The cause is the two host regimes, and the effect understates. The pre-registered headline stays.
2. The pooled mixed multiples (3.31x Rust, 2.06x C) lean on the noisy session; the quiet one reads 3.10x and 1.83x.

Checked and true:
- The validation totals (recounted from the raw files: 0 errors or invalid responses, every write audit verified).
- The hand re-runs' CPU per request against their throughput (2.6-3.4 busy cores in all 60 windows).
- The fresh-mode cost (1.18x the CPU of the cached decision per room-page hit; 0.82-0.86x of its throughput in every session but the noisy normal-2).

**Verdict.** Against current Rust `f9dca47`, onCrack in its default, comparable mode (fresh authorization) is about **2.6-2.7x** on upstream's five normal workloads. Against current C `cd0cbe4` it is about **1.85-1.9x**. The pooled harness figure, the quiet session and the server's CPU per request all agree on that. On the mixed profile it is about 3.1-3.3x Rust and 1.8-2.1x C. Posts are about 2x both by the harness, and 2.5x Rust and 3.4x C by CPU per post. These are real leads, measured on a busy host and good to about +/-25%. They are smaller than round 2's cached-decision 3.25x and 2.37x, because fresh authorization costs about 15-18% of throughput on cache hits.
