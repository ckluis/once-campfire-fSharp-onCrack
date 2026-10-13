```
date: 2026-10-08T00:52:37-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: DOTNET_HillClimbing_Disable=0
oncrack extra env: 
user agent: (none)
fsharp image: campfire-fsharp:app sha256:421f335c3ff8ee640991228ffe18bb750f2a37a4bd5ad9da64e0a0da5cb1ae0c 2026-10-07T04:18:34.342866793-04:00 built from commit: 2e6c08e242191cb9c982ecc0f2c06e56d2e9855e
repo HEAD: da1e92f (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-07 07:47:18), built with rust:1.98.1-trixie
schedule: apps fsharp, reps 1; suites: http; http secs 8, concs 1 16 64, routes up, warm-up 30s at each route and concentration, idle 10s
log retention: 2 x 10m (json-file)
```

Reps: fsharp 1. Cells: median [min–max].

### Startup and memory

| Metric | F# |
|---|---|
| cold start: docker run → /up 200 (ms) | 275 |
| idle memory.current (MB) | 27.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 123 |
| peak anon under load (MB) | 102 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | F# |
|---|---|
| up c=1 req/s | 15,493 |
| up c=1 CPU µs/req | 118 |
| up c=1 p50 ms | 0.06 |
| up c=1 p99 ms | 0.10 |
| up c=16 req/s | 136,324 |
| up c=16 CPU µs/req | 20.7 |
| up c=16 p50 ms | 0.10 |
| up c=16 p99 ms | 0.27 |
| up c=64 req/s | 170,379 |
| up c=64 CPU µs/req | 15.8 |
| up c=64 p50 ms | 0.33 |
| up c=64 p99 ms | 1.29 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| F# | 1 | 1.33 2.29 2.49 | 7.52 4.04 3.08 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| F# | 1 | 1.03 | 1.04 | 0/3 | 1.04 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| F# | up | 2,577,961 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| F# | up | 1 | 48.0 | 1/1 | 1.03 |
| F# | up | 16 | 50.0 | 1/1 | 1.01 |
| F# | up | 64 | 30.0 | 1/1 | 0.98 |

### Rows written by `post_message` (messages of the write room counted in the app's SQLite file around each run)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | F# gzip wire / decoded | F# identity | F# c=16 avg | vs Rust |
|---|---|---|---|---|
| up | 200 90 / 73 | 200 73 | 90 | – |
| post_message | – | – | – | – |
