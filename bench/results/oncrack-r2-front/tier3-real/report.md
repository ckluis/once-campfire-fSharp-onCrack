```
date: 2026-10-08T15:47:38-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:390e390e43faa666e99cfbc3a6bcc161d9a1c3709c952c908f48f7a979638129 2026-10-08T15:17:46.141811435-04:00 built from commit: 09415ba6bddbaa5b9d4904edf426c9b1ecee4ca8
repo HEAD: 09415ba (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 11:27:25), built with rust:1.98.1-trixie
seed: crowd (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 3; suites: http; http secs 8, concs 1 16, routes mixed spread spread_mixed search_spread, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 3. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 212 [202–225] |
| idle memory.current (MB) | 28.0 [28.0–28.0] |
| idle anon (MB) | 15.0 [15.0–16.0] |
| peak memory.current under load (MB) | 688 [683–826] |
| peak anon under load (MB) | 600 [579–714] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| mixed c=16 req/s (all lanes) | 46,532 [46,428–47,395] |
| mixed c=16 CPU µs/req (all lanes) | 77.4 [77.2–77.4] |
| mixed c=16 posts req/s | 1,355 [1,345–1,386] |
| mixed c=16 posts p50 ms | 0.66 [0.66–0.67] |
| mixed c=16 posts p99 ms | 2.24 [1.92–2.27] |
| mixed c=16 reads req/s | 45,187 [45,073–46,009] |
| mixed c=16 reads p50 ms | 0.19 [0.18–0.19] |
| mixed c=16 reads p99 ms | 1.66 [1.24–1.67] |
| spread c=16 req/s (all lanes) | 93,619 [93,361–94,352] |
| spread c=16 CPU µs/req (all lanes) | 38.8 [38.7–39.1] |
| spread c=16 reads req/s | 93,619 [93,361–94,352] |
| spread c=16 reads p50 ms | 0.08 [0.08–0.08] |
| spread c=16 reads p99 ms | 1.00 [1.00–1.02] |
| spread_mixed c=16 req/s (all lanes) | 11,996 [11,909–12,203] |
| spread_mixed c=16 CPU µs/req (all lanes) | 322 [320–330] |
| spread_mixed c=16 posts req/s | 674 [670–682] |
| spread_mixed c=16 posts p50 ms | 1.36 [1.36–1.38] |
| spread_mixed c=16 posts p99 ms | 4.37 [4.22–4.68] |
| spread_mixed c=16 reads req/s | 11,322 [11,239–11,520] |
| spread_mixed c=16 reads p50 ms | 1.33 [1.32–1.36] |
| spread_mixed c=16 reads p99 ms | 4.00 [3.97–4.15] |
| search_spread c=16 req/s (all lanes) | 16,408 [15,984–16,769] |
| search_spread c=16 CPU µs/req (all lanes) | 225 [221–233] |
| search_spread c=16 reads req/s | 16,408 [15,984–16,769] |
| search_spread c=16 reads p50 ms | 0.64 [0.64–0.65] |
| search_spread c=16 reads p99 ms | 7.36 [7.00–7.38] |

Realistic workloads (bench/lib/realistic.py), seed `crowd`; lanes, their connections (c is the measured concurrency) and targets:

| Workload | Lane | Connections | Pick | Targets | Users |
|---|---|---|---|---|---|
| mixed | reads | c | cycle | 1 | 1 |
| mixed | posts | 1 | cycle | 1 | 1 |
| spread | reads | c | random | 2,112 | 525 |
| spread_mixed | reads | c | random | 2,112 | 525 |
| spread_mixed | posts | 1 | random | 108 | 31 |
| search_spread | reads | c | random | 104,800 | 524 |

Sign-in of the seed's people before the workloads, per rep: onCrack 31.2 s, onCrack 31.2 s, onCrack 31.2 s.

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.42 2.43 2.59 | 6.12 4.38 3.34 |
| onCrack | 2 | 1.33 3.20 3.01 | 4.98 4.40 3.55 |
| onCrack | 3 | 1.22 3.30 3.23 | 5.93 4.71 3.81 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.07 | 1.06 | 0/4 | 1.07 |
| onCrack | 2 | 1.05 | 1.07 | 0/4 | 1.08 |
| onCrack | 3 | 1.07 | 1.08 | 0/4 | 1.07 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | mixed | 1,122,996 | 0 | 0 | 0 | 0 |
| onCrack | spread | 2,250,804 | 0 | 0 | 0 | 0 |
| onCrack | spread_mixed | 288,917 | 0 | 0 | 0 | 0 |
| onCrack | search_spread | 393,938 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | mixed | 16 | 32.0 [30.0–42.0] | 3/3 | 0.99 |
| onCrack | spread | 16 | 30.0 [30.0–30.0] | 3/3 | 0.99 |
| onCrack | spread_mixed | 16 | 30.0 [30.0–30.0] | 3/3 | 0.99 |
| onCrack | search_spread | 16 | 30.1 [30.1–30.2] | 3/3 | 0.98 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | mixed warm-up c=16 | 56,792 | 56,792 | yes |
| onCrack | 1 | mixed run c=16 | 11,087 | 11,087 | yes |
| onCrack | 1 | spread_mixed warm-up c=16 | 20,108 | 20,108 | yes |
| onCrack | 1 | spread_mixed run c=16 | 5,390 | 5,390 | yes |
| onCrack | 1 | **all** | 93,377 | 93,377 | yes |
| onCrack | 2 | mixed warm-up c=16 | 40,287 | 40,287 | yes |
| onCrack | 2 | mixed run c=16 | 10,760 | 10,760 | yes |
| onCrack | 2 | spread_mixed warm-up c=16 | 20,388 | 20,388 | yes |
| onCrack | 2 | spread_mixed run c=16 | 5,364 | 5,364 | yes |
| onCrack | 2 | **all** | 76,799 | 76,799 | yes |
| onCrack | 3 | mixed warm-up c=16 | 42,824 | 42,824 | yes |
| onCrack | 3 | mixed run c=16 | 10,842 | 10,842 | yes |
| onCrack | 3 | spread_mixed warm-up c=16 | 20,598 | 20,598 | yes |
| onCrack | 3 | spread_mixed run c=16 | 5,461 | 5,461 | yes |
| onCrack | 3 | **all** | 79,725 | 79,725 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | – | – |
