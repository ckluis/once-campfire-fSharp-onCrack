```
date: 2026-10-13T10:04:22-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:r3final sha256:e34e485ff87ddd3d1fdb7f5dbebe6f2a1a563b3b8f6ccb5f403f31b6fbc753a4 2026-10-13T04:46:33.001661448-04:00 built from commit: 37c5988
repo HEAD: 3e6a300 (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-10 23:47:11), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 3; suites: http; http secs 8, concs 1 16, routes post_message, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 3. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 243 [205–264] |
| idle memory.current (MB) | 28.0 [28.0–28.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 687 [424–698] |
| peak anon under load (MB) | 174 [171–177] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| post_message c=1 req/s | 3,362 [3,328–4,928] |
| post_message c=1 CPU µs/req | 272 [261–302] |
| post_message c=1 p50 ms | 0.19 [0.18–0.20] |
| post_message c=1 p99 ms | 0.36 [0.31–0.80] |
| post_message c=16 req/s | 8,808 [8,291–11,993] |
| post_message c=16 CPU µs/req | 187 [186–207] |
| post_message c=16 p50 ms | 0.88 [0.88–0.95] |
| post_message c=16 p99 ms | 4.74 [4.58–4.79] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.38 2.12 2.28 | 2.45 2.32 2.34 |
| onCrack | 2 | 1.38 2.06 2.25 | 3.63 2.65 2.42 |
| onCrack | 3 | 1.31 2.15 2.26 | 3.03 2.41 2.32 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.05 | 1.08 | 0/2 | 1.08 |
| onCrack | 2 | 1.08 | 1.14 | 0/2 | 1.08 |
| onCrack | 3 | 1.07 | 1.05 | 0/2 | 1.07 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | post_message | 326,764 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | post_message | 1 | 30.0 [30.0–92.0] | 2/3 **←** | 1.01 |
| onCrack | post_message | 16 | 90.2 [53.3–91.6] | 1/3 **←** | 0.94 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 90,050 | 90,050 | yes |
| onCrack | 1 | run c=1 | 26,895 | 26,895 | yes |
| onCrack | 1 | warm-up c=16 | 384,964 | 384,964 | yes |
| onCrack | 1 | run c=16 | 66,348 | 66,348 | yes |
| onCrack | 1 | **all** | 568,257 | 568,257 | yes |
| onCrack | 2 | warm-up c=1 | 288,147 | 288,147 | yes |
| onCrack | 2 | run c=1 | 26,626 | 26,626 | yes |
| onCrack | 2 | warm-up c=16 | 918,563 | 918,563 | yes |
| onCrack | 2 | run c=16 | 71,457 | 71,457 | yes |
| onCrack | 2 | **all** | 1,304,793 | 1,304,793 | yes |
| onCrack | 3 | warm-up c=1 | 137,250 | 137,250 | yes |
| onCrack | 3 | run c=1 | 39,429 | 39,429 | yes |
| onCrack | 3 | warm-up c=16 | 1,065,655 | 1,065,655 | yes |
| onCrack | 3 | run c=16 | 96,009 | 96,009 | yes |
| onCrack | 3 | **all** | 1,338,343 | 1,338,343 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | 2,096 | – |
