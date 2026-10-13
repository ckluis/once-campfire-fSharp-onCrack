```
date: 2026-10-08T12:16:26-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: CAMPFIRE_GZIP_ONCE_LEVEL=6
user agent: (none)
oncrack image: campfire-oncrack:app sha256:1651f5173e7e1163a56fae69c452a0ca9981ccefe3e0d51e625ce8552418f6e2 2026-10-08T11:52:06.405254996-04:00 built from commit: bb78cc730de2816980ad9f8ed6d1df329580a8fc
oncrack build: MOUNTED /var/tmp/campfire-mounted over /opt/campfire (33500f4 (dirty files under src/: 2) at 2026-10-08T16:13:00Z)
repo HEAD: 33500f4 (dirty: 2 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 11:27:25), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: http; http secs 8, concs 1 16 64, routes post_message, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 231 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 673 |
| peak anon under load (MB) | 178 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| post_message c=1 req/s | 4,443 |
| post_message c=1 CPU µs/req | 403 |
| post_message c=1 p50 ms | 0.20 |
| post_message c=1 p99 ms | 0.37 |
| post_message c=16 req/s | 11,819 |
| post_message c=16 CPU µs/req | 193 |
| post_message c=16 p50 ms | 0.90 |
| post_message c=16 p99 ms | 4.94 |
| post_message c=64 req/s | 17,788 |
| post_message c=64 CPU µs/req | 164 |
| post_message c=64 p50 ms | 3.18 |
| post_message c=64 p99 ms | 9.33 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.28 2.04 2.04 | 2.73 2.27 2.12 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.05 | 1.07 | 0/3 | 1.10 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | post_message | 275,837 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | post_message | 1 | 30.0 | 1/1 | 0.99 |
| onCrack | post_message | 16 | 31.3 | 0/1 **←** | 1.09 |
| onCrack | post_message | 64 | 30.0 | 1/1 | 0.99 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 126,524 | 126,524 | yes |
| onCrack | 1 | run c=1 | 35,546 | 35,546 | yes |
| onCrack | 1 | warm-up c=16 | 310,977 | 310,977 | yes |
| onCrack | 1 | run c=16 | 97,934 | 97,934 | yes |
| onCrack | 1 | warm-up c=64 | 542,891 | 542,891 | yes |
| onCrack | 1 | run c=64 | 142,357 | 142,357 | yes |
| onCrack | 1 | **all** | 1,256,229 | 1,256,229 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | 1,987 | – |
