```
date: 2026-10-08T15:10:04-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: CAMPFIRE_INLINE=replays
user agent: (none)
oncrack image: campfire-oncrack:app sha256:12969a1861f3fdea4d8c87aeeca3656d2e2a6fd00ecbf94b4321d206484e0d2f 2026-10-08T12:53:21.14723596-04:00 built from commit: eae5bebb5f9fc2ccd7eccd9ea18f3ad85d687e92
oncrack build: MOUNTED /var/tmp/campfire-mounted over /opt/campfire (56452bf (dirty files under src/: 11) at 2026-10-08T19:05:14Z)
repo HEAD: 56452bf (dirty: 11 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 11:27:25), built with rust:1.98.1-trixie
seed: crowd (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: http; http secs 8, concs 1 16, routes mixed spread spread_mixed search_spread, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 231 |
| idle memory.current (MB) | 29.0 |
| idle anon (MB) | 16.0 |
| peak memory.current under load (MB) | 668 |
| peak anon under load (MB) | 579 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| mixed c=16 req/s (all lanes) | 47,188 |
| mixed c=16 CPU µs/req (all lanes) | 77.6 |
| mixed c=16 posts req/s | 1,380 |
| mixed c=16 posts p50 ms | 0.66 |
| mixed c=16 posts p99 ms | 1.90 |
| mixed c=16 reads req/s | 45,807 |
| mixed c=16 reads p50 ms | 0.19 |
| mixed c=16 reads p99 ms | 1.26 |
| spread c=16 req/s (all lanes) | 94,497 |
| spread c=16 CPU µs/req (all lanes) | 38.2 |
| spread c=16 reads req/s | 94,497 |
| spread c=16 reads p50 ms | 0.08 |
| spread c=16 reads p99 ms | 1.03 |
| spread_mixed c=16 req/s (all lanes) | 11,962 |
| spread_mixed c=16 CPU µs/req (all lanes) | 324 |
| spread_mixed c=16 posts req/s | 671 |
| spread_mixed c=16 posts p50 ms | 1.36 |
| spread_mixed c=16 posts p99 ms | 4.57 |
| spread_mixed c=16 reads req/s | 11,291 |
| spread_mixed c=16 reads p50 ms | 1.33 |
| spread_mixed c=16 reads p99 ms | 4.12 |
| search_spread c=16 req/s (all lanes) | 16,732 |
| search_spread c=16 CPU µs/req (all lanes) | 223 |
| search_spread c=16 reads req/s | 16,732 |
| search_spread c=16 reads p50 ms | 0.63 |
| search_spread c=16 reads p99 ms | 7.57 |

Realistic workloads (bench/lib/realistic.py), seed `crowd`; lanes, their connections (c is the measured concurrency) and targets:

| Workload | Lane | Connections | Pick | Targets | Users |
|---|---|---|---|---|---|
| mixed | reads | c | cycle | 1 | 1 |
| mixed | posts | 1 | cycle | 1 | 1 |
| spread | reads | c | random | 2,112 | 525 |
| spread_mixed | reads | c | random | 2,112 | 525 |
| spread_mixed | posts | 1 | random | 108 | 31 |
| search_spread | reads | c | random | 104,800 | 524 |

Sign-in of the seed's people before the workloads, per rep: onCrack 31.2 s.

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.32 2.36 2.91 | 5.68 4.21 3.54 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.04 | 1.05 | 0/4 | 1.08 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | mixed | 377,531 | 0 | 0 | 0 | 0 |
| onCrack | spread | 756,016 | 0 | 0 | 0 | 0 |
| onCrack | spread_mixed | 95,711 | 0 | 0 | 0 | 0 |
| onCrack | search_spread | 133,865 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | mixed | 16 | 34.0 | 1/1 | 1.01 |
| onCrack | spread | 16 | 30.0 | 1/1 | 1.01 |
| onCrack | spread_mixed | 16 | 30.0 | 1/1 | 0.98 |
| onCrack | search_spread | 16 | 30.1 | 1/1 | 0.98 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | mixed warm-up c=16 | 45,283 | 45,283 | yes |
| onCrack | 1 | mixed run c=16 | 11,045 | 11,045 | yes |
| onCrack | 1 | spread_mixed warm-up c=16 | 20,360 | 20,360 | yes |
| onCrack | 1 | spread_mixed run c=16 | 5,368 | 5,368 | yes |
| onCrack | 1 | **all** | 82,056 | 82,056 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | – | – |
