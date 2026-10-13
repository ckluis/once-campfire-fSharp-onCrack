```
date: 2026-10-13T10:26:37-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: CAMPFIRE_FRESH_AUTH=0
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
| cold start: docker run → /up 200 (ms) | 237 [212–314] |
| idle memory.current (MB) | 28.0 [28.0–29.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 696 [696–710] |
| peak anon under load (MB) | 183 [181–184] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 24,142 [22,851–24,538] |
| room_show c=1 CPU µs/req | 20.9 [20.0–21.4] |
| room_show c=1 p50 ms | 0.04 [0.04–0.04] |
| room_show c=1 p99 ms | 0.07 [0.06–0.11] |
| room_show c=16 req/s | 172,150 [157,018–173,452] |
| room_show c=16 CPU µs/req | 18.2 [18.0–19.1] |
| room_show c=16 p50 ms | 0.09 [0.08–0.09] |
| room_show c=16 p99 ms | 0.21 [0.21–0.30] |
| messages_page c=1 req/s | 24,655 [23,466–25,510] |
| messages_page c=1 CPU µs/req | 20.3 [19.3–21.3] |
| messages_page c=1 p50 ms | 0.04 [0.04–0.04] |
| messages_page c=1 p99 ms | 0.06 [0.05–0.15] |
| messages_page c=16 req/s | 184,586 [169,720–185,233] |
| messages_page c=16 CPU µs/req | 16.5 [16.4–19.2] |
| messages_page c=16 p50 ms | 0.08 [0.08–0.09] |
| messages_page c=16 p99 ms | 0.20 [0.20–0.24] |
| sidebar c=1 req/s | 25,648 [15,467–25,671] |
| sidebar c=1 CPU µs/req | 19.1 [19.0–25.1] |
| sidebar c=1 p50 ms | 0.04 [0.03–0.04] |
| sidebar c=1 p99 ms | 0.09 [0.05–0.38] |
| sidebar c=16 req/s | 194,379 [172,398–196,373] |
| sidebar c=16 CPU µs/req | 15.2 [15.0–19.4] |
| sidebar c=16 p50 ms | 0.08 [0.08–0.09] |
| sidebar c=16 p99 ms | 0.19 [0.19–0.30] |
| search c=1 req/s | 24,640 [23,725–27,246] |
| search c=1 CPU µs/req | 19.6 [18.0–20.6] |
| search c=1 p50 ms | 0.04 [0.04–0.04] |
| search c=1 p99 ms | 0.06 [0.05–0.07] |
| search c=16 req/s | 190,664 [146,798–190,942] |
| search c=16 CPU µs/req | 15.7 [15.7–19.6] |
| search c=16 p50 ms | 0.08 [0.08–0.08] |
| search c=16 p99 ms | 0.20 [0.19–0.39] |
| post_message c=1 req/s | 3,505 [3,150–5,047] |
| post_message c=1 CPU µs/req | 258 [255–274] |
| post_message c=1 p50 ms | 0.18 [0.18–0.19] |
| post_message c=1 p99 ms | 0.33 [0.32–0.42] |
| post_message c=16 req/s | 11,121 [10,316–14,024] |
| post_message c=16 CPU µs/req | 206 [182–206] |
| post_message c=16 p50 ms | 0.91 [0.88–0.94] |
| post_message c=16 p99 ms | 5.36 [4.43–5.47] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 0.63 1.59 1.93 | 3.59 3.01 2.47 |
| onCrack | 2 | 1.29 2.44 2.31 | 3.34 3.02 2.63 |
| onCrack | 3 | 0.86 2.24 2.39 | 3.42 3.14 2.78 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.06 | 1.06 | 1/10 **noisy** | 1.12 |
| onCrack | 2 | 1.09 | 1.10 | 5/10 **noisy** | 1.23 |
| onCrack | 3 | 1.08 | 1.09 | 2/10 **noisy** | 1.13 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 4,593,410 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 4,905,642 | 0 | 0 | 0 | 0 |
| onCrack | sidebar | 5,039,679 | 0 | 0 | 0 | 0 |
| onCrack | search | 4,832,311 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 377,341 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 36.0 [30.0–82.0] | 3/3 | 0.96 |
| onCrack | room_show | 16 | 46.0 [30.0–72.0] | 3/3 | 0.99 |
| onCrack | messages_page | 1 | 32.0 [32.0–54.0] | 3/3 | 1.00 |
| onCrack | messages_page | 16 | 30.0 [30.0–30.0] | 3/3 | 1.01 |
| onCrack | sidebar | 1 | 48.0 [30.0–90.0] | 2/3 **←** | 1.01 |
| onCrack | sidebar | 16 | 32.0 [30.0–60.0] | 3/3 | 1.01 |
| onCrack | search | 1 | 30.0 [30.0–40.0] | 3/3 | 1.02 |
| onCrack | search | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | post_message | 1 | 30.0 [30.0–92.2] | 2/3 **←** | 1.00 |
| onCrack | post_message | 16 | 92.1 [91.5–92.3] | 0/3 **←** | 1.13 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 144,781 | 144,781 | yes |
| onCrack | 1 | run c=1 | 28,040 | 28,040 | yes |
| onCrack | 1 | warm-up c=16 | 1,061,345 | 1,061,345 | yes |
| onCrack | 1 | run c=16 | 82,547 | 82,547 | yes |
| onCrack | 1 | **all** | 1,316,713 | 1,316,713 | yes |
| onCrack | 2 | warm-up c=1 | 309,461 | 309,461 | yes |
| onCrack | 2 | run c=1 | 25,199 | 25,199 | yes |
| onCrack | 2 | warm-up c=16 | 926,801 | 926,801 | yes |
| onCrack | 2 | run c=16 | 88,979 | 88,979 | yes |
| onCrack | 2 | **all** | 1,350,440 | 1,350,440 | yes |
| onCrack | 3 | warm-up c=1 | 144,867 | 144,867 | yes |
| onCrack | 3 | run c=1 | 40,376 | 40,376 | yes |
| onCrack | 3 | warm-up c=16 | 1,033,390 | 1,033,390 | yes |
| onCrack | 3 | run c=16 | 112,200 | 112,200 | yes |
| onCrack | 3 | **all** | 1,330,833 | 1,330,833 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| sidebar | 200 5,826 / 30,763 | 200 30,763 | 5,826 | – |
| search | 200 9,712 / 149,623 | 200 149,623 | 9,712 | – |
| post_message | – | – | 2,096 | – |
