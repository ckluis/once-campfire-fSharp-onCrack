```
date: 2026-10-08T07:52:19-04:00
host: 6.8.0-117-generic, , 10 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
rust image: campfire-rust:app sha256:d582a01d3a4ae9c5fd4bc9cd7b0262e1a5d4440cc0058d200b50ad9b27e1365c 2026-10-05T23:48:02.375329666-04:00 built from commit: 
repo HEAD: ef45046 (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 06:11:29), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps rust, reps 1; suites: http; http secs 8, concs 16 64, routes room_show sidebar, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: rust 1. Cells: median [min–max].

### Startup and memory

| Metric | Rust |
|---|---|
| cold start: docker run → /up 200 (ms) | 151 |
| idle memory.current (MB) | 41.0 |
| idle anon (MB) | 14.0 |
| peak memory.current under load (MB) | 54.0 |
| peak anon under load (MB) | 27.0 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | Rust |
|---|---|
| room_show c=16 req/s | 27,578 |
| room_show c=16 CPU µs/req | 130 |
| room_show c=16 p50 ms | 0.56 |
| room_show c=16 p99 ms | 1.11 |
| room_show c=64 req/s | 28,188 |
| room_show c=64 CPU µs/req | 127 |
| room_show c=64 p50 ms | 2.21 |
| room_show c=64 p99 ms | 4.11 |
| sidebar c=16 req/s | 27,160 |
| sidebar c=16 CPU µs/req | 131 |
| sidebar c=16 p50 ms | 0.56 |
| sidebar c=16 p99 ms | 1.14 |
| sidebar c=64 req/s | 27,676 |
| sidebar c=64 CPU µs/req | 129 |
| sidebar c=64 p50 ms | 2.24 |
| sidebar c=64 p99 ms | 4.28 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| Rust | 1 | 1.32 3.62 2.62 | 4.57 4.20 3.01 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| Rust | 1 | 1.04 | 1.04 | 0/4 | 1.08 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| Rust | room_show | 446,207 | 0 | 0 | 0 | 0 |
| Rust | sidebar | 438,770 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| Rust | room_show | 16 | 30.0 | 1/1 | 1.00 |
| Rust | room_show | 64 | 30.0 | 1/1 | 1.02 |
| Rust | sidebar | 16 | 30.0 | 1/1 | 1.00 |
| Rust | sidebar | 64 | 30.0 | 1/1 | 1.00 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | Rust gzip wire / decoded | Rust identity | Rust c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,231 / 416,122 | 200 416,122 | 24,231 | – |
| sidebar | 200 5,910 / 30,763 | 200 30,763 | 5,910 | – |
| post_message | – | – | – | – |
