```
date: 2026-10-08T13:14:42-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:12969a1861f3fdea4d8c87aeeca3656d2e2a6fd00ecbf94b4321d206484e0d2f 2026-10-08T12:53:21.14723596-04:00 built from commit: eae5bebb5f9fc2ccd7eccd9ea18f3ad85d687e92
fsharp image: campfire-fsharp:app sha256:421f335c3ff8ee640991228ffe18bb750f2a37a4bd5ad9da64e0a0da5cb1ae0c 2026-10-07T04:18:34.342866793-04:00 built from commit: 2e6c08e242191cb9c982ecc0f2c06e56d2e9855e
rust image: campfire-rust:app sha256:d582a01d3a4ae9c5fd4bc9cd7b0262e1a5d4440cc0058d200b50ad9b27e1365c 2026-10-05T23:48:02.375329666-04:00 built from commit: 
repo HEAD: eae5beb (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 11:27:25), built with rust:1.98.1-trixie
seed: crowd (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 500, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack,fsharp,rust, reps 1; suites: http; http secs 8, concs 1 16, routes mixed, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: rust 1, fsharp 1, oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | Rust | F# | onCrack | F# adv. | onCrack adv. | onCrack / F# |
|---|---|---|---|---|---|---|
| cold start: docker run → /up 200 (ms) | 156 | 409 | 200 | 0.38× | 0.78× | 2.04× |
| idle memory.current (MB) | 18.0 | 27.0 | 28.0 | 0.67× | 0.64× | 0.96× |
| idle anon (MB) | 15.0 | 15.0 | 15.0 | 1.00× | 1.00× | 1.00× |
| peak memory.current under load (MB) | 214 | 475 | 356 | 0.45× | 0.60× | 1.33× |
| peak anon under load (MB) | 164 | 404 | 284 | 0.41× | 0.58× | 1.42× |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | Rust | F# | onCrack | F# adv. | onCrack adv. | onCrack / F# |
|---|---|---|---|---|---|---|
| mixed c=16 req/s (all lanes) | 21,241 | 29,627 | 93,052 | 1.39× | 4.38× | 3.14× |
| mixed c=16 CPU µs/req (all lanes) | 162 | 125 | 39.6 | 1.30× | 4.08× | 3.15× |
| mixed c=16 posts req/s | 500 | 500 | 500 | 1.00× | 1.00× | 1.00× |
| mixed c=16 posts p50 ms | 1.39 | 1.25 | 0.72 | 1.12× | 1.93× | 1.73× |
| mixed c=16 posts p99 ms | 2.53 | 3.22 | 1.76 | 0.79× | 1.43× | 1.83× |
| mixed c=16 reads req/s | 20,742 | 29,127 | 92,552 | 1.40× | 4.46× | 3.18× |
| mixed c=16 reads p50 ms | 0.72 | 0.44 | 0.11 | 1.63× | 6.71× | 4.11× |
| mixed c=16 reads p99 ms | 1.68 | 1.32 | 0.81 | 1.27× | 2.07× | 1.63× |

Realistic workloads (bench/lib/realistic.py), seed `crowd`; lanes, their connections (c is the measured concurrency) and targets:

| Workload | Lane | Connections | Pick | Targets | Users |
|---|---|---|---|---|---|
| mixed | reads | c | cycle | 1 | 1 |
| mixed | posts | 1 | cycle | 1 | 1 |
| spread | reads | c | random | 2,112 | 525 |
| spread_mixed | reads | c | random | 2,112 | 525 |
| spread_mixed | posts | 1 | random | 108 | 31 |
| search_spread | reads | c | random | 104,800 | 524 |

Sign-in of the seed's people before the workloads, per rep: Rust 24.7 s, F# 31.2 s, onCrack 31.2 s.

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| Rust | 1 | 1.37 2.38 2.40 | 4.54 3.18 2.68 |
| F# | 1 | 1.31 2.43 2.39 | 3.81 2.94 2.57 |
| onCrack | 1 | 1.36 2.43 2.34 | 4.41 3.10 2.58 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| Rust | 1 | 1.05 | 1.06 | 0/1 | 1.05 |
| F# | 1 | 1.07 | 1.07 | 0/1 | 1.05 |
| onCrack | 1 | 1.06 | 1.07 | 0/1 | 1.07 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| Rust | mixed | 169,948 | 0 | 0 | 0 | 0 |
| F# | mixed | 237,034 | 0 | 0 | 0 | 0 |
| onCrack | mixed | 744,560 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| Rust | mixed | 16 | 30.0 | 1/1 | 0.96 |
| F# | mixed | 16 | 30.0 | 1/1 | 1.00 |
| onCrack | mixed | 16 | 30.0 | 1/1 | 1.01 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| Rust | 1 | mixed warm-up c=16 | 15,000 | 15,000 | yes |
| Rust | 1 | mixed run c=16 | 4,000 | 4,000 | yes |
| Rust | 1 | **all** | 19,000 | 19,000 | yes |
| F# | 1 | mixed warm-up c=16 | 15,000 | 15,000 | yes |
| F# | 1 | mixed run c=16 | 4,000 | 4,000 | yes |
| F# | 1 | **all** | 19,000 | 19,000 | yes |
| onCrack | 1 | mixed warm-up c=16 | 15,000 | 15,000 | yes |
| onCrack | 1 | mixed run c=16 | 4,000 | 4,000 | yes |
| onCrack | 1 | **all** | 19,000 | 19,000 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | Rust gzip wire / decoded | F# gzip wire / decoded | onCrack gzip wire / decoded | Rust identity | F# identity | onCrack identity | Rust c=16 avg | F# c=16 avg | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|---|---|---|---|---|---|
| post_message | – | – | – | – | – | – | – | – | – | –; – |
