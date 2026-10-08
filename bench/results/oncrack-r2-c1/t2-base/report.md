```
date: 2026-10-08T16:27:16-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:390e390e43faa666e99cfbc3a6bcc161d9a1c3709c952c908f48f7a979638129 2026-10-08T15:17:46.141811435-04:00 built from commit: 09415ba6bddbaa5b9d4904edf426c9b1ecee4ca8
oncrack build: MOUNTED /var/tmp/campfire-mounted over /opt/campfire (e29ee2b (dirty files under src/: 0) at 2026-10-08T20:24:33Z)
repo HEAD: e29ee2b (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 11:27:25), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: http; http secs 8, concs 1, routes room_show avatar static_css up post_message, warm-up 15s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 200 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 276 |
| peak anon under load (MB) | 172 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 26,402 |
| room_show c=1 CPU µs/req | 18.7 |
| room_show c=1 p50 ms | 0.04 |
| room_show c=1 p99 ms | 0.05 |
| avatar c=1 req/s | 28,914 |
| avatar c=1 CPU µs/req | 16.0 |
| avatar c=1 p50 ms | 0.03 |
| avatar c=1 p99 ms | 0.05 |
| static_css c=1 req/s | 30,528 |
| static_css c=1 CPU µs/req | 14.6 |
| static_css c=1 p50 ms | 0.03 |
| static_css c=1 p99 ms | 0.04 |
| up c=1 req/s | 19,156 |
| up c=1 CPU µs/req | 105 |
| up c=1 p50 ms | 0.05 |
| up c=1 p99 ms | 0.08 |
| post_message c=1 req/s | 4,741 |
| post_message c=1 CPU µs/req | 393 |
| post_message c=1 p50 ms | 0.18 |
| post_message c=1 p99 ms | 0.40 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 0.51 1.64 2.77 | 1.35 1.51 2.55 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.05 | 1.05 | 0/5 | 1.08 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 211,221 | 0 | 0 | 0 | 0 |
| onCrack | avatar | 231,310 | 0 | 0 | 0 | 0 |
| onCrack | static_css | 244,223 | 0 | 0 | 0 | 0 |
| onCrack | up | 153,248 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 37,931 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 16.0 | 1/1 | 1.01 |
| onCrack | avatar | 1 | 16.0 | 1/1 | 1.00 |
| onCrack | static_css | 1 | 16.0 | 1/1 | 1.00 |
| onCrack | up | 1 | 16.0 | 1/1 | 1.00 |
| onCrack | post_message | 1 | 16.0 | 1/1 | 0.97 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 74,537 | 74,537 | yes |
| onCrack | 1 | run c=1 | 37,931 | 37,931 | yes |
| onCrack | 1 | **all** | 112,468 | 112,468 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | – | – |
| avatar | 200 3,368 / 3,364 | 200 3,364 | – | – |
| static_css | 200 651 / 1,218 | 200 1,218 | – | – |
| up | 200 82 / 73 | 200 73 | – | – |
| post_message | – | – | – | – |
