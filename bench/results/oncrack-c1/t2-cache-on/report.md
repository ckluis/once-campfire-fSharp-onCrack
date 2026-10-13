```
date: 2026-10-07T08:39:21-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:78b7c9f9bcdc06887dfb0bdd2d47fca8279c7492e642a36a5f37caace362c3d1 2026-10-07T07:46:54.565800272-04:00 built from commit: 2de7519d49865f7514a6973540c2d781d32c5dca
oncrack build: MOUNTED /var/tmp/campfire-mounted over /opt/campfire (23cf334 (dirty files under src/: 0) at 2026-10-07T12:39:13Z)
repo HEAD: 23cf334 (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-07 07:47:18), built with rust:1.98.1-trixie
schedule: apps oncrack, reps 1; suites: http; http secs 8, concs 16, routes room_show messages_page sidebar search post_message, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 358 |
| idle memory.current (MB) | 76.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 450 |
| peak anon under load (MB) | 217 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=16 req/s | 95,310 |
| room_show c=16 CPU µs/req | 32.2 |
| room_show c=16 p50 ms | 0.14 |
| room_show c=16 p99 ms | 0.42 |
| messages_page c=16 req/s | 103,268 |
| messages_page c=16 CPU µs/req | 30.7 |
| messages_page c=16 p50 ms | 0.13 |
| messages_page c=16 p99 ms | 0.44 |
| sidebar c=16 req/s | 110,523 |
| sidebar c=16 CPU µs/req | 27.3 |
| sidebar c=16 p50 ms | 0.12 |
| sidebar c=16 p99 ms | 0.35 |
| search c=16 req/s | 71,472 |
| search c=16 CPU µs/req | 31.4 |
| search c=16 p50 ms | 0.23 |
| search c=16 p99 ms | 0.37 |
| post_message c=16 req/s | 8,735 |
| post_message c=16 CPU µs/req | 354 |
| post_message c=16 p50 ms | 1.56 |
| post_message c=16 p99 ms | 5.99 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.41 0.50 0.68 | 4.41 2.99 1.74 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.03 | 1.03 | 0/5 | 1.05 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 762,526 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 826,181 | 0 | 0 | 0 | 0 |
| onCrack | sidebar | 884,232 | 0 | 0 | 0 | 0 |
| onCrack | search | 571,802 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 69,891 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 16 | 30.0 | 1/1 | 0.95 |
| onCrack | messages_page | 16 | 44.0 | 1/1 | 0.99 |
| onCrack | sidebar | 16 | 30.0 | 1/1 | 0.98 |
| onCrack | search | 16 | 90.0 | 0/1 **←** | 0.98 |
| onCrack | post_message | 16 | 34.0 | 1/1 | 1.00 |

### Rows written by `post_message` (messages of the write room counted in the app's SQLite file around each run)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=16 | 293,526 | 293,526 | yes |
| onCrack | 1 | run c=16 | 69,891 | 69,891 | yes |
| onCrack | 1 | **all** | 363,417 | 363,417 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| sidebar | 200 5,910 / 30,763 | 200 30,763 | 5,910 | – |
| search | 200 9,713 / 149,623 | 200 149,623 | 9,713 | – |
| post_message | – | – | 1,993 | – |
