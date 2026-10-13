```
date: 2026-10-07T10:13:29-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:75caf211cc3721a7ab4b6eebec7e21fa4f4ed4cc3859fff3436e87a21f28d21b 2026-10-07T08:50:08.575773277-04:00 built from commit: 23cf3346587c33001f160ef7aa7d9e86311706ec
oncrack build: MOUNTED /var/tmp/campfire-mounted over /opt/campfire (25ea87e (dirty files under src/: 0) at 2026-10-07T14:13:29Z)
repo HEAD: 25ea87e (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-07 07:47:18), built with rust:1.98.1-trixie
schedule: apps oncrack, reps 1; suites: http; http secs 8, concs 16 64, routes post_message, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 229 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 751 |
| peak anon under load (MB) | 285 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| post_message c=16 req/s | 12,963 |
| post_message c=16 CPU µs/req | 234 |
| post_message c=16 p50 ms | 1.07 |
| post_message c=16 p99 ms | 5.41 |
| post_message c=64 req/s | 17,934 |
| post_message c=64 CPU µs/req | 186 |
| post_message c=64 p50 ms | 3.28 |
| post_message c=64 p99 ms | 9.44 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.33 2.05 1.47 | 4.44 2.90 1.82 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.05 | 1.02 | 0/2 | 1.03 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | post_message | 247,251 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | post_message | 16 | 34.0 | 1/1 | 1.00 |
| onCrack | post_message | 64 | 30.0 | 1/1 | 1.02 |

### Rows written by `post_message` (messages of the write room counted in the app's SQLite file around each run)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=16 | 419,865 | 419,865 | yes |
| onCrack | 1 | run c=16 | 103,721 | 103,721 | yes |
| onCrack | 1 | warm-up c=64 | 521,733 | 521,733 | yes |
| onCrack | 1 | run c=64 | 143,530 | 143,530 | yes |
| onCrack | 1 | **all** | 1,188,849 | 1,188,849 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | 1,994 | – |
