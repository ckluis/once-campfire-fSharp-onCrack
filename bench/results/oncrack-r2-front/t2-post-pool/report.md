```
date: 2026-10-08T14:41:07-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:12969a1861f3fdea4d8c87aeeca3656d2e2a6fd00ecbf94b4321d206484e0d2f 2026-10-08T12:53:21.14723596-04:00 built from commit: eae5bebb5f9fc2ccd7eccd9ea18f3ad85d687e92
oncrack build: MOUNTED /var/tmp/campfire-mounted over /opt/campfire (56452bf (dirty files under src/: 10) at 2026-10-08T18:32:15Z)
repo HEAD: 56452bf (dirty: 10 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 11:27:25), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: http; http secs 8, concs 1 16 64, routes post_message, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 258 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 849 |
| peak anon under load (MB) | 177 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| post_message c=1 req/s | 4,518 |
| post_message c=1 CPU µs/req | 396 |
| post_message c=1 p50 ms | 0.20 |
| post_message c=1 p99 ms | 0.39 |
| post_message c=16 req/s | 12,176 |
| post_message c=16 CPU µs/req | 186 |
| post_message c=16 p50 ms | 0.89 |
| post_message c=16 p99 ms | 4.65 |
| post_message c=64 req/s | 18,549 |
| post_message c=64 CPU µs/req | 154 |
| post_message c=64 p50 ms | 3.06 |
| post_message c=64 p99 ms | 10.1 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.28 2.44 2.45 | 3.82 2.94 2.63 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.05 | 1.06 | 0/3 | 1.08 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | post_message | 282,004 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | post_message | 1 | 30.0 | 1/1 | 0.99 |
| onCrack | post_message | 16 | 60.3 | 0/1 **←** | 1.18 |
| onCrack | post_message | 64 | 30.0 | 1/1 | 1.02 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 127,772 | 127,772 | yes |
| onCrack | 1 | run c=1 | 36,142 | 36,142 | yes |
| onCrack | 1 | warm-up c=16 | 815,482 | 815,482 | yes |
| onCrack | 1 | run c=16 | 97,419 | 97,419 | yes |
| onCrack | 1 | warm-up c=64 | 550,428 | 550,428 | yes |
| onCrack | 1 | run c=64 | 148,443 | 148,443 | yes |
| onCrack | 1 | **all** | 1,775,686 | 1,775,686 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | 2,097 | – |
