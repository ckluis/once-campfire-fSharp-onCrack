# onCrack unit C0: measurable on its own terms

Date 2026-10-07, branch `crack`, plan `plans/oncrack.md`. Nothing about the app changed: this unit built the instruments and measured the
unchanged fork once, so every later number has a starting dot.

## What exists now

| Piece | Where |
|---|---|
| Image `campfire-oncrack:app` (the port's source, rebuilt from HEAD; `campfire-fsharp:app` untouched) | `CAMPFIRE_REVISION=$(git rev-parse HEAD) parity/bin/candidate build` in colima, 31 s (all layers cached) |
| An `oncrack` app (and `oncrack-identity`) beside `reference`, `rust`, `fsharp` (the port) | `bench/run --apps reference,rust,fsharp,oncrack`, `ONCRACK_IMAGE`, `ONCRACK_EXTRA_ENV`, `ONCRACK_MOUNT`; `bench/report` has onCrack columns (vs Rust, vs the port) |
| `bench/quick` measures onCrack alone | `--apps` takes any of the four; `--mounted` mounts over `campfire-oncrack:app` |
| Scoring | `bench/quick compare DIR` prints onCrack against the stored Rust **and** F# port medians of `bench/results/phase7-final/` (same session, 3 reps each); `bench/quick log` appends to `bench/results/oncrack-log.jsonl` (the port's `phase7-log.jsonl` is history) |
| The climb chart is onCrack's | `bench/progress/climb.py` (line = onCrack / Rust, c=16 geometric mean), `history.json` starts with the port's final result (`python3 bench/progress/climb.py --check` verifies its numbers against `phase7-final`), cards have an "F# port" column, `site/build.py` writes a short onCrack `index.html`; the port-era dots are in the "port's climb" panel |
| Parity candidate | `parity/bin/candidate` defaults to `campfire-oncrack:app` (`campfire-candidate-oncrack`); `PARITY_CANDIDATE_APP=fsharp\|rust` select the others; `PARITY_CANDIDATE_ENV="K=V ..."` adds env to every candidate a compare starts |
| Pixel gate | `bin/pixel-parity` (below) |

## Pixel parity, once, on the unchanged image

`bin/pixel-parity` (lean matrix, 4 workers, all five seeds, one compare at a time) against the Rails reference:

| Seed | Screenshots equal | Time |
|---|---|---|
| default | 860 / 860 | 3,531 s |
| crowd | 24 / 24 | 78 s |
| custom_styles | 32 / 32 | 90 s |
| first_run | 16 / 16 | 64 s |
| restricted | 8 / 8 | 25 s |
| **all** | **940 / 940, 0 different, 0 not captured** | **3,788 s (63 min)** |

That is not fast. The default seed is 874 cells, 228 of them on freshly started servers (mutating states), and the harness is built for a
box with more cores and memory than the 6 GB colima VM, where 4 Chromium workers is what fits. `bin/pixel-parity --fast` (Chromium, light scheme,
no breakpoint sweep: about half the cells) is the first look while a change is in progress and has not been timed on a whole seed; the unit's close
runs the default. Something to beat in a later unit if the gate is to run per change: the cells on fresh servers.

Two things the run showed, both of the harness and not of the pixels:

- **Cells that do not capture.** `auth/sign_in/error` and `auth/sign_in/rate_limited` (a failed login, on freshly started servers) time out
  ("not ready after 30000 ms", stylesheets in flight) on the candidate side in some of their cells on the first attempt: 2 states went to a second attempt and 1 to a third
  in the full run. It is probably not onCrack's doing (the image is the port's, bit for bit in source), but that was not established: the checks meant to run the port's
  image and the Rust one in the harness ran onCrack's, because `colima ssh` dropped the environment (since fixed in `bin/pixel-parity`). Against that, `curl`, six keep-alive
  connections and the same states on shared servers all get the stylesheets in
  milliseconds, so it was not chased. `bin/pixel-parity` captures those states again (`PIXEL_PARITY_RETRIES`, default 2) and counts a cell by its last
  attempt; a cell that never captures fails the gate instead of passing it. Worth a root cause in a later unit, because a stylesheet that hangs for 30 s in a
  browser would be a real defect.
- **A 5.9 GB core file** (`parity/core`, 06:54 in the VM) appeared in the repository during the run, from a process that crashed (the harness carried on). It was deleted;
  with the run's own scratch files it took the Mac from 19 GB to 2.6 GB free until `bin/clean-docker` trimmed the VM disk. Check `df -h ~` after a parity run, not only
  before a benchmark.

## Tier 3 of the unchanged image (the chart's first measured dot)

`campfire-oncrack:app` rebuilt from HEAD (`2de7519`, no source change since the fork), `bench/quick --only oncrack:N --part K/2`, 3 reps, all five workloads at c=1 and c=16, server on
CPUs 0-3, load generator on 4-7, warm-up until flat, every response 2xx with 0 connection errors in 30 runs, decoded bytes equal Rust's on every probed route,
post rows equal to the 2xx answers, host probe 1.01-1.06 before and after every window (0 of 30 above 1.10). Raw: `bench/results/oncrack-c0/tier3/` (`report.md`, `vs-stored.md`), logged with `bench/quick log` (`bench/results/oncrack-log.jsonl`).

Against the port's final result (`phase7-final`), the port's own later tier 3 (unit 7.5: thread-pool hill climbing off, the one change the port made after its final run and
the image onCrack was forked from), and Rust:

| Workload | c | onCrack req/s | port 7.5 tier 3 | onCrack / 7.5 | port final | onCrack / final | Rust | onCrack / Rust | onCrack CPU µs/req | 7.5 | final | Rust |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 38,994 | 39,144 | 0.996 | 40,422 | 0.965 | 28,623 | 1.362 | 91.6 | 91.0 | 93.6 | 122.4 |
| room page | 1 | 7,450 | 7,391 | 1.008 | 7,617 | 0.978 | 6,481 | 1.150 | 210.6 | 209.4 | 208.7 | 142.1 |
| messages page | 16 | 41,859 | 42,144 | 0.993 | 37,836 | 1.106 | 30,063 | 1.392 | 84.9 | 84.4 | 102.2 | 114.2 |
| messages page | 1 | 8,148 | 8,115 | 1.004 | 8,312 | 0.980 | 6,822 | 1.194 | 202.6 | 201.7 | 199.3 | 139.2 |
| sidebar | 16 | 37,894 | 37,814 | 1.002 | 37,555 | 1.009 | 28,238 | 1.342 | 95.1 | 95.4 | 101.8 | 123.2 |
| sidebar | 1 | 7,620 | 7,752 | 0.983 | 8,000 | 0.953 | 6,196 | 1.230 | 189.6 | 184.9 | 181.0 | 149.0 |
| search | 16 | 33,931 | 34,002 | 0.998 | 34,070 | 0.996 | 26,606 | 1.275 | 107.5 | 107.5 | 107.3 | 123.9 |
| search | 1 | 5,669 | 5,841 | 0.971 | 6,055 | 0.936 | 5,646 | 1.004 | 328.3 | 326.3 | 315.1 | 158.3 |
| post a message | 16 | 8,566 | 8,738 | 0.980 | 8,905 | 0.962 | 7,174 | 1.194 | 359.9 | 357.5 | 353.0 | 385.6 |
| post a message | 1 | 2,970 | 2,976 | 0.998 | 3,052 | 0.973 | 2,779 | 1.069 | 641.9 | 644.6 | 629.1 | 403.7 |

Geometric means of the five workloads: at c=16 onCrack is **1.311x Rust**, 1.006x the port's final result and 0.994x the port's unit 7.5 tier 3 (which was 1.319x Rust);
at c=1, **1.126x Rust**, 0.964x the final and 0.993x unit 7.5 (1.135x Rust). So the unchanged fork matches the port within noise (0.7% at c=16 against the build it was forked from),
and the c=1 gap to `phase7-final` is the one the port itself measured when it disabled hill climbing: its CPU per request is level, the single connection gets a little less
throughput. Nothing here was manufactured, and nothing looked too good: the one cell above 1.10 against the final (messages page, c=16, 1.106x) is the port's own
unit 7.5 value (1.114x), whose final-run counterpart had the 3.19 ms p99 tail.

Ratios in this file are against the stored Rust and port medians (not re-measured beside them this session) and are onCrack's, never like-for-like port results.

## Not done here

- `bench/breakdown perf` and `alloc` still name the F# image by `image_for fsharp`; `bench/quick cpu` works for onCrack (report columns relabelled), perf and alloc need the same treatment when a unit needs them.
- Rust and the port were not re-measured in this session (the plan scores against `phase7-final`); `bench/run --apps reference,rust,fsharp,oncrack` is there for the re-baseline that closes a phase.
- `site/data.json` and `site/collect_tokens.py` are the port's story and are no longer drawn.
