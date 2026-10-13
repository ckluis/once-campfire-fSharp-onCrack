```
date: 2026-10-08T06:40:44-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: CAMPFIRE_READ_CACHE_MB=512
user agent: (none)
oncrack image: campfire-oncrack:app sha256:3fd0dd609e3ccca63edac303f0f2c0098052ecf10e090e48da4b99694d452775 2026-10-07T18:06:59.581414571-04:00 built from commit: da1e92f56d59f65de6d3225a503e49d6bc06fed6
repo HEAD: cb971af (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 06:11:29), built with rust:1.98.1-trixie
seed: crowd (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: http; http secs 8, concs 1 16, routes spread search_spread, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 238 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 770 |
| peak anon under load (MB) | 738 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| spread c=16 req/s (all lanes) | 127,399 |
| spread c=16 CPU µs/req (all lanes) | 28.7 |
| spread c=16 reads req/s | 127,399 |
| spread c=16 reads p50 ms | 0.11 |
| spread c=16 reads p99 ms | 0.39 |
| search_spread c=16 req/s (all lanes) | 25,340 |
| search_spread c=16 CPU µs/req (all lanes) | 148 |
| search_spread c=16 reads req/s | 25,340 |
| search_spread c=16 reads p50 ms | 0.61 |
| search_spread c=16 reads p99 ms | 1.55 |
| mixed c=16 req/s (all lanes) | 42,407 |
| mixed c=16 CPU µs/req (all lanes) | 86.3 |
| mixed c=16 posts req/s | 1,073 |
| mixed c=16 posts p50 ms | 0.86 |
| mixed c=16 posts p99 ms | 2.41 |
| mixed c=16 reads req/s | 41,333 |
| mixed c=16 reads p50 ms | 0.24 |
| mixed c=16 reads p99 ms | 1.16 |
| spread_mixed c=16 req/s (all lanes) | 13,285 |
| spread_mixed c=16 CPU µs/req (all lanes) | 291 |
| spread_mixed c=16 posts req/s | 339 |
| spread_mixed c=16 posts p50 ms | 2.61 |
| spread_mixed c=16 posts p99 ms | 7.46 |
| spread_mixed c=16 reads req/s | 12,946 |
| spread_mixed c=16 reads p50 ms | 1.12 |
| spread_mixed c=16 reads p99 ms | 4.25 |

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
| onCrack | 1 | 1.39 3.23 2.90 | 4.19 3.61 3.68 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.06 | 1.06 | 0/4 | 1.07 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | spread | 1,019,252 | 0 | 0 | 0 | 0 |
| onCrack | search_spread | 202,741 | 0 | 0 | 0 | 0 |
| onCrack | mixed | 339,271 | 0 | 0 | 0 | 0 |
| onCrack | spread_mixed | 106,300 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | spread | 16 | 30.0 | 1/1 | 0.99 |
| onCrack | search_spread | 16 | 30.0 | 1/1 | 1.00 |
| onCrack | mixed | 16 | 30.0 | 1/1 | 0.97 |
| onCrack | spread_mixed | 16 | 30.0 | 1/1 | 0.99 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | mixed warm-up c=16 | 31,753 | 31,753 | yes |
| onCrack | 1 | mixed run c=16 | 8,588 | 8,588 | yes |
| onCrack | 1 | spread_mixed warm-up c=16 | 9,995 | 9,995 | yes |
| onCrack | 1 | spread_mixed run c=16 | 2,715 | 2,715 | yes |
| onCrack | 1 | **all** | 53,051 | 53,051 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | – | – |
