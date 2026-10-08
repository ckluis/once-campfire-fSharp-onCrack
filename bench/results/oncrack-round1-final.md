# onCrack round 1: four-way re-baseline and review, 2026-10-07/08

This run re-measures Rails, the Rust port, the F# port and onCrack in one session. It ran
`bench/run --apps reference,rust,fsharp,oncrack --reps 3` with every suite (HTTP at c=1, 16 and 64 on eight routes, Cable fan-out,
upload), the long warm-up (30-90 s) and capped logs. `SERVER_CPUS=0-3 LOADGEN_CPUS=4-7`.

- Raw data: one JSON per app and rep in [`oncrack-round1-final/`](oncrack-round1-final/).
- `report.md` is `bench/report`'s full output, with every validity table.
- `vs-stored.md` scores onCrack against phase7-final's stored medians.
- The hand-run review checks are in [`oncrack-round1-final/review/`](oncrack-round1-final/review/).

onCrack is scored on its own terms (plan rule 4). It is not a like-for-like port result. It caches finished pages, and it groups
concurrent posts into one commit.

**Verdict**

- **Against Rust:** onCrack serves more requests per second on all five workloads at all three concurrencies.
  - Geometric mean of the five workloads: 2.06x Rust at c=1, 3.84x at c=16 and 4.54x at c=64.
  - Read pages: 2.0-2.9x at c=1 and 4.1-5.4x at c=16 and c=64.
  - Posts: 1.23x at c=1, 1.87x at c=16 and 3.97x at c=64.
- **Against the F# port:** the geometric mean is 1.77x at c=1, 2.89x at c=16 and 3.37x at c=64.
- **CPU per request** at c=16 and c=64 is a quarter of Rust's on the read pages and half of Rust's on posts.
- **Where onCrack does not win:**
  - CPU per request at one connection is level with Rust on the read pages (0.78-1.00x), and 1.43x Rust on posts.
  - Memory is higher than the port's, and well above Rust's.
  - Cold start is 1.8x Rust's.
  - Cable fan-out is the port's (0.61-0.87x Rust).
  - Avatar and the CSS file are the port's.
- **The read-page multiples are a 100% cache-hit benchmark.** `bench/run`'s read workloads never write. I measured the other end,
  with the read room written to about 1,100 times a second (below). There onCrack reads 1.75x the port and 2.3x Rust, and posts
  1.4x the port and 1.6x Rust in the same window.
- **The run is sound:**
  - Every response was 2xx, with 0 connection errors.
  - Rows written equal the answers in all 72 post phases.
  - Decoded bodies are byte-identical to Rust's.
  - The UI is pixel-identical to Rails': 940/940 screenshots on all five seeds.
  - Rust re-measured within 2.5% of its stored phase7-final medians on every c=1 and c=16 cell.

## The five workloads

Req/s, median of 3 reps, with the server container's CPU µs per request in brackets (cgroup `cpu.stat`, unprofiled). All four apps
were measured in this session. Signed in, keep-alive, gzip, same seed and pinned CPUs.
The script is [`review/table.py`](oncrack-round1-final/review/table.py).

| Workload | c | Rails | Rust | F# port | **onCrack** | **onCrack / Rust** | **onCrack / port** | port / Rust |
|---|---|---|---|---|---|---|---|---|
| room page | 1 | 112 (9,054) | 6,395 (143.8) | 7,555 (210.5) | 13,428 (144.2) | **2.10x** (CPU 1.00x) | **1.78x** (CPU 0.69x) | 1.18x |
| room page | 16 | 233 (12,602) | 28,582 (122.5) | 39,459 (90.3) | 123,942 (30.1) | **4.34x** (CPU 0.25x) | **3.14x** (CPU 0.33x) | 1.38x |
| room page | 64 | 228 (12,740) | 29,171 (120.4) | 41,342 (85.2) | 128,395 (29.4) | **4.40x** (CPU 0.24x) | **3.11x** (CPU 0.35x) | 1.42x |
| messages page | 1 | 216 (4,756) | 6,684 (140.6) | 8,155 (201.4) | 13,623 (142.3) | **2.04x** (CPU 1.01x) | **1.67x** (CPU 0.71x) | 1.22x |
| messages page | 16 | 394 (7,138) | 30,158 (114.2) | 42,404 (83.7) | 123,252 (29.8) | **4.09x** (CPU 0.26x) | **2.91x** (CPU 0.36x) | 1.41x |
| messages page | 64 | 372 (7,408) | 30,700 (112.0) | 45,174 (78.3) | 135,872 (27.2) | **4.43x** (CPU 0.24x) | **3.01x** (CPU 0.35x) | 1.47x |
| sidebar | 1 | 284 (3,614) | 6,134 (149.0) | 7,838 (184.0) | 14,987 (133.7) | **2.44x** (CPU 0.90x) | **1.91x** (CPU 0.73x) | 1.28x |
| sidebar | 16 | 602 (4,879) | 28,378 (122.5) | 38,001 (95.0) | 138,182 (26.7) | **4.87x** (CPU 0.22x) | **3.64x** (CPU 0.28x) | 1.34x |
| sidebar | 64 | 532 (5,521) | 28,844 (120.6) | 39,722 (90.3) | 154,883 (24.0) | **5.37x** (CPU 0.20x) | **3.90x** (CPU 0.27x) | 1.38x |
| search | 1 | 196 (5,157) | 5,509 (162.2) | 5,734 (328.9) | 15,700 (126.8) | **2.85x** (CPU 0.78x) | **2.74x** (CPU 0.39x) | 1.04x |
| search | 16 | 400 (7,139) | 26,396 (124.6) | 33,773 (108.2) | 136,032 (27.3) | **5.15x** (CPU 0.22x) | **4.03x** (CPU 0.25x) | 1.28x |
| search | 64 | 367 (7,780) | 32,717 (109.6) | 42,187 (84.9) | 152,233 (24.8) | **4.65x** (CPU 0.23x) | **3.61x** (CPU 0.29x) | 1.29x |
| post a message | 1 | 187 (7,481) | 2,759 (408.7) | 3,034 (636.0) | 3,395 (585.2) | **1.23x** (CPU 1.43x) | **1.12x** (CPU 0.92x) | 1.10x |
| post a message | 16 | 344 (9,785) | 7,082 (388.1) | 8,780 (354.8) | 13,215 (230.0) | **1.87x** (CPU 0.59x) | **1.51x** (CPU 0.65x) | 1.24x |
| post a message | 64 | 343 (9,999) | 4,459 (387.0) | 5,324 (339.8) | 17,684 (186.6) | **3.97x** (CPU 0.48x) | **3.32x** (CPU 0.55x) | 1.19x |

Geometric means of the five workloads:

| | onCrack / Rust | onCrack / port | port / Rust |
|---|---|---|---|
| c=1 | 2.06x | 1.77x | 1.16x |
| c=16 | 3.84x | 2.89x | 1.33x |
| c=64 | 4.54x | 3.37x | 1.35x |

The ratios against the stored phase7-final medians are almost the same: 2.02x, 3.82x and 4.47x Rust, and 1.73x, 2.93x and 3.52x the
port. `vs-stored.md` has them cell by cell. onCrack's tier 3 from the verifier fixes (`oncrack-fixes.md`, image 1598c5e, same
`src/`) is within 1% on every c=16 cell.

Latency, p50 / p99 ms, at c=16: room page Rust 0.53 / 1.08, port 0.38 / 1.07, onCrack 0.11 / 0.41. Post Rust 2.10 / 6.13, port
1.56 / 6.10, onCrack 1.03 / 5.34. onCrack has the lowest p50 and p99 of the four on every workload and concurrency, except post
c=1, where its p99 equals Rust's (0.53 ms).

## Other suites

| | Rails | Rust | F# port | onCrack | onCrack / Rust | onCrack / port |
|---|---|---|---|---|---|---|
| cold start, docker run → `/up` (ms) | 2,165 | 140 | 292 ¹ | 256 | 1.8x slower | 0.88x the time |
| idle memory.current (MB) | 311 | 16 | 27 | 28 | 1.75x more | level |
| peak memory.current, whole run (MB) | 1,665 | 630 | 1,175 | 1,327 [1,288-1,399] | 2.1x more | 1.13x more |
| peak anon, whole run (MB) | 1,616 | 264 | 718 | 781 [755-850] | 3.0x more | 1.09x more |
| Cable, 100 clients: msgs/s delivered to all | 94 | 3,215 | 2,695 | 2,781 | 0.87x | 1.03x |
| Cable, 1,000 clients: msgs/s delivered to all | 16.1 | 579 | 350 | 356 | 0.61x | 1.01x |
| Cable, 1,000 clients saturated: app Pss (MB) | 980 | 126 | 654 | 749 | 5.9x more | 1.15x more |
| upload + thumbnail, POST → thumb served (ms) | 50.1 | 27.7 | 29.0 | 29.7 | 1.07x slower | level |
| avatar c=16 req/s (CPU µs) | 71,475 (38.4) | 141,004 (15.7) | 168,372 (22.2) | 170,736 (21.8) | 1.21x (CPU 1.39x) | level |
| CSS file c=16 req/s (CPU µs) | 96,947 (29.4) | 150,301 (14.8) | 186,537 (20.3) | 186,488 (20.3) | 1.24x (CPU 1.37x) | level |
| `/up` c=16 req/s (CPU µs) | 4,245 (640) | 116,041 (22.4) | 89,808 (23.4) ² | 166,137 (22.3) | 1.43x | 1.85x ² |

¹ The port's median includes a 410 ms first start. Its other starts were 221-265 ms.

² `/up` at c=16 is the one cell that moved for the port between phase7-final and now (147,639 → 89,808). It is not onCrack's doing.
I checked it two ways (`review/up-check/`, one rep each):
- The port with hill climbing turned back on (`DOTNET_HillClimbing_Disable=0`) reads 136,324. Unit 7.5's tier 3 measured only the five
  workloads, so it never saw this cost.
- onCrack with chunking turned back on (`CAMPFIRE_GZIP_LENGTH=off`) reads 86,052.

So the chunked answer's second send costs `/up` a third at c=16, but only with the smaller thread pool of hill climbing off. C3's
Content-Length is what gives onCrack the cell back. CPU per request is the same in all four runs (21-24 µs): the server was waiting,
not working.

## Reads while the room is being written to (the cache's other end)

`bench/run`'s read workloads repeat one URL with no writes, so onCrack's read cache answers every request from a stored page. In
[`review/mixed.sh`](oncrack-round1-final/review/mixed.sh), 16 connections read the room page while one connection posts into the
same room as fast as the app answers. Each post moves the room's counter. The run is 30 s together as a warm-up, then a 15 s
window. Two runs per app, in opposite orders: [`review/mixed.jsonl`](oncrack-round1-final/review/mixed.jsonl).

| | Rust | F# port | onCrack | onCrack / Rust | onCrack / port |
|---|---|---|---|---|---|
| room page reads/s, c=16 | 18,810 / 18,428 | 24,307 / 24,438 | 43,212 / 42,291 | 2.32x | 1.75x |
| posts/s into that room, c=1 | 692 / 665 | 774 / 787 | 1,099 / 1,115 | 1.63x | 1.42x |
| read p50 / p99 ms (first run) | 0.82 / 1.78 | 0.67 / 1.59 | 0.19 / 1.12 | | |
| CPU µs per request (reads and posts) | 177 / 180 | 148 / 148 | 85 / 86 | 0.48x | 0.58x |

Every response was 200, and rows written equal posts answered in all six runs. With about 1,100 invalidations a second against
42,000 reads, onCrack still serves mostly hits (about 38 reads per change), so this is a mix of hits and renders, not the miss path
alone. The miss path alone is the port's: unit C1's tier 2 with `CAMPFIRE_READ_CACHE=off` lands within noise of C0. Even with the
read room written to about 1,100 times a second, onCrack keeps 1.75x the port on the reads.

## The review (assume it is wrong until shown otherwise)

**Image provenance** (`env.txt`, `docker image inspect`):
- onCrack is `campfire-oncrack:app` `sha256:3fd0dd609e3c`, label `da1e92f` (HEAD). It was rebuilt before the run, and its app layers
  came from the build cache. `src/` is identical to 1598c5e, the verifier-fix image.
- The F# port is `campfire-fsharp:app` `sha256:421f335c3ff8`, label `2e6c08e`. That is unit 7.5's image, with hill climbing off, and
  the published port's final. It is not phase7-final's `82ebcbc734ec`, so the port's re-measured numbers differ from phase7-final
  where unit 7.5 moved them (messages page c=16 +12%, `/up` c=16 above).
- Rust `d582a01d3a4a` and Rails `d2ca3b5d7a7f` are the same images as phase7-final.
- `git status` was clean under `src/` and `rust/`. `bin/clean-docker` ran after the rebuild and after the parity runs.

**Statuses:** every response of every run was 2xx, with 0 connection errors. That is 57.0M onCrack, 34.8M F# port, 29.1M Rust and 8.5M
Rails responses.

**Rows written:** equal to the 2xx answers in all 72 post phases (the warm-ups and runs of every app and rep). onCrack wrote 3.86M rows.

**Bytes**, checked two ways:
- `bench/run`'s probe found equal decoded sizes on every route.
- [`review/bytes.sh`](oncrack-round1-final/review/bytes.sh) ran Rust's and onCrack's parity images on the same seed, on the same port,
  with the clock frozen at 2026-03-02T16:00Z and nothing masked. The decoded bodies are **byte-identical**: room page (gzip and
  identity), messages page, sidebar, search, the post's answer and the room page after the post
  ([`bytes-sha256.txt`](oncrack-round1-final/review/bytes-sha256.txt)).
- onCrack's gzip on the wire is 0-1.2% smaller than Rust's, the same deflate as the port.

**Pixel parity:** `bin/pixel-parity` (lean matrix) against Rails, on image `campfire-candidate-oncrack` built from `da1e92f`. The
verifier's run was on the pre-fix image 460e89d, so this is the first pixel gate of the fixed code.
- **940/940 screenshots pixel-equal**, 0 different, 0 flaky: default 860/860, crowd 24/24, custom_styles 32/32, first_run 16/16,
  restricted 8/8.
- The default seed ran in ten `--only` slices, so each fits one foreground call. They cover the same 860 cells as the verifier's
  full run (checked against its `report.json`).
- `auth/sign_in/error @ chromium-desktop-light` was not captured twice: the 30 s wait for stylesheets that predates round 1 (C0).
  It matched on the retry.
- Reports are in `parity/out/pixel-parity-round1-final/{small,A-J,I-retry}/` (gitignored).
- During the realtime slice, WebKit's WPEWebProcess again left a 5.8 GB core dump at `parity/core`, as in the verifier's run. I
  deleted it.

**Counts the load generator could get wrong:** [`review/manual.sh`](oncrack-round1-final/review/manual.sh) is phase7-final's hand run
with onCrack added. It runs the room page and post at c=16 and c=1, outside `bench/run`. Each has a fixed warm-up (90 s at c=16, 45 s
at c=1), then a 15 s window. CPU is read straight from `cpu.stat`, and requests are also counted from the server's own log.

| | Rust | onCrack |
|---|---|---|
| room page c=16: req/s, CPU µs, cores busy | 28,299, 123.5, 3.49 | 122,428, 30.3, 3.71 |
| room page c=1 | 6,433, 143.5, 0.92 | 13,823, 142.4, 1.97 |
| post c=16 (after 90 s of posting) | 5,005, 386.8, 1.94 | 12,735, 235.6, 3.00 |
| post c=1 | 2,766, 406.0, 1.12 | 3,290, 605.6, 1.99 |

- The hand-run req/s are within 4% of `bench/run`'s, except Rust's post at c=16. Rust's posting rate falls as the write room grows,
  as phase7-final found (7,082 in `bench/run` after 30 s, 5,005 after 90 s). onCrack's does not fall (13,215 and 12,735). After
  90 s of posting, onCrack is 2.54x Rust.
- **Rows written equal the load generator's count** in every window.
- Server log lines equal the load generator's count exactly for Rust. onCrack's are 3-218 short at the window's end, which is the
  batched log's flush, the same as the port's.

**CPU per request:**
- At c=16, onCrack keeps 3.7 of the 4 server cores busy, against Rust's 3.5. It is CPU-bound, so the lead at c=16 is CPU per request.
- At c=1, onCrack's CPU per request on the read pages is level with Rust's: it spends 1.97 cores at one connection where Rust spends
  0.92. A cached hit costs about 30 µs of CPU, and the rest is the thread pool spinning between requests. That is the port's
  behaviour (unit 7.5), and onCrack has not changed it.

**Load average and host:**
- Every part waited for the VM's 1-minute load to fall below 1.5. It was at most 1.49 at every start.
- The host probe was ≤ 1.08 after all 288 measured windows, and none was flagged.

**Warm-up:** every run settled, except at the 90 s maximum in these cells:
- Rust and the port, post c=64 (all reps): the decline described above.
- onCrack, messages page c=1 and search c=1 (one rep each).
- The port, search c=1 (2 reps).
- Rust `/up` c=1 and Rails CSS c=1 (one rep each).

Measured / tail was 0.95-1.02 throughout.

**Durability:**
- onCrack runs with the defaults (`journal_mode=wal`, `synchronous=normal`, as Rails).
- Group commit is on with a 0 µs window, so every post commits before it is answered.
- No setting that weakens durability was used.

**Disk:** the Mac's free space fell to 4.7 GB during the parity slices, because of the WebKit core dump and VM disk growth. That is
under the 12 GB floor. The first reads-while-writing run was already under way. I deleted the dump, ran `bin/clean-docker` (back to
17 GB), and repeated the reads-while-writing check. Its second run agrees with the first within 3%.

**What I found:**
- The port's `/up` regression from unit 7.5 (note ² above). It is the port's, not one of the five workloads, and not fixed here.
- The cache-hit caveat on the read pages, quantified above.

Nothing in the five-workload numbers had to be changed.

## Where onCrack stands, plainly

- **Ahead of Rust and the port by more than 10%** on all five workloads at all three concurrencies. The smallest leads are post c=1:
  1.23x Rust and 1.12x the port.
- **Behind Rust:**
  - CPU per request at one connection: level on the read pages, 1.43x on posts (thread-pool spinning).
  - Memory: peak anon 3.0x and Cable Pss 5.9x.
  - Cold start: 1.8x. The opt-in AOT image (C4) is 98 ms, below Rust's.
  - Cable fan-out: 0.61-0.87x.
  - CPU per request on the cheap static routes: 1.4x.
- **Behind the port:** memory, by 9-15% (not broken down here; the read cache's page store is budgeted at 64 MB). Nothing else is.
- **Not re-measured here:** identity bodies, `bench/front`, `bench/cable/run`, and the AOT image (C4's numbers stand).

## Reproducing

All inside colima. Each app's rep runs in parts, one container per part, merged into the rep's file by `MERGE_PART=1`, so that every
part fits one foreground call. Each part runs 1-3 routes. Cable and upload run
in the rep's last part. Order: reference, rust, fsharp, oncrack in reps 1 and 3, reversed in rep 2.

```sh
CAMPFIRE_REVISION=$(git rev-parse HEAD) parity/bin/candidate build     # then bin/clean-docker from macOS
R=bench/results/oncrack-round1-final/review
$R/quiet.sh && $R/part.sh reference 1 'room_show messages_page'          # ... sidebar search | avatar static_css up | post_message
$R/quiet.sh && $R/part.sh oncrack 1 'post_message' 'http cable upload'   # the rep's last part
bench/report bench/results/oncrack-round1-final > bench/results/oncrack-round1-final/report.md
python3 bench/results/oncrack-round1-final/review/table.py
$R/manual.sh rust; $R/manual.sh oncrack; $R/mixed.sh rust|fsharp|oncrack; $R/bytes.sh
bin/pixel-parity --seeds crowd,custom_styles,first_run,restricted; bin/pixel-parity --seeds default --only 'realtime/**'   # ... ten slices
bench/quick log bench/results/oncrack-round1-final --unit round1-final --tier 3 --kept true --build sha256:3fd0dd609e3c --commit da1e92f --change "..."
```

`bin/verify` and the differentials were not re-run for this unit, which changes nothing under `src/`. The verifier-fix round
(`oncrack-fixes.md`) ran them on the same `src/`.
