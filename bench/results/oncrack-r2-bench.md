# onCrack R2.0: making the benchmark tell the truth, 2026-10-08

Round 1 scored onCrack on five workloads. Each one repeats one URL as one user and never writes while it reads. So onCrack's
read cache answered every read from a stored page, and the 120-155k req/s and 4-5x Rust figures are a 100%-hit result. This unit
adds realistic workloads to the harness and records a same-session baseline of them for all four apps. It also measures whether
the top figures belong to the server or to the load generator. **No app code changed.** The images are round 1's final ones
(onCrack `da1e92f`, `sha256:3fd0dd609e3c`; `src/` has not changed since), so there was nothing to rebuild.

- Raw data: [`oncrack-r2-bench/`](oncrack-r2-bench/). It has one JSON per app and rep, `report.md` (`bench/report`, with every
  validity table) and `vs-stored.md` (`bench/quick compare`).
- Controls: [`oncrack-r2-bench/controls/`](oncrack-r2-bench/controls/), cache off and a 512 MB cache.
- Load generator ceiling: [`oncrack-r2-bench/ceiling/ceiling.jsonl`](oncrack-r2-bench/ceiling/ceiling.jsonl).
- Scripts: [`oncrack-r2-bench/review/`](oncrack-r2-bench/review/) (`part.sh`, `control.sh`, `ceiling.sh`, `quiet.sh`).

**Verdict**

- **The read cache's win is real when its working set fits, and absent when it doesn't.**
  - With one room being written to (`mixed`), onCrack reads 2.33x Rust and 1.79x the port, and posts 1.57x and 1.43x.
  - With requests spread over 525 people's pages (`spread`, read-only), onCrack is **0.95x the port** (1.11x Rust). The default
    64 MB cache does not hold the crowd seed's 2,112 pages, so it thrashes. Cache off lands exactly on the port. A 512 MB cache
    gives 127k req/s.
  - Posting into rooms 526 people read (`spread_mixed`) invalidates nearly everything. onCrack reads 0.97x the port and posts
    **0.86x the port**, and a bigger cache does not help.
  - Search over 524 users x 200 queries (`search_spread`) is 0.94x the port. onCrack's 2.10x Rust there is the port's search path
    (Rust spends 415 µs a search on varied queries), not the cache.
- **Geometric mean of the six realistic cells:** 1.44x Rust and **1.11x the port**. The five classic workloads gave 3.84x Rust
  and 2.89x the port at c=16.
- **The 120-155k figures are not tool-bound, but they are partly environment-bound.**
  - Giving the load generator a 4th core adds nothing at c=16 and 8% at c=64. Six cores is slower than four.
  - The same 4+4 CPU sets on a VM with two spare vCPUs make onCrack 9-17% faster (twice) and Rust 3-4% slower (against round 1's 8-vCPU medians).
  - The load generator costs 19-23 µs a request against onCrack's 24-30 µs. Its 4-core ceiling is about 170-210k req/s, so a
    faster hit path will soon be measuring the tool.
- **The run is sound:**
  - Every response was 200, with 0 connection errors. That covers the baseline's 40 windows, the controls' 8 and the ceiling's 32.
  - Rows written equal posts answered in every phase: 1,658 for Rails and 43-80k per rep for the others.
  - The host probe was ≤ 1.10 after every window except one Rails window (1.103).
  - Rust's `mixed` reads re-measured within 1% of round 1's hand-run `review/mixed.sh` (18,597 against 18,810 / 18,428).

## The realistic workloads

All four run on the **crowd seed** (`parity/.seed/crowd`: the default seed plus 520 members of the three open rooms). At the
start of each rep the harness signs in its 525 people (every active, non-bot user with an email address). Each sign-in comes
from its own `X-Forwarded-For` address, so the sign-in rate limit (Rails: 10 in 3 minutes per client) does not refuse them. The
sign-ins take 25-31 s.

Every request carries the cookie of the user it is for, over keep-alive connections. Measured connections are c=16 readers
(`REAL_CONCS`), and the post lanes keep their own single connection. Each workload gets the warm-up rule and the 8 s window that
bench/run uses for every route. The table is [`bench/lib/realistic.py`](../lib/realistic.py)'s:

| Workload | Reads | Writes | Targets |
|---|---|---|---|
| `mixed` | 16 connections read the busy room's page (`/rooms/<watercooler>`) as David | 1 connection posts into that room as David, as fast as the app answers | 1 page; round 1's `review/mixed.sh` as a workload |
| `spread` | 16 connections. Each request is a (user, page) drawn uniformly from every user's room pages (each room they belong to) and their sidebar | none | 2,112 pages of 525 users |
| `spread_mixed` | as `spread` | 1 connection posts as one of 31 users into one of their rooms, drawn uniformly (open rooms have 526 members) | 2,112 pages; 108 (user, room) posts |
| `search_spread` | 16 connections. Each request is `/searches?q=` with a user and a query drawn independently: 524 users x 200 words of the seed's messages | none | 104,800 (user, query) pages |

Two decisions, and why:

- **The Broken room is left out of the targets.** Its message's author is missing on purpose, as a parity case.
- **Lonely Lou is left out of `search_spread`.** He is the one user with no rooms. Rails' search page raises for him
  (`searches/index.html.erb:63`, `room_path(nil)`). The first Rails rep showed 16 such 500s in 6,069 answers, so I found
  the cause and re-ran that cell. Lou still reads his sidebar in `spread`.

How the harness uses them:

- `bench/quick --real` runs the four.
- `bench/run` takes them as route names (`HTTP_ROUTES="mixed spread spread_mixed search_spread"`). It refuses a part that mixes
  them with the classic routes, because the two need different seeds.
- `bench/report` prints each lane's req/s, p50 and p99.
- `bench/quick compare` prints the realistic workloads against this baseline.
- The load generator's new `http --mix-spec` runs the lanes. Its one-URL path is unchanged: re-measured, the room page and
  sidebar landed within 1-4% of round 1 (below).

## Same-session baseline

Req/s, median of 3 reps (Rails: 1 rep), c=16, with the server container's CPU µs per request over all lanes in brackets.
Measured 2026-10-08 06:16-07:18, in this order:

- rep 1: Rails, Rust, the port, onCrack
- rep 2: onCrack, the port, Rust
- rep 3: Rust, the port, onCrack

`SERVER_CPUS=0-3 LOADGEN_CPUS=4-7`, VM 8 vCPUs.

| Workload | lane | Rails | Rust | F# port | **onCrack** | **onCrack / Rust** | **onCrack / port** | port / Rust |
|---|---|---|---|---|---|---|---|---|
| mixed | reads | 219 | 18,597 | 24,232 | 43,283 [40,760-43,423] | **2.33x** | **1.79x** | 1.30x |
| mixed | posts | 30.5 | 688 | 753 | 1,079 [1,069-1,093] | **1.57x** | **1.43x** | 1.09x |
| mixed | CPU µs/req | (11,664) | (176) | (149) | (84.3) | 0.48x | 0.57x | |
| spread | reads | 589 | 25,655 | 29,902 | 28,547 [28,524-28,808] | **1.11x** | **0.95x** | 1.17x |
| spread | CPU µs/req | (5,102) | (143) | (125) | (134) | 0.94x | 1.07x | |
| spread_mixed | reads | 265 | 13,155 | 13,584 | 13,229 [13,054-13,253] | **1.01x** | **0.97x** | 1.03x |
| spread_mixed | posts | 5.8 | 319 | 393 | 337 [331-338] | **1.06x** | **0.86x** | 1.23x |
| spread_mixed | CPU µs/req | (10,740) | (268) | (274) | (284) | 1.06x | 1.04x | |
| search_spread | reads | 826 | 8,468 | 18,942 | 17,802 [17,388-17,808] | **2.10x** | **0.94x** | 2.24x |
| search_spread | CPU µs/req | (3,548) | (415) | (186) | (204) | 0.49x | 1.10x | |

Geometric mean of the six lane cells: onCrack 1.44x Rust and 1.11x the port; the port 1.30x Rust. The four read lanes alone:
1.53x Rust and 1.12x the port.

Latency, read p50 / p99 ms:

| Workload | Rust | F# port | onCrack |
|---|---|---|---|
| mixed | 0.84 / 1.78 | 0.66 / 1.56 | 0.20 / 1.11 |
| spread | 0.59 / 1.29 | 0.51 / 1.11 | 0.53 / 1.29 |
| spread_mixed | 1.14 / 2.78 | 1.08 / 2.94 | 1.11 / 3.15 |
| search_spread | 1.07 / 19.2 | 0.63 / 4.99 | 0.69 / 5.39 |

## Why, from two controls (onCrack, one rep each)

| Workload | lane | onCrack default (64 MB) | cache off | 512 MB cache | F# port |
|---|---|---|---|---|---|
| mixed | reads | 43,283 | 24,364 | 41,333 | 24,232 |
| mixed | posts | 1,079 | 772 | 1,073 | 753 |
| spread | reads | 28,547 (134 µs) | 29,916 (125 µs) | **127,399 (28.7 µs)** | 29,902 (125 µs) |
| spread_mixed | reads | 13,229 | 13,543 | 12,946 | 13,584 |
| spread_mixed | posts | 337 | 350 | 339 | 393 |
| search_spread | reads | 17,802 (204 µs) | 19,182 (185 µs) | 25,341 (148 µs) | 18,942 (186 µs) |

- **The miss path is the port's.** With the cache off, onCrack lands within 1% of the port on every read lane. That agrees with
  unit C1's tier 2 of `CAMPFIRE_READ_CACHE=off`.
- **`spread` is a capacity problem, not an invalidation problem.**
  - Nothing writes in `spread`, so every stored page stays valid until it is evicted.
  - The store is two generations of at most half of `CAMPFIRE_READ_CACHE_MB` each. Its cost counts an entry's key twice and its
    body twice (`ReadCache.fs`, `cost`).
  - At 64 MB, 2,112 pages do not fit. The cache keeps evicting what the next request needs, so its overhead (lookup, store,
    generation churn) is paid on every request: 9 µs and 5% of throughput against cache off.
  - At 512 MB they fit and `spread` serves at the classic room page's rate (127k, 28.7 µs).
- **`spread_mixed` is an invalidation problem, and more cache cannot fix it.**
  - Each post into an open room moves that room's version. Every page of that room, and the sidebar of every one of its 526
    members, depends on it.
  - At about 340 posts a second into three such rooms, almost no page lives long enough to be read twice.
  - This is Campfire's real data flow: a post does change every member's sidebar (unread state) and the room page. Whole-page
    caching cannot win here; finer-grained reuse could.
  - The post rate is the extreme end: one connection posting as fast as the app answers. A paced variant is deferred.
- **onCrack's posts into big rooms are slower than the port's.**
  - In `spread_mixed`, onCrack posts 0.86x the port. With the cache off it is 0.89x (350 against 393; one rep), so it is not the
    read cache's doing.
  - In `mixed` (a 3-member room), cache-off posts are level with the port (772 against 753).
  - So the difference is in onCrack's write path for posts that touch many members. Not investigated here.
- **`search_spread` is mostly misses even at 512 MB.** There are 104,800 (user, query) pages, and the key starts with the user.
  The 520 crowd members all belong to the same three rooms, so their results for a query are identical, but each is stored
  apart.
- **Rust and search.** Rust's search costs 415 µs here, against 125 µs on the classic workload's single query (`coffee`). The
  port's and onCrack's do not slow down that way (186-204 µs). The 2.1-2.2x over Rust on `search_spread` is the port's search
  path, which onCrack inherits.

## Is the top rate the server's or the load generator's?

onCrack only (plus one Rust run), the classic room page and sidebar at c=16 and c=64 on the default seed, one rep per
configuration. "Busy" is cores busy over the window (cgroup `cpu.stat` for the server, rusage for the load generator).

| VM vCPUs | server CPUs | loadgen CPUs | room c=16 | room c=64 | sidebar c=16 | sidebar c=64 | server busy | loadgen busy | loadgen µs/req |
|---|---|---|---|---|---|---|---|---|---|
| 8 | 0-3 (4) | 4-7 (4) | 122,915 | 133,021 | 138,080 | 157,526 | 3.71-3.78 | 2.74-3.06 | 19.0-23.0 |
| 8 | 0-3 (4) | 4-6 (3) | 127,545 | 123,113 | 139,659 | 145,301 | 3.83-3.90 | 2.74-2.79 | 19.2-22.7 |
| 8 | 0-3 (4) | 4-5 (2) | 100,211 | 97,790 | 115,700 | 113,821 | 3.77-3.84 | 1.88-1.89 | 16.3-19.3 |
| 8 | 0-2 (3) | 4-7 (4) | 115,036 | 121,744 | 130,927 | 145,875 | 2.88-2.94 | 2.57-2.63 | 18.0-22.3 |
| 10 | 0-3 (4) | 4-7 (4) | 136,975 | 154,983 | 150,636 | 174,309 | 3.59-3.82 | 3.14-3.51 | 20.2-23.5 |
| 10 | 0-3 (4) | 4-9 (6) | 116,633 | 140,626 | 136,385 | 165,289 | 3.47-3.64 | 3.06-3.57 | 20.7-26.2 |
| 10 | 0-3 (4) | 4-7 (4), again | 135,454 | 151,819 | 152,399 | 184,413 | 3.64-3.80 | 3.19-3.50 | 18.7-23.8 |
| 10, **Rust** | 0-3 (4) | 4-7 (4) | 27,578 | 28,188 | 27,160 | 27,676 | 3.55-3.58 | 0.81-0.95 | 29.7-33.9 |

What it says:

- **Not tool-bound at the harness's settings.**
  - With 2 cores the load generator is the limit: 1.89 of 2 busy, and the rate falls 19-28%.
  - From 3 cores to 4 the rate does not move at c=16 (127.5k → 122.9k, noise) and gains 8% at c=64.
  - On the 10-vCPU VM, 6 load generator cores are slower than 4 (117k against 135-137k at c=16). More threads spread 16
    connections over more vCPUs, which then compete with the host for its 10 cores.
- **Not linearly server-bound either.** Taking the server from 4 cores to 3 costs 5-9%, not 25%, and its CPU per request drops
  (30.2 → 25.5 µs).
  - "Cores busy" is not a saturation signal for onCrack. With the load generator on 2 cores, onCrack served 19% fewer requests
    yet still showed 3.82 cores busy (38 µs a request): idle threads spin.
- **The closed loop's round trip inside the VM is the binding limit.**
  - At c=16 a round trip is 16 / 123k = 130 µs, against 25-30 µs of server CPU and 19-23 µs of load generator CPU.
  - Two spare vCPUs (VM at 10, the same 4+4 pinning) raise onCrack 9-17% (both runs agree) and lower Rust 3-4% against round
    1's 8-vCPU medians. Rust is CPU-bound at 120-130 µs a request.
  - So on the 8-vCPU harness, onCrack's c=16/64 multiples over Rust are, if anything, understated. On the 10-vCPU VM the room
    page at c=16 would read about 4.9x Rust, against 4.3x.
  - I kept the 8-vCPU harness, which every stored baseline was measured on, and I do not claim the 10-vCPU ratios (one Rust rep).
- **Headroom is thin.** At 19-23 µs a request, 4 load generator cores top out around 170-210k req/s at full use. Any further gain
  on onCrack's hit path will hit that before it shows. A cheaper load generator is listed below.

The VM ran at 10 vCPUs only for the rows that say so, and was restored to 8 (`colima start --cpu 8 --memory 6`) before this
write-up. `nproc` is 8.

## Logging

- **The baseline is logged.** `bench/quick log ... --tier 3 --build sha256:3fd0dd609e3c --commit da1e92f` records the image's
  commit. It joins round 1's dot (same build) instead of adding one, and the climb chart's five-workload geometric mean is
  unchanged (3.824x Rust, 2.935x the port).
- **The controls and ceiling runs are not logged.** They are configuration and environment experiments of the same build.
  Logged under its commit, they would overwrite the dot's room page and sidebar values with 3-core and 10-vCPU numbers.

## The review (assume it is wrong until shown otherwise)

- **Image provenance:** `env.txt` records the same four image digests as round 1's final run, and `git status` was clean under
  `src/` and `rust/`.
  - `env.txt` says `repo HEAD: 2ed2e5e`, the tooling commit. Everything after Rails' first part ran on `cb971af`'s
    `realistic.py`, which differs only in leaving Lou out of `search_spread`. Rails' `search_spread` was re-run under it and
    replaced in `reference-1.json`.
- **Statuses:** every measured window of every app was all 200 with 0 connection errors. The ceiling runs were too.
- **Rows:** every `mixed` and `spread_mixed` warm-up and window wrote exactly as many messages as its posts lane had answered.
  The count covers every room of the app's own SQLite file.
- **Warm-up:**
  - Rails' `spread_mixed` (90 s) and Rust's `mixed` (90 s, all 3 reps) did not settle. Rust's posting rate falls as the room
    grows, as phase 7 found. Measured / tail was 0.95-1.02 throughout (0.95: Rust's `search_spread`).
  - Every .NET cell settled at the 30 s minimum.
- **Host:** every part started below a 1-minute load of 1.5, with a host probe of 1.02-1.08. One window probed above 1.10 (Rails'
  `mixed`, 1.103), and Rails' numbers are 10-200x below the others' anyway.
- **Too good to be true?** The one big number here is the 512 MB `spread` (127k). It is the classic room page's rate (124k) on
  pages that, once stored, nothing invalidates. Its CPU per request (28.7 µs) matches a hit's. Every other onCrack number in
  this unit is within 5% of the port's, or explained by the cache-off control.
- **The load generator:** I rebuilt it with the mix mode. Its one-URL path, re-measured on the 8-vCPU 4+4 configuration, gave
  122.9k / 133.0k / 138.1k / 157.5k against round 1's 123.9k / 128.4k / 138.2k / 154.9k medians.
- **Disk:** the Mac had 15 GB free at the start and 20 GB at the end (the VM restart returned some). No image was rebuilt, so
  `bin/clean-docker` had nothing to clean.

## Deferred (the improvement areas this baseline points at, for the next units)

1. **Read cache budget and costing** (`spread`: 0.95x the port).
   - The 64 MB default does not hold 525 people's pages, and an entry costs its body twice.
   - Options: size by measured bytes (body plus the actual gzip member), raise the default, or make it adaptive.
   - The 512 MB control shows the ceiling: 127k.
2. **A cache that thrashes should cost nothing.** On misses onCrack is 5-9% slower than with the cache off (`spread` 134 against
   125 µs, `search_spread` 204 against 185 µs). Admission control (store on a second miss, or a frequency sketch) would make a
   too-small cache harmless.
3. **onCrack's post path into big rooms** is 0.86x the port in `spread_mixed` (0.89x with the cache off). Find which per-member
   work onCrack adds: version bumps per membership, broadcast ordering, group commit with one poster.
4. **Share what is the same across users.** The 520 crowd members have identical room sets, so search results (and the message
   list of a room page) per (query or room, room-set version) could be shared instead of stored per user. That is the only way
   `search_spread` (104,800 keys) and `spread_mixed` (invalidated per post) can gain.
5. **A cheaper load generator.**
   - At 19-23 µs a request it costs three quarters of an onCrack hit, and its 4-core ceiling (about 170-210k) is close.
   - Pre-serialized requests over plain sockets would leave room to measure further hit-path gains.
   - It must be re-measured against all four apps, because the instrument changes.
6. **A paced-writes variant** (for example 5-20 posts a second spread over the rooms). This is a team chatting, not one
   connection posting flat out. It shows the cache under realistic churn once item 1 is done. It needs a `rate` per lane in
   the load generator.
7. **The project page does not show the realistic workloads yet.** The data files it would cite are in `oncrack-r2-bench/`.
8. **Rails' search page raises for a user with no rooms.** I did not check what Rust, the port and onCrack answer for Lou's
   search. If they answer 200, that is a known difference worth recording; if 500, a bug they copied.
9. **The harness VM** is 8 vCPUs on a 10-core host (4 performance, 6 efficiency). At onCrack's rates, VM scheduling co-limits
   the result (above). Any change to it must re-baseline every app.

## Reproducing

All inside colima (8 vCPUs), from the repo root:

```sh
R=bench/results/oncrack-r2-bench/review
$R/quiet.sh && $R/part.sh reference 1          # then rust 1, fsharp 1, oncrack 1; oncrack 2, fsharp 2, rust 2; rust 3, fsharp 3, oncrack 3
$R/part.sh reference 1 search_spread           # a single workload, merged into the rep's file
bench/report bench/results/oncrack-r2-bench > bench/results/oncrack-r2-bench/report.md
python3 bench/lib/quicklog.py compare bench/results/oncrack-r2-bench > bench/results/oncrack-r2-bench/vs-stored.md
$R/control.sh cache-off mixed,spread,spread_mixed,search_spread CAMPFIRE_READ_CACHE=off
$R/control.sh cache-512mb spread,search_spread CAMPFIRE_READ_CACHE_MB=512    # MERGE_PART=1 ... mixed,spread_mixed for the rest
$R/ceiling.sh vm8-s4-l4 0-3 4-7; $R/ceiling.sh vm8-s4-l3 0-3 4-6; $R/ceiling.sh vm8-s4-l2 0-3 4-5; $R/ceiling.sh vm8-s3-l4 0-2 4-7
# colima stop; colima start --cpu 10 --memory 6  (from macOS), then:
$R/ceiling.sh vm10-s4-l4 0-3 4-7; $R/ceiling.sh vm10-s4-l6 0-3 4-9; $R/ceiling.sh vm10-s4-l4-again 0-3 4-7; APP=rust $R/ceiling.sh vm10-s4-l4-rust 0-3 4-7
# colima stop; colima start --cpu 8 --memory 6
bench/quick log bench/results/oncrack-r2-bench --unit r2-bench --tier 3 --kept true --build sha256:3fd0dd609e3c --commit da1e92f --change "..."
```

`bin/verify` was not run: this unit changes nothing under `src/` or `tests/`. The load generator built cleanly in
`rust:1.98.1-trixie`. `bench/report` on round 1's directory reproduces its stored `report.md` except for one renamed heading.
