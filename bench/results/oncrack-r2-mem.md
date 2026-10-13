# onCrack R2.5: memory and cold start

Date 2026-10-08/09, branch `crack`. Code commits `4eb87dc` (tools, diagnostics, start-up prewarm) and `64a714d` (cache sizes, libvips, malloc). Image
`campfire-oncrack:app` `sha256:24c79d6462e5` (label `64a714d`); "before" is R2.4's image, kept as `campfire-oncrack:r24` `sha256:c4942d0a4aa7` (label
`4e12ec8`). `campfire-fsharp:app` (the port) and `campfire-rust:app` untouched. Raw data in [`oncrack-r2-mem/`](oncrack-r2-mem/); every table below is
printed by [`review/table.py`](oncrack-r2-mem/review/table.py) (output in [`review/table.txt`](oncrack-r2-mem/review/table.txt)) or quoted from
[`evidence/console-notes.txt`](oncrack-r2-mem/evidence/console-notes.txt) (requests per second of the memory runs, which the jsonl files do not hold).
Memory is the container's cgroup `anon` (what the processes hold; `memory.current` also counts the page cache the database writes fill) and the app
process's Pss (`smaps_rollup`), sampled every 200 ms by `bench/mem`.

onCrack is scored on its own terms (plan rule 4). Nothing here weakens durability, and no opt-in was added: the changes are default sizes of caches and
allocators, each with its environment variable.

## Verdict

- **The 781 MB peak was already gone when this unit began.** R2.1's direct cable writes took the 1,000-client fan-out from 726 to 295 MB. What
  was left was posting, 1,000 cable clients and an upload, in one container: **389 MB anon (490 Pss)** on R2.4's image. Now **285 MB (385 Pss)**.
  Same session, same scenario: **Rust 267 MB (291), the F# port 695 (796)**. So onCrack's peak anon is **1.07x Rust's** (round 1: 3.0x) and 0.41x the
  port's; Pss is 1.32x Rust's.
- **What did it** (each measured on its own, below):
  - an upload makes the process 100-200 MB bigger for a moment, in Rust as much as here (+163 MB). libvips' operation cache (100 MB), a worker per core
    and glibc's arena per thread were the cause. **16 MB, two workers and two arenas** cut an upload alone from 207 MB to 107 MB, and the classic
    scenario's whole-run peak from 389 to 285 MB, with the thumbnail 1.3 ms slower (30.8 against 29.5 ms).
  - the page caches were mis-sized. **Read cache 64 -> 16 MB, fast path 32 -> 64 MB.** The read cache keeps a page three ways (raw, gzip, plain) and
    only feeds the fast path; the fast path keeps the gzip member alone, and 2,112 pages did not quite fit its 32 MB. Under 525 users that is **`spread`
    88.5k -> 190.2k req/s (2.15x; 7.4x Rust, 6.4x the port) at 500 -> 151 MB anon** in the phase.
- **No GC setting is kept.** Seventeen settings measured (gen0 size, DATAS, conserve memory, heap count, hard limit, concurrent, workstation GC):
  they move a read-only phase and cost a write one, or move nothing. The heap that is left under writes is allocation, not configuration.
- **Idle** is level in anon (16 MB against Rust's 15) and higher in what the process maps: `memory.current` 30 against 18 MB, Pss 87 against 33
  (the runtime's file-backed pages, inherent to the JIT image; the AOT build is 53).
- **Cold start** (docker run to the first `/up`, 7 containers): **186-188 ms, was 192-201 ms** (a start-up thread now warms the route table, SQLite and
  the host builder). Rust 104, the port 194. **The AOT build is the reference for a fast start: 89-97 ms** (below Rust), idle 22 MB (anon 20, Pss 53);
  it peaks at 323 MB anon in the classic scenario. Still an opt-in (`--build-arg NATIVE_AOT=true`).
- **Throughput did not move** except `spread`, up 2.15x: the five classic workloads at c=16 and the three other realistic workloads are level (tables
  below). One earlier series showed `search_spread` 14% down and did not reproduce; it is reported below, not dropped.
- **Correct:** every response 2xx with 0 connection errors in every run; post rows equal the answers; decoded bytes equal Rust's on every probed route.
  Pixel parity on the states that revisit cached pages: **116/116** (default seed, `realtime/**` and `interactions/sidebar/**`) and **24/24** (crowd seed).

## Where the memory is (onCrack before, classic scenario)

One container, the phases in the order of `bench/run` (reads, posts at 1, 16 and 64 connections, cable at 100, 500 and 1,000 clients, an upload), peak anon
MB per phase with Pss in brackets (`review/table.txt` has all 20 phases):

| Phase | Rust | F# port | onCrack before | onCrack after | after, AOT |
|---|---|---|---|---|---|
| idle, 10 s after boot | 15 (33) | 15 (84) | 16 (85) | 16 (87) | 18 (53) |
| room page c=16 | 21 (39) | 103 (185) | 90 (169) | 88 (169) | 28 (64) |
| up c=16 (end of the reads) | 27 (46) | 106 (191) | 114 (198) | 114 (199) | 40 (77) |
| post c=16 | 100 (119) | 206 (292) | 184 (270) | 190 (277) | 196 (233) |
| post c=64 | 103 (122) | 206 (293) | 184 (270) | 187 (275) | 197 (234) |
| cable 1,000 clients | 108 (127) | 535 (625) | 216 (306) | 226 (317) | 237 (274) |
| upload (and the 10 s after) | 105 -> 267 (291) | 526 -> 695 (796) | 301 -> 389 (490) | 283 -> 285 (385) | 265 -> 323 (362) |
| **whole run** | **267 (291)** | **695 (796)** | **389 (490)** | **285 (385)** | **323 (362)** |

(The upload's memory arrives after its last request, as the thumbnail jobs run: read the later number.)

Inside onCrack's 184 MB at posting (`SMAPS=1 bench/mem`, the committed part of the GC's 256 GB reservation against the rest): the managed heap is about
127 MB of it, of which 45 MB is live after a collection; the rest, about 40 MB, is the runtime, SQLite's page caches (2,000 pages for each of six
connections, filled only as far as they are read), thread stacks and malloc. Idle is 16.

The 85 MB between live and committed is **allocation, not configuration**: the 294k posts of a 20 s window at c=16 took 781 gen0 collections, one per
380 posts, at a 64 MB gen0 budget, and nothing in the GC's settings changed what a collection leaves committed (below). Rust's posting phase is
100 MB anon altogether.

## The page caches (what moved `spread` and its memory)

`CAMPFIRE_READ_CACHE_MB` was 64 and `CAMPFIRE_FAST_PATH_MB` 32. The read cache's budget counts a page as `BodyLength * 2`, but a page it keeps costs
more (the body, its gzip member, a plain copy for the front server), and while it churns (`spread`, with the fast path too small) the pages it drops
are still in gen1 until a gen1 collection: gen1 reached 185 MB, and a 64 MB budget showed up as a 500 MB peak.

Cold container, 25 s per workload from the crowd seed (`bench/mem --seed crowd`, 30 s windows in the first row; req/s; the last column is the
peak anon of the whole run, which in the rows without a `mixed` figure ends after `search_spread`):

| Read cache / fast path | spread | spread_mixed | search_spread | mixed | peak anon |
|---|---|---|---|---|---|
| 64 / 32 (before) | 79,308 | 11,720 | 19,525 | 43,444 | 562 |
| 16 / 32 | 75,259 | 11,450 | 20,566 | | 403 |
| 32 / 32 | 74,818 | 11,586 | 20,540 | | 492 |
| 8 / 32 | 74,942-78,712 (3 windows) | | | | |
| 16 / 48 | 156,356 | 11,255 | 20,709 | 44,057 | 447 |
| 16 / 64, fragment cache 16 | 155,917 | 11,404 | 21,204 | 43,261 | 422 |
| 8 / 64, fragment cache 16 | 156,009 | 11,237 | 21,182 | 43,953 | 404 |

The fast path at 32 MB sat on the edge of the 2,112 pages and thrashed, so the read cache's size hid it. With room for all of them, `spread` is
all replays (16 us of CPU a request, was 38). The read cache does nothing for `spread` then, and it is what the other workloads need: tier 2 on the
mounted build, the realistic workloads once per read-cache size, fast path 64 MB, one rep each (`rc-16`, `rc-32`, `rc-64`):

| Read cache | mixed reads (posts)/s | spread | spread_mixed | search_spread | peak anon |
|---|---|---|---|---|---|
| 16 MB | 42,701 (1,292) | 191,207 | 11,958 | 17,584 | 470 |
| 32 MB | 43,524 (1,363) | 190,691 | 11,872 | 17,043 | 497 |
| 64 MB | 42,825 (1,375) | 190,070 | 12,146 | 15,778 | 563 |

**16 MB is kept**: the smallest heap, and `search_spread` is best there (17.6k against 15.8k at 64 MB; I did not find why a larger read cache is
slower on 105k distinct pages: the heap is larger and its collections were not compared). Fragment cache stays at 32 MB (Rails' default; 16 MB saved 40 MB in `spread_mixed` in one sweep, with a
throughput effect nobody measured). `CAMPFIRE_READ_CACHE_MB` and `CAMPFIRE_FAST_PATH_MB` still say otherwise. **Disclosed:** a client that does
not send `Accept-Encoding: gzip` gets pages that are bigger in both tiers, so fewer of them fit.

## libvips and malloc (what moved the upload)

`bench/mem idle:3 post:16:15 upload:5 idle:6`, peak anon of the whole run (single runs; the first rows are the base build, the rest `b3`, which adds
the knobs):

| Setting | Peak anon MB |
|---|---|
| none | 339 / 331 |
| `MALLOC_ARENA_MAX=2` | 307 |
| `MALLOC_ARENA_MAX=1` | 297 |
| `MALLOC_TRIM_THRESHOLD_=131072` | 283 |
| `VIPS_CONCURRENCY=1` | 311 |
| `CAMPFIRE_VIPS_CACHE_MB=0` | 332 |
| `CAMPFIRE_VIPS_CACHE_MB=16` | 307 |
| `CAMPFIRE_VIPS_CONCURRENCY=2` | 318 |
| **cache 16 + concurrency 2 + `MALLOC_ARENA_MAX=2`** | **253** |

An upload alone, from idle (`idle:3 upload:8 idle:3`): 225 / 214 MB against **123 / 120**. Rust through the same upload goes from 96 to 259 MB, so the
libvips cost is shared and Rust has no better settings for it. The thumbnail of the 2160x3840 JPEG in `upload:12` runs: 29.0 ms (base), 29.9 (all three), 27.6 (cache
16 + arena 2 without the worker cap). Fifteen uploads each, three runs with the images alternating (`t3-guard.sh`): **30.1 / 29.1 / 29.4 ms before,
30.7 / 30.8 / 30.8 after** (+1.3 ms, +4%); the classic scenario's five uploads gave 28.0 and 32.2. **Disclosed:** two libvips workers rather than one per core; a large PNG or TIFF on a many-core host may thumbnail more
slowly (set `CAMPFIRE_VIPS_CONCURRENCY=0` for libvips' own default, or `VIPS_CONCURRENCY`).

`MALLOC_ARENA_MAX=2` is in the Dockerfile's environment. Paired A B A B on the mounted build, `room` c=16 / post c=1, 16, 64: 137.9k/140.5k against
140.2k/138.6k; 4,576/4,610 against 4,616/4,613; 15,659/15,846 against 15,782/15,684; 17,510/17,455 against 17,442/17,496. Level.

## GC settings (none kept)

Posting and reading phases, `bench/mem`, peak anon of the run in MB; req/s in `evidence/console-notes.txt`. The base is the image's own environment
(`DOTNET_GCgen0size=0x4000000`, hill climbing off) with DATAS on, the .NET default.

| Setting | Result |
|---|---|
| `GCgen0size` 16 MiB / 32 MiB / 4 MiB | read phase 95 -> 48 / 63 / 51 MB, but the run's peak 182 -> 228 / 225 / 218 MB; room level, posts c=16 +1..+3%, c=64 +6..+8% |
| `GCgen0MaxBudget` 32 MiB / 8 MiB | no change (180-184 MB): not honoured under DATAS |
| `GCgen1size` 16 MiB | no change (179) |
| `GCConserveMemory` 9 (and 7 on the realistic runs) | no change (180); the realistic run 492, inside the 470-562 the same build gave in other runs |
| `GCHeapHardLimit` 256 MiB / `GCHeapHardLimitPercent` 10 | no change in committed (130-139 MB); 197 / 175 MB anon |
| `GCHeapCount` 2 | **542 MB**: setting a count turns DATAS off |
| `GCDynamicAdaptationMode` 0 (DATAS off) | **893 MB** (850 MB committed, 58 gen0 collections) |
| `gcConcurrent` 0 | 167 against 182 MB, posts -5% (13.9k against 14.7k at c=16), pauses 5.0 s against 3.0 s |
| workstation GC (`gcServer` 0) | same memory (187), same throughput at c=16 (room 139.9k against 141.6k, posts 14.9k against 14.7k) |
| workstation, gen0 16 MiB, non-concurrent | 337 MB: a small gen0 promotes the posts in flight |

Two findings that are not settings. **Workstation GC matches server GC at c=16 now** (the fast path allocates almost nothing on a hit), so the
phase 7 reason for server GC is gone for the read pages; it is not changed here, because the miss paths (`spread_mixed`, `search_spread`) allocate
and were not measured with it. And **committed memory in the posting phase is 130 MB under every setting** that leaves DATAS on: it follows the
allocation per post.

## Cold start

Docker alone is 67-83 ms of every number below (`docker run --network host --entrypoint /bin/true`). Milestones of the JIT image, ms since the process
started (`bench/boot --timeline`, `CAMPFIRE_BOOT_LOG=1`): the runtime reaches `main` at 25-30; the logger factory takes 23; the database opens in 25-30;
the app is built in 13; Kestrel's host in 20; listening at about 120. Then the first `/up` through the poll.

- **Kept:** a thread of its own does the first use of the route table (177 compiled regexes), SQLite and the host builder while the main thread builds
  the logger factory and opens the database (`CAMPFIRE_PREWARM=off`). Two paired runs of 7 containers: 201 / 197 ms off, 188 / 184 on. Tier 3 (7
  containers each, new / before / new / before): **186 / 188 against 201 / 192**. About 10 ms (5%); the milestone listing shows listening at 105-121
  instead of 120-125 ms.
- **Env settings, not kept:** `TieredPGO=0` 195, `gcServer=0` 197, both 193, `QuickJitForLoops=1 OSR_HitLimit=1` 198, against 214 for the same build
  (7 runs each): within the noise and each costs throughput or JIT quality.
- **AOT as the reference.** `AOT=1 bin/publish-mounted` at `64a714d`, 7 containers twice: **97 [94-148] and 89 [86-99] ms**, idle 22 MB (anon 20,
  Pss 53, rss 56). Rust 104 [98-106] in the same session. The classic scenario on it: peak anon 323 MB (the AOT runtime ignores
  `DOTNET_GCgen0size` and has no tiered compilation), room page c=16 141.6k req/s against the JIT image's 146.3k (-3%; it was -12% before the fast
  path), posts c=16 14.6k against 15.0k. It stays an opt-in: not rebuilt as an image and not run through pixel parity in this unit (C4's 361 cells
  were on older code), no HTTP/2 over cleartext.
- **Not done:** the database open (25 ms) and the host builder (20 ms) are still on the critical path; the runtime's own start (25-30 ms before `main`)
  is deps resolution and assembly loads.

## Tier 3

The rebuilt image against R2.4's, alternating in one window (series B: old, new, old, new; "new" has a third rep, the recheck run described below),
c=16 readers on the crowd seed, median [min-max] of the reps, CPU in us per request. Rust and the port are the stored medians of
[`oncrack-r2-bench/`](oncrack-r2-bench/) (R2.0's session, same harness and seed).

| Workload | before | after | after / before | Rust | port | after / Rust | after / port |
|---|---|---|---|---|---|---|---|
| mixed, reads/s | 43,050 [42,384-43,717] | 43,763 [43,336-44,523] | 1.02x | 18,597 | 24,232 | 2.35x | 1.81x |
| mixed, posts/s | 1,373 | 1,378 | 1.00x | 688 | 753 | 2.00x | 1.83x |
| spread, reads/s (CPU) | 88,512 (38.8) | **190,209 [189,609-191,038] (16.3)** | **2.15x** | 25,655 | 29,902 | **7.41x** | **6.36x** |
| spread_mixed, reads/s | 10,914 [10,412-11,416] | 11,112 [10,948-11,274] | 1.02x | 13,155 | 13,584 | 0.84x | 0.82x |
| spread_mixed, posts/s | 644 | 665 | 1.03x | 319 | 393 | 2.08x | 1.69x |
| search_spread, reads/s | 16,968 [16,831-17,104] | 17,356 [17,352-17,394] | 1.02x | 8,468 | 18,942 | 2.05x | 0.92x |

Peak anon over the four workloads in one container: before 579 [572-586] MB, **after 462 [455-467]**; Rust 220, port 409 (round 2.0's session).

**The first series did not reproduce.** The first tier 3 run (series A, two reps per image, images alternating, started right after the rebuild) put
`search_spread` at 14,305 [14,276-14,334] for the new image against 16,623 for the old, and the mixed lane's posts at 1,231 against 1,362: -14% and
-10%. The tier 2 runs of the same code on the mounted build (16 / 32 / 64 MB read cache), a rerun of the same image, and series B (above) all put
them level or up (17.0-17.6k; 1,292-1,381). I could not attribute series A; its raw files are in `t3-real-old/` and `t3-real-new/` and its table is in
`review/table.txt`. The searches' read cache capacity is not the cause: at 64 MB, with the same build, `search_spread` was the slowest (15.8k).

The classic five at c=16, the guard that the sizes did not move the cached-hit workloads (`t3b-classic-old/new`, 2 reps each, alternating):

| Workload, c=16 | before, req/s [min-max] (CPU us) | after | after / before |
|---|---|---|---|
| room page | 171,701 [167,684-175,719] (18.0) | 176,902 [176,328-177,476] (17.6) | 1.03x |
| messages page | 181,967 [180,785-183,149] (16.6) | 185,005 [183,840-186,171] (16.4) | 1.02x |
| sidebar | 196,183 [196,168-196,198] (14.9) | 197,655 [197,516-197,793] (14.9) | 1.01x |
| search | 191,411 [190,827-191,996] (15.5) | 193,464 [193,394-193,533] (15.4) | 1.01x |
| post a message | 12,968 [10,325-15,611] (179.9) | 15,687 [15,608-15,765] (177.8) | 1.21x |

The post row's "before" median averages a stalled rep (10.3k: the known c=16 posting stall of R2.2, the writer's WAL restart; its warm-up reached the 90 s
maximum) with a normal one (15.6k); the normal reps are level, 15.6k and 15.6-15.8k. The reads are 1-3% higher after, which I do not read as a gain.

Memory of the realistic suite in one container (peak anon per phase, `review/table.txt`): `spread` 500 -> **151** MB, `spread_mixed` 447 -> 447,
`search_spread` 522 -> 412, `mixed` 468 -> 449; whole run 522 -> **449**. The three after `spread` stay at 400+ MB for the reason in the first
deferred item.

## Checks

- `bin/verify` on `64a714d`'s tree, twice: 1,117 tests, 1,109 passed, 7 skipped, **1 failed**, the same one both times (`evidence/verify-first-run.txt`,
  `verify-final.txt`): `Campfire.Cable.Tests.DirectTests` "a plain TCP connection writes to its socket once its probe is answered" got a
  disconnect frame where it wanted its first message. It passes 10/10 alone and in its own project's 81 (run twice). It is not this unit's: with
  `src/`, `tests/` and the Dockerfile checked out at R2.4's `b79234d`, a full `bin/verify` fails the same test (1,116 tests, 1 failed,
  `evidence/verify-r24-source.txt`). I did not diagnose it: it looks load-dependent (it fails only when the other test projects run beside it), and R2.4's own run
  did not hit it. Open.
- New test: the libvips defaults (`UnitTests.fs`, "libvips starts with a 16 MB operation cache and two workers unless the container says otherwise").
  No cache is new, so no new attack test: the existing `FastPathTests` and `ReadCache` tests ran against the new sizes in `bin/verify`. The fast
  path's key, its validity rule and its bound are R2.3's; only the number moved.
- Pixel parity (`bin/pixel-parity`, screenshot layer): default seed `--only 'realtime/**,interactions/sidebar/**'` **116/116** in 1,222 s, crowd seed
  **24/24** in 79 s, on the candidate image built from `64a714d`. Not run: the other three seeds and the full matrix (nothing here changes what a
  request returns, only how much is kept).
- `bench/run`'s checks in every run: every response 2xx, 0 connection errors, post rows equal answers, decoded bytes equal Rust's.
- Durability: untouched (`journal_mode=wal`, `synchronous=normal`, group commit window 0).

## New settings (all defaults are Rails-equivalent in behaviour; they change sizes)

| Variable | Default | Was |
|---|---|---|
| `CAMPFIRE_READ_CACHE_MB` | 16 | 64 |
| `CAMPFIRE_FAST_PATH_MB` | 64 | 32 |
| `CAMPFIRE_VIPS_CACHE_MB` | 16 | libvips' 100 |
| `CAMPFIRE_VIPS_CONCURRENCY` | 2 (0: libvips' own; `VIPS_CONCURRENCY` wins) | one worker per core |
| `MALLOC_ARENA_MAX` (Dockerfile) | 2 | glibc's 8 per core |
| `CAMPFIRE_PREWARM` | on (`off`) | none |
| `CAMPFIRE_MEM_LOG_MS`, `CAMPFIRE_BOOT_LOG` | off | diagnostics |

## Tools

`bench/mem` (scenarios `idle:S`, `get:KIND:C:S`, `post:C:S`, `cable:N`, `upload:N`, `real:WORKLOAD:S`; `SMAPS=1` for the heap split), `bench/mem-sweep`
(one run per environment setting), `bench/boot --timeline`. Drivers of this unit's runs: `oncrack-r2-mem/t3*.sh`, `t2-rc.sh`.

## Deferred

1. **Allocation per post (about 120 KB).** It is why the heap holds 85 MB beyond its live data while posting, and why a small gen0 hurts. No setting
   touches it; the render and the write path would. This is the largest remaining gap to Rust's posting phase (190 against 100 MB).
2. **Stale cache entries under writes.** `spread_mixed` and `search_spread` reach 400+ MB: a post moves the counters of every reader's pages, and the
   entries it invalidated stay reachable until their generation rotates, growing gen1 and gen2. Dropping an entry when its version check fails, or
   dropping a generation on a version bump, would let the collector have it.
3. **SQLite's reader page caches** (`cache_size = 2000` pages, six connections, up to about 48 MB of native memory on a large database). Not measured:
   a smaller cache means more `pread`s on a miss.
4. **Cold start:** the database open (25 ms), the host builder (20 ms) and the runtime's own start; a composite or trimmed image was ruled out by C4.
5. **AOT:** an image rebuilt at HEAD, pixel parity on it, static PGO. The tier 2 numbers above are one container each.
6. **Workstation GC** for the read pages (the same speed with 4 fewer threads); the miss paths decide it.
