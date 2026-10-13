```
date: 2026-10-10T09:46:18-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: CAMPFIRE_FRESH_HOLD=0
user agent: (none)
oncrack image: campfire-oncrack:app sha256:df19fab7a0b5cda8cafd4d0647cb351f9a7814c80bdc0c7cf1d165c005b1c80d 2026-10-10T09:24:13.825073222-04:00 built from commit: 0aaa21a2aaf7d035067ce61f7fe0fc8983dd8455
repo HEAD: 0aaa21a (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-10 02:25:45), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: http; http secs 8, concs 1 16, routes room_show messages_page, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 450 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 122 |
| peak anon under load (MB) | 102 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 17,154 |
| room_show c=1 CPU µs/req | 29.3 |
| room_show c=1 p50 ms | 0.05 |
| room_show c=1 p99 ms | 0.30 |
| room_show c=16 req/s | 130,583 |
| room_show c=16 CPU µs/req | 24.3 |
| room_show c=16 p50 ms | 0.11 |
| room_show c=16 p99 ms | 0.31 |
| messages_page c=1 req/s | 21,402 |
| messages_page c=1 CPU µs/req | 25.6 |
| messages_page c=1 p50 ms | 0.05 |
| messages_page c=1 p99 ms | 0.09 |
| messages_page c=16 req/s | 116,027 |
| messages_page c=16 CPU µs/req | 27.9 |
| messages_page c=16 p50 ms | 0.12 |
| messages_page c=16 p99 ms | 0.38 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.45 2.14 2.48 | 3.62 2.52 2.49 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.07 | 1.09 | 2/4 **noisy** | 1.14 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 1,181,950 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 1,099,495 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 90.0 | 0/1 **←** | 0.93 |
| onCrack | room_show | 16 | 88.0 | 1/1 | 1.01 |
| onCrack | messages_page | 1 | 90.0 | 0/1 **←** | 1.06 |
| onCrack | messages_page | 16 | 30.0 | 1/1 | 0.98 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| post_message | – | – | – | – |
