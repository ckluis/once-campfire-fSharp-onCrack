```
date: 2026-10-07T10:59:45-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:56c3c35f8fd5e742ed90860e4b043c2f9496b320301af599f69c4b965b9dec96 2026-10-07T10:27:20.937724291-04:00 built from commit: 0f3e1202e2a9c6d094ba0073530d3f0af4df8dd5
repo HEAD: 0f3e120 (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-07 07:47:18), built with rust:1.98.1-trixie
schedule: apps oncrack, reps 3; suites: http; http secs 8, concs 64, routes post_message, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 3. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 198 [188–234] |
| idle memory.current (MB) | 28.0 [28.0–28.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 577 [560–579] |
| peak anon under load (MB) | 287 [286–287] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| post_message c=64 req/s | 17,865 [17,666–17,995] |
| post_message c=64 CPU µs/req | 187 [186–187] |
| post_message c=64 p50 ms | 3.32 [3.29–3.33] |
| post_message c=64 p99 ms | 9.17 [8.86–9.50] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.32 2.63 2.86 | 3.47 3.00 2.98 |
| onCrack | 2 | 1.30 2.44 2.78 | 3.44 2.89 2.92 |
| onCrack | 3 | 1.45 2.42 2.75 | 3.94 2.95 2.92 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.01 | 1.02 | 0/1 | 1.05 |
| onCrack | 2 | 1.02 | 1.05 | 0/1 | 1.01 |
| onCrack | 3 | 1.04 | 1.02 | 0/1 | 1.05 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | post_message | 428,407 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | post_message | 64 | 32.0 [30.0–34.0] | 3/3 | 1.02 |

### Rows written by `post_message` (messages of the write room counted in the app's SQLite file around each run)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=64 | 557,044 | 557,044 | yes |
| onCrack | 1 | run c=64 | 144,008 | 144,008 | yes |
| onCrack | 1 | **all** | 701,052 | 701,052 | yes |
| onCrack | 2 | warm-up c=64 | 523,044 | 523,044 | yes |
| onCrack | 2 | run c=64 | 141,417 | 141,417 | yes |
| onCrack | 2 | **all** | 664,461 | 664,461 | yes |
| onCrack | 3 | warm-up c=64 | 485,468 | 485,468 | yes |
| onCrack | 3 | run c=64 | 142,982 | 142,982 | yes |
| onCrack | 3 | **all** | 628,450 | 628,450 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | – | – |
