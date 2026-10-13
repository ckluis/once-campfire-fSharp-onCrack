```
date: 2026-10-13T10:14:01-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:r5head sha256:bfcbb4633485c87c7c9bc9c11e7ad0a6a313d7f9bf900fa73da01b48569144f3 2026-10-12T18:32:41.82752305-04:00 built from commit: ee5a2e91795e7c8892757af2cf2561666c7c6e93
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
| cold start: docker run → /up 200 (ms) | 191 [190–276] |
| idle memory.current (MB) | 28.0 [28.0–28.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 707 [639–709] |
| peak anon under load (MB) | 175 [174–176] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| post_message c=1 req/s | 4,175 [3,376–4,934] |
| post_message c=1 CPU µs/req | 272 [259–291] |
| post_message c=1 p50 ms | 0.19 [0.18–0.20] |
| post_message c=1 p99 ms | 0.37 [0.32–1.05] |
| post_message c=16 req/s | 11,860 [10,178–12,224] |
| post_message c=16 CPU µs/req | 189 [187–189] |
| post_message c=16 p50 ms | 0.89 [0.88–0.89] |
| post_message c=16 p99 ms | 4.60 [4.56–4.91] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.29 2.02 2.19 | 2.33 2.15 2.21 |
| onCrack | 2 | 0.99 1.79 2.08 | 2.73 2.22 2.18 |
| onCrack | 3 | 1.33 1.92 2.08 | 2.48 2.14 2.13 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.08 | 1.06 | 0/2 | 1.09 |
| onCrack | 2 | 1.09 | 1.07 | 0/2 | 1.07 |
| onCrack | 3 | 1.07 | 1.08 | 0/2 | 1.05 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | post_message | 374,132 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | post_message | 1 | 30.0 [30.0–90.1] | 2/3 **←** | 1.01 |
| onCrack | post_message | 16 | 91.0 [90.6–92.6] | 0/3 **←** | 1.18 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 138,265 | 138,265 | yes |
| onCrack | 1 | run c=1 | 33,403 | 33,403 | yes |
| onCrack | 1 | warm-up c=16 | 912,113 | 912,113 | yes |
| onCrack | 1 | run c=16 | 97,935 | 97,935 | yes |
| onCrack | 1 | **all** | 1,181,716 | 1,181,716 | yes |
| onCrack | 2 | warm-up c=1 | 249,553 | 249,553 | yes |
| onCrack | 2 | run c=1 | 27,011 | 27,011 | yes |
| onCrack | 2 | warm-up c=16 | 1,012,717 | 1,012,717 | yes |
| onCrack | 2 | run c=16 | 81,428 | 81,428 | yes |
| onCrack | 2 | **all** | 1,370,709 | 1,370,709 | yes |
| onCrack | 3 | warm-up c=1 | 137,536 | 137,536 | yes |
| onCrack | 3 | run c=1 | 39,473 | 39,473 | yes |
| onCrack | 3 | warm-up c=16 | 1,098,269 | 1,098,269 | yes |
| onCrack | 3 | run c=16 | 94,882 | 94,882 | yes |
| onCrack | 3 | **all** | 1,370,160 | 1,370,160 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | 2,097 | – |
