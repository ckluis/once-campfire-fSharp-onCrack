```
date: 2026-10-08T11:42:00-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: CAMPFIRE_GZIP_LIBDEFLATE=off
user agent: (none)
oncrack image: campfire-oncrack:app sha256:449b485c8a0eebd20640ffdd0612e973f49f38e44466855082c36a6388ca7a65 2026-10-08T09:06:39.370441452-04:00 built from commit: 72ddf9f758d99fc81e626ac734ae0fc752ab2393
oncrack build: MOUNTED /var/tmp/campfire-mounted over /opt/campfire (564a162 (dirty files under src/: 4) at 2026-10-08T15:39:15Z)
repo HEAD: 564a162 (dirty: 4 files under src/ and rust/)
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
| cold start: docker run → /up 200 (ms) | 250 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 818 |
| peak anon under load (MB) | 286 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| post_message c=1 req/s | 4,198 |
| post_message c=1 CPU µs/req | 446 |
| post_message c=1 p50 ms | 0.21 |
| post_message c=1 p99 ms | 0.42 |
| post_message c=16 req/s | 10,861 |
| post_message c=16 CPU µs/req | 218 |
| post_message c=16 p50 ms | 0.92 |
| post_message c=16 p99 ms | 5.43 |
| post_message c=64 req/s | 19,322 |
| post_message c=64 CPU µs/req | 180 |
| post_message c=64 p50 ms | 2.93 |
| post_message c=64 p99 ms | 9.38 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.43 1.97 2.13 | 6.74 3.48 2.64 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.09 | 1.06 | 0/3 | 1.06 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | post_message | 275,118 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | post_message | 1 | 30.0 | 1/1 | 1.00 |
| onCrack | post_message | 16 | 31.6 | 0/1 **←** | 0.95 |
| onCrack | post_message | 64 | 30.0 | 1/1 | 1.00 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 118,097 | 118,097 | yes |
| onCrack | 1 | run c=1 | 33,589 | 33,589 | yes |
| onCrack | 1 | warm-up c=16 | 385,001 | 385,001 | yes |
| onCrack | 1 | run c=16 | 86,895 | 86,895 | yes |
| onCrack | 1 | warm-up c=64 | 587,204 | 587,204 | yes |
| onCrack | 1 | run c=64 | 154,634 | 154,634 | yes |
| onCrack | 1 | **all** | 1,365,420 | 1,365,420 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | 1,994 | – |
