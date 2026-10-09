```
date: 2026-10-09T10:38:54-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:prev sha256:e4927fa7ec95af4175e46ca11e2fed7fc3d30e4d08b96b964a7471f51bc4b40e 2026-10-09T09:37:43.982919747-04:00 built from commit: 87c1ad12e97b399c16b18ef457c9d546fa936564
repo HEAD: 2b412e5 (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 11:27:25), built with rust:1.98.1-trixie
seed: crowd (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: http; http secs 8, concs 1 16, routes search_spread, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 235 |
| idle memory.current (MB) | 30.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 348 |
| peak anon under load (MB) | 316 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| search_spread c=16 req/s (all lanes) | 23,944 |
| search_spread c=16 CPU µs/req (all lanes) | 148 |
| search_spread c=16 reads req/s | 23,944 |
| search_spread c=16 reads p50 ms | 0.64 |
| search_spread c=16 reads p99 ms | 2.21 |

Realistic workloads (bench/lib/realistic.py), seed `crowd`; lanes, their connections (c is the measured concurrency) and targets:

| Workload | Lane | Connections | Pick | Targets | Users |
|---|---|---|---|---|---|
| mixed | reads | c | cycle | 1 | 1 |
| mixed | posts | 1 | cycle | 1 | 1 |
| spread | reads | c | random | 2,112 | 525 |
| spread_mixed | reads | c | random | 2,112 | 525 |
| spread_mixed | posts | 1 | random | 108 | 31 |
| search_spread | reads | c | random | 104,800 | 524 |

Sign-in of the seed's people before the workloads, per rep: onCrack 31.4 s.

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.38 2.20 2.04 | 3.97 2.82 2.28 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.07 | 1.07 | 0/1 | 1.05 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | search_spread | 191,569 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | search_spread | 16 | 30.0 | 1/1 | 0.99 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | – | – |
