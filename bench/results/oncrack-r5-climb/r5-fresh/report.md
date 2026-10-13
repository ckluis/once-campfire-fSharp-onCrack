```
date: 2026-10-13T04:46:51-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:r5head sha256:bfcbb4633485c87c7c9bc9c11e7ad0a6a313d7f9bf900fa73da01b48569144f3 2026-10-12T18:32:41.82752305-04:00 built from commit: ee5a2e91795e7c8892757af2cf2561666c7c6e93
repo HEAD: 3e6a300 (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-10 23:47:11), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 3; suites: http; http secs 8, concs 1 16, routes room_show messages_page sidebar search post_message, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 3. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 245 [242–348] |
| idle memory.current (MB) | 28.0 [28.0–91.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 679 [629–817] |
| peak anon under load (MB) | 181 [181–182] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 24,563 [24,083–24,840] |
| room_show c=1 CPU µs/req | 21.1 [20.9–22.0] |
| room_show c=1 p50 ms | 0.04 [0.04–0.04] |
| room_show c=1 p99 ms | 0.06 [0.06–0.06] |
| room_show c=16 req/s | 166,316 [165,420–166,416] |
| room_show c=16 CPU µs/req | 19.3 [19.1–19.4] |
| room_show c=16 p50 ms | 0.09 [0.09–0.09] |
| room_show c=16 p99 ms | 0.22 [0.22–0.23] |
| messages_page c=1 req/s | 24,854 [21,908–25,164] |
| messages_page c=1 CPU µs/req | 20.6 [20.5–23.7] |
| messages_page c=1 p50 ms | 0.04 [0.04–0.05] |
| messages_page c=1 p99 ms | 0.06 [0.06–0.13] |
| messages_page c=16 req/s | 173,518 [162,848–175,227] |
| messages_page c=16 CPU µs/req | 18.1 [18.1–20.7] |
| messages_page c=16 p50 ms | 0.08 [0.08–0.09] |
| messages_page c=16 p99 ms | 0.22 [0.21–0.26] |
| sidebar c=1 req/s | 25,086 [24,281–25,622] |
| sidebar c=1 CPU µs/req | 19.8 [19.8–20.6] |
| sidebar c=1 p50 ms | 0.04 [0.04–0.04] |
| sidebar c=1 p99 ms | 0.06 [0.06–0.06] |
| sidebar c=16 req/s | 187,738 [187,708–189,755] |
| sidebar c=16 CPU µs/req | 16.3 [16.3–16.4] |
| sidebar c=16 p50 ms | 0.08 [0.08–0.08] |
| sidebar c=16 p99 ms | 0.20 [0.20–0.20] |
| search c=1 req/s | 24,584 [24,010–25,241] |
| search c=1 CPU µs/req | 20.7 [20.1–21.1] |
| search c=1 p50 ms | 0.04 [0.04–0.04] |
| search c=1 p99 ms | 0.06 [0.05–0.06] |
| search c=16 req/s | 184,094 [183,187–184,278] |
| search c=16 CPU µs/req | 16.8 [16.8–17.0] |
| search c=16 p50 ms | 0.08 [0.08–0.08] |
| search c=16 p99 ms | 0.20 [0.20–0.20] |
| post_message c=1 req/s | 3,462 [3,143–3,545] |
| post_message c=1 CPU µs/req | 270 [260–273] |
| post_message c=1 p50 ms | 0.19 [0.18–0.20] |
| post_message c=1 p99 ms | 0.36 [0.32–0.41] |
| post_message c=16 req/s | 9,911 [9,004–11,270] |
| post_message c=16 CPU µs/req | 214 [188–220] |
| post_message c=16 p50 ms | 0.96 [0.88–1.01] |
| post_message c=16 p99 ms | 4.91 [4.55–5.87] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.36 2.96 3.32 | 3.84 3.62 3.48 |
| onCrack | 2 | 1.30 2.89 3.24 | 3.86 3.16 3.16 |
| onCrack | 3 | 1.16 2.45 2.91 | 3.89 3.54 3.26 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.07 | 1.09 | 0/10 | 1.10 |
| onCrack | 2 | 1.07 | 1.09 | 1/10 **noisy** | 1.29 |
| onCrack | 3 | 1.09 | 1.05 | 0/10 | 1.09 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 4,573,259 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 4,668,339 | 0 | 0 | 0 | 0 |
| onCrack | sidebar | 5,121,759 | 0 | 0 | 0 | 0 |
| onCrack | search | 5,003,458 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 328,147 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 30.0 [30.0–32.0] | 3/3 | 1.00 |
| onCrack | room_show | 16 | 30.0 [30.0–62.0] | 3/3 | 1.01 |
| onCrack | messages_page | 1 | 32.0 [30.0–40.0] | 3/3 | 1.01 |
| onCrack | messages_page | 16 | 30.0 [30.0–30.0] | 3/3 | 0.99 |
| onCrack | sidebar | 1 | 30.0 [30.0–56.0] | 3/3 | 1.01 |
| onCrack | sidebar | 16 | 44.0 [34.0–80.0] | 3/3 | 1.00 |
| onCrack | search | 1 | 30.0 [30.0–36.0] | 3/3 | 1.01 |
| onCrack | search | 16 | 30.0 [30.0–86.0] | 3/3 | 1.01 |
| onCrack | post_message | 1 | 91.7 [30.0–91.7] | 1/3 **←** | 0.89 |
| onCrack | post_message | 16 | 91.6 [90.8–92.1] | 0/3 **←** | 0.97 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 338,377 | 338,377 | yes |
| onCrack | 1 | run c=1 | 27,141 | 27,141 | yes |
| onCrack | 1 | warm-up c=16 | 1,033,452 | 1,033,452 | yes |
| onCrack | 1 | run c=16 | 79,299 | 79,299 | yes |
| onCrack | 1 | **all** | 1,478,269 | 1,478,269 | yes |
| onCrack | 2 | warm-up c=1 | 354,204 | 354,204 | yes |
| onCrack | 2 | run c=1 | 27,695 | 27,695 | yes |
| onCrack | 2 | warm-up c=16 | 673,221 | 673,221 | yes |
| onCrack | 2 | run c=16 | 72,034 | 72,034 | yes |
| onCrack | 2 | **all** | 1,127,154 | 1,127,154 | yes |
| onCrack | 3 | warm-up c=1 | 142,276 | 142,276 | yes |
| onCrack | 3 | run c=1 | 31,803 | 31,803 | yes |
| onCrack | 3 | warm-up c=16 | 1,017,681 | 1,017,681 | yes |
| onCrack | 3 | run c=16 | 90,175 | 90,175 | yes |
| onCrack | 3 | **all** | 1,281,935 | 1,281,935 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| sidebar | 200 5,826 / 30,763 | 200 30,763 | 5,826 | – |
| search | 200 9,712 / 149,623 | 200 149,623 | 9,712 | – |
| post_message | – | – | 2,097 | – |
