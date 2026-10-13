```
date: 2026-10-09T05:17:30-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:155ea5d0e559c8f48866c20155890405568a7ec068f057aa66af2c41e6fa2fb7 2026-10-09T04:20:53.243370801-04:00 built from commit: f5352d038bbb7ba23d297ed6df5c641e1bd55fd8
repo HEAD: f5352d0 (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 11:27:25), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 3; suites: http; http secs 8, concs 1 16, routes room_show messages_page sidebar search post_message (in parts, --part 1/2 is one slice of them), warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 3. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 213 [195–224] |
| idle memory.current (MB) | 28.0 [28.0–28.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 718 [718–787] |
| peak anon under load (MB) | 181 [181–182] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 26,215 [25,986–26,293] |
| room_show c=1 CPU µs/req | 18.9 [18.9–19.2] |
| room_show c=1 p50 ms | 0.04 [0.04–0.04] |
| room_show c=1 p99 ms | 0.05 [0.05–0.05] |
| room_show c=16 req/s | 177,276 [174,732–178,994] |
| room_show c=16 CPU µs/req | 17.4 [17.4–17.9] |
| room_show c=16 p50 ms | 0.08 [0.08–0.08] |
| room_show c=16 p99 ms | 0.21 [0.21–0.21] |
| messages_page c=1 req/s | 26,199 [25,921–26,576] |
| messages_page c=1 CPU µs/req | 18.7 [18.5–18.8] |
| messages_page c=1 p50 ms | 0.04 [0.04–0.04] |
| messages_page c=1 p99 ms | 0.05 [0.05–0.05] |
| messages_page c=16 req/s | 185,538 [178,378–187,179] |
| messages_page c=16 CPU µs/req | 16.2 [16.1–17.4] |
| messages_page c=16 p50 ms | 0.08 [0.08–0.08] |
| messages_page c=16 p99 ms | 0.20 [0.20–0.21] |
| sidebar c=1 req/s | 26,821 [26,022–27,114] |
| sidebar c=1 CPU µs/req | 17.9 [17.6–18.3] |
| sidebar c=1 p50 ms | 0.04 [0.04–0.04] |
| sidebar c=1 p99 ms | 0.05 [0.05–0.05] |
| sidebar c=16 req/s | 198,161 [198,115–198,627] |
| sidebar c=16 CPU µs/req | 14.7 [14.7–14.8] |
| sidebar c=16 p50 ms | 0.07 [0.07–0.07] |
| sidebar c=16 p99 ms | 0.18 [0.18–0.18] |
| search c=1 req/s | 27,765 [27,647–28,108] |
| search c=1 CPU µs/req | 17.3 [17.2–17.4] |
| search c=1 p50 ms | 0.04 [0.04–0.04] |
| search c=1 p99 ms | 0.05 [0.05–0.05] |
| search c=16 req/s | 192,737 [192,538–194,164] |
| search c=16 CPU µs/req | 15.4 [15.2–15.4] |
| search c=16 p50 ms | 0.08 [0.08–0.08] |
| search c=16 p99 ms | 0.19 [0.19–0.19] |
| post_message c=1 req/s | 5,112 [3,847–5,152] |
| post_message c=1 CPU µs/req | 248 [247–250] |
| post_message c=1 p50 ms | 0.17 [0.17–0.17] |
| post_message c=1 p99 ms | 0.30 [0.30–0.30] |
| post_message c=16 req/s | 11,292 [10,732–12,470] |
| post_message c=16 CPU µs/req | 178 [175–180] |
| post_message c=16 p50 ms | 0.86 [0.85–0.87] |
| post_message c=16 p99 ms | 4.46 [4.39–4.53] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.31 4.05 4.67 | 3.82 3.04 3.75 |
| onCrack | 2 | 1.32 2.45 3.50 | 4.34 3.21 3.34 |
| onCrack | 3 | 1.45 2.57 3.10 | 3.66 2.93 3.01 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.06 | 1.06 | 1/10 **noisy** | 1.10 |
| onCrack | 2 | 1.07 | 1.04 | 0/10 | 1.09 |
| onCrack | 3 | 1.08 | 1.03 | 0/10 | 1.10 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 4,876,145 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 5,038,558 | 0 | 0 | 0 | 0 |
| onCrack | sidebar | 5,399,100 | 0 | 0 | 0 | 0 |
| onCrack | search | 5,303,882 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 395,334 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | room_show | 16 | 30.0 [30.0–30.0] | 3/3 | 0.99 |
| onCrack | messages_page | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | messages_page | 16 | 30.0 [30.0–30.0] | 3/3 | 0.99 |
| onCrack | sidebar | 1 | 30.0 [30.0–30.0] | 3/3 | 1.02 |
| onCrack | sidebar | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | search | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | search | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | post_message | 1 | 30.0 [30.0–90.2] | 2/3 **←** | 1.01 |
| onCrack | post_message | 16 | 91.2 [90.4–91.8] | 0/3 **←** | 1.07 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 355,344 | 355,344 | yes |
| onCrack | 1 | run c=1 | 30,779 | 30,779 | yes |
| onCrack | 1 | warm-up c=16 | 1,108,540 | 1,108,540 | yes |
| onCrack | 1 | run c=16 | 96,803 | 96,803 | yes |
| onCrack | 1 | **all** | 1,591,466 | 1,591,466 | yes |
| onCrack | 2 | warm-up c=1 | 149,568 | 149,568 | yes |
| onCrack | 2 | run c=1 | 41,218 | 41,218 | yes |
| onCrack | 2 | warm-up c=16 | 1,089,807 | 1,089,807 | yes |
| onCrack | 2 | run c=16 | 99,772 | 99,772 | yes |
| onCrack | 2 | **all** | 1,380,365 | 1,380,365 | yes |
| onCrack | 3 | warm-up c=1 | 148,692 | 148,692 | yes |
| onCrack | 3 | run c=1 | 40,897 | 40,897 | yes |
| onCrack | 3 | warm-up c=16 | 1,115,930 | 1,115,930 | yes |
| onCrack | 3 | run c=16 | 85,865 | 85,865 | yes |
| onCrack | 3 | **all** | 1,391,384 | 1,391,384 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| sidebar | 200 5,826 / 30,763 | 200 30,763 | 5,826 | – |
| search | 200 9,713 / 149,623 | 200 149,623 | 9,713 | – |
| post_message | – | – | 2,097 | – |
