```
date: 2026-10-13T09:53:08-04:00
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
| cold start: docker run → /up 200 (ms) | 239 [234–281] |
| idle memory.current (MB) | 29.0 [28.0–29.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 685 [677–728] |
| peak anon under load (MB) | 175 [173–175] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| post_message c=1 req/s | 4,967 [4,958–4,996] |
| post_message c=1 CPU µs/req | 258 [256–258] |
| post_message c=1 p50 ms | 0.18 [0.18–0.18] |
| post_message c=1 p99 ms | 0.33 [0.32–0.34] |
| post_message c=16 req/s | 11,743 [10,566–12,895] |
| post_message c=16 CPU µs/req | 185 [182–189] |
| post_message c=16 p50 ms | 0.87 [0.86–0.89] |
| post_message c=16 p99 ms | 4.55 [4.33–4.70] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.34 2.23 2.37 | 3.21 2.50 2.44 |
| onCrack | 2 | 1.32 2.09 2.30 | 3.31 2.63 2.47 |
| onCrack | 3 | 1.39 2.21 2.33 | 3.18 2.52 2.42 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.05 | 1.04 | 0/2 | 1.07 |
| onCrack | 2 | 1.07 | 1.04 | 0/2 | 1.06 |
| onCrack | 3 | 1.06 | 1.10 | 0/2 | 1.06 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | post_message | 401,591 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | post_message | 1 | 30.0 [30.0–30.0] | 3/3 | 1.02 |
| onCrack | post_message | 16 | 91.5 [90.9–91.5] | 0/3 **←** | 1.11 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 136,850 | 136,850 | yes |
| onCrack | 1 | run c=1 | 39,664 | 39,664 | yes |
| onCrack | 1 | warm-up c=16 | 1,025,097 | 1,025,097 | yes |
| onCrack | 1 | run c=16 | 93,957 | 93,957 | yes |
| onCrack | 1 | **all** | 1,295,568 | 1,295,568 | yes |
| onCrack | 2 | warm-up c=1 | 134,873 | 134,873 | yes |
| onCrack | 2 | run c=1 | 39,967 | 39,967 | yes |
| onCrack | 2 | warm-up c=16 | 1,145,320 | 1,145,320 | yes |
| onCrack | 2 | run c=16 | 103,733 | 103,733 | yes |
| onCrack | 2 | **all** | 1,423,893 | 1,423,893 | yes |
| onCrack | 3 | warm-up c=1 | 134,953 | 134,953 | yes |
| onCrack | 3 | run c=1 | 39,734 | 39,734 | yes |
| onCrack | 3 | warm-up c=16 | 1,029,970 | 1,029,970 | yes |
| onCrack | 3 | run c=16 | 84,536 | 84,536 | yes |
| onCrack | 3 | **all** | 1,289,193 | 1,289,193 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | 2,096 | – |
