```
date: 2026-10-08T18:35:01-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:c4942d0a4aa78e18b47b32394017d573338199c41431bdc195990a41830330cc 2026-10-08T18:05:19.069830184-04:00 built from commit: 4e12ec88408ca627c4bfa08187e2fd377ad052f9
repo HEAD: 4e12ec8 (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 11:27:25), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: http; http secs 8, concs 1 16 64, routes up avatar static_css post_message, warm-up 20s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 217 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 634 |
| peak anon under load (MB) | 203 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| avatar c=1 req/s | 29,078 |
| avatar c=1 CPU µs/req | 15.9 |
| avatar c=1 p50 ms | 0.03 |
| avatar c=1 p99 ms | 0.05 |
| avatar c=16 req/s | 203,063 |
| avatar c=16 CPU µs/req | 13.8 |
| avatar c=16 p50 ms | 0.07 |
| avatar c=16 p99 ms | 0.18 |
| avatar c=64 req/s | 276,408 |
| avatar c=64 CPU µs/req | 12.2 |
| avatar c=64 p50 ms | 0.20 |
| avatar c=64 p99 ms | 0.73 |
| static_css c=1 req/s | 30,846 |
| static_css c=1 CPU µs/req | 14.6 |
| static_css c=1 p50 ms | 0.03 |
| static_css c=1 p99 ms | 0.04 |
| static_css c=16 req/s | 230,143 |
| static_css c=16 CPU µs/req | 11.6 |
| static_css c=16 p50 ms | 0.07 |
| static_css c=16 p99 ms | 0.16 |
| static_css c=64 req/s | 321,002 |
| static_css c=64 CPU µs/req | 10.4 |
| static_css c=64 p50 ms | 0.18 |
| static_css c=64 p99 ms | 0.52 |
| up c=1 req/s | 24,004 |
| up c=1 CPU µs/req | 22.4 |
| up c=1 p50 ms | 0.04 |
| up c=1 p99 ms | 0.06 |
| up c=16 req/s | 185,900 |
| up c=16 CPU µs/req | 17.6 |
| up c=16 p50 ms | 0.07 |
| up c=16 p99 ms | 0.22 |
| up c=64 req/s | 236,629 |
| up c=64 CPU µs/req | 15.2 |
| up c=64 p50 ms | 0.22 |
| up c=64 p99 ms | 1.18 |
| post_message c=1 req/s | 5,201 |
| post_message c=1 CPU µs/req | 247 |
| post_message c=1 p50 ms | 0.17 |
| post_message c=1 p99 ms | 0.29 |
| post_message c=16 req/s | 15,559 |
| post_message c=16 CPU µs/req | 178 |
| post_message c=16 p50 ms | 0.86 |
| post_message c=16 p99 ms | 4.79 |
| post_message c=64 req/s | 17,757 |
| post_message c=64 CPU µs/req | 162 |
| post_message c=64 p50 ms | 3.16 |
| post_message c=64 p99 ms | 8.57 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.45 2.27 2.36 | 3.69 3.32 2.80 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.08 | 1.05 | 0/12 | 1.09 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | avatar | 4,068,779 | 0 | 0 | 0 | 0 |
| onCrack | static_css | 4,656,416 | 0 | 0 | 0 | 0 |
| onCrack | up | 3,572,630 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 308,196 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | avatar | 1 | 20.0 | 1/1 | 1.01 |
| onCrack | avatar | 16 | 20.0 | 1/1 | 1.00 |
| onCrack | avatar | 64 | 20.0 | 1/1 | 1.00 |
| onCrack | static_css | 1 | 20.0 | 1/1 | 1.02 |
| onCrack | static_css | 16 | 20.0 | 1/1 | 1.00 |
| onCrack | static_css | 64 | 20.0 | 1/1 | 1.00 |
| onCrack | up | 1 | 20.0 | 1/1 | 1.02 |
| onCrack | up | 16 | 20.0 | 1/1 | 1.00 |
| onCrack | up | 64 | 20.0 | 1/1 | 1.01 |
| onCrack | post_message | 1 | 20.0 | 1/1 | 1.01 |
| onCrack | post_message | 16 | 20.0 | 1/1 | 0.98 |
| onCrack | post_message | 64 | 20.0 | 1/1 | 1.00 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 98,524 | 98,524 | yes |
| onCrack | 1 | run c=1 | 41,609 | 41,609 | yes |
| onCrack | 1 | warm-up c=16 | 314,443 | 314,443 | yes |
| onCrack | 1 | run c=16 | 124,488 | 124,488 | yes |
| onCrack | 1 | warm-up c=64 | 356,815 | 356,815 | yes |
| onCrack | 1 | run c=64 | 142,099 | 142,099 | yes |
| onCrack | 1 | **all** | 1,077,978 | 1,077,978 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| avatar | 200 3,368 / 3,364 | 200 3,364 | 3,368 | – |
| static_css | 200 651 / 1,218 | 200 1,218 | 651 | – |
| up | 200 82 / 73 | 200 73 | 82 | – |
| post_message | – | – | 2,097 | – |
