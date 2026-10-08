```
date: 2026-10-08T17:16:13-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: DOTNET_ThreadPool_UnfairSemaphoreSpinLimit=0
user agent: (none)
oncrack image: campfire-oncrack:app sha256:390e390e43faa666e99cfbc3a6bcc161d9a1c3709c952c908f48f7a979638129 2026-10-08T15:17:46.141811435-04:00 built from commit: 09415ba6bddbaa5b9d4904edf426c9b1ecee4ca8
oncrack build: MOUNTED /var/tmp/campfire-mounted over /opt/campfire (e29ee2b (dirty files under src/: 1) at 2026-10-08T20:32:42Z)
repo HEAD: e29ee2b (dirty: 1 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 11:27:25), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: http; http secs 8, concs 1 2 4 16 64, routes post_message, warm-up 20s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 206 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 758 |
| peak anon under load (MB) | 180 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| post_message c=1 req/s | 4,898 |
| post_message c=1 CPU µs/req | 263 |
| post_message c=1 p50 ms | 0.18 |
| post_message c=1 p99 ms | 0.41 |
| post_message c=2 req/s | 7,994 |
| post_message c=2 CPU µs/req | 256 |
| post_message c=2 p50 ms | 0.21 |
| post_message c=2 p99 ms | 0.56 |
| post_message c=4 req/s | 8,079 |
| post_message c=4 CPU µs/req | 222 |
| post_message c=4 p50 ms | 0.31 |
| post_message c=4 p99 ms | 1.62 |
| post_message c=16 req/s | 15,817 |
| post_message c=16 CPU µs/req | 179 |
| post_message c=16 p50 ms | 0.88 |
| post_message c=16 p99 ms | 4.48 |
| post_message c=64 req/s | 17,806 |
| post_message c=64 CPU µs/req | 162 |
| post_message c=64 p50 ms | 3.15 |
| post_message c=64 p99 ms | 8.58 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.33 2.15 2.44 | 3.60 2.60 2.55 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.09 | 1.04 | 0/5 | 1.09 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | post_message | 436,810 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | post_message | 1 | 20.0 | 1/1 | 0.97 |
| onCrack | post_message | 2 | 20.0 | 1/1 | 1.00 |
| onCrack | post_message | 4 | 22.5 | 0/1 **←** | 1.14 |
| onCrack | post_message | 16 | 20.0 | 1/1 | 0.98 |
| onCrack | post_message | 64 | 20.0 | 1/1 | 1.01 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 90,666 | 90,666 | yes |
| onCrack | 1 | run c=1 | 39,185 | 39,185 | yes |
| onCrack | 1 | warm-up c=2 | 158,212 | 158,212 | yes |
| onCrack | 1 | run c=2 | 63,956 | 63,956 | yes |
| onCrack | 1 | warm-up c=4 | 152,189 | 152,189 | yes |
| onCrack | 1 | run c=4 | 64,631 | 64,631 | yes |
| onCrack | 1 | warm-up c=16 | 318,939 | 318,939 | yes |
| onCrack | 1 | run c=16 | 126,554 | 126,554 | yes |
| onCrack | 1 | warm-up c=64 | 350,497 | 350,497 | yes |
| onCrack | 1 | run c=64 | 142,484 | 142,484 | yes |
| onCrack | 1 | **all** | 1,507,313 | 1,507,313 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | 2,097 | – |
