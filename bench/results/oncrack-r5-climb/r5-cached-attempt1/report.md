```
date: 2026-10-13T05:50:59-04:00
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
| cold start: docker run → /up 200 (ms) | 224 [210–259] |
| idle memory.current (MB) | 29.0 [29.0–29.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 649 [610–680] |
| peak anon under load (MB) | 181 [181–183] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 22,687 [10,112–25,689] |
| room_show c=1 CPU µs/req | 21.8 [19.5–42.5] |
| room_show c=1 p50 ms | 0.04 [0.04–0.06] |
| room_show c=1 p99 ms | 0.12 [0.05–0.70] |
| room_show c=16 req/s | 146,329 [98,121–168,785] |
| room_show c=16 CPU µs/req | 22.6 [18.5–26.3] |
| room_show c=16 p50 ms | 0.10 [0.09–0.11] |
| room_show c=16 p99 ms | 0.27 [0.22–1.00] |
| messages_page c=1 req/s | 22,318 [14,842–26,619] |
| messages_page c=1 CPU µs/req | 22.0 [18.5–31.6] |
| messages_page c=1 p50 ms | 0.05 [0.04–0.05] |
| messages_page c=1 p99 ms | 0.06 [0.05–0.25] |
| messages_page c=16 req/s | 164,452 [155,388–180,005] |
| messages_page c=16 CPU µs/req | 19.9 [16.8–21.8] |
| messages_page c=16 p50 ms | 0.09 [0.08–0.09] |
| messages_page c=16 p99 ms | 0.22 [0.21–0.38] |
| sidebar c=1 req/s | 23,886 [22,578–27,311] |
| sidebar c=1 CPU µs/req | 20.3 [17.8–21.1] |
| sidebar c=1 p50 ms | 0.04 [0.04–0.04] |
| sidebar c=1 p99 ms | 0.06 [0.06–0.13] |
| sidebar c=16 req/s | 161,784 [161,021–177,104] |
| sidebar c=16 CPU µs/req | 19.6 [18.3–20.1] |
| sidebar c=16 p50 ms | 0.09 [0.08–0.09] |
| sidebar c=16 p99 ms | 0.30 [0.24–0.31] |
| search c=1 req/s | 24,679 [23,597–24,729] |
| search c=1 CPU µs/req | 19.8 [19.0–20.7] |
| search c=1 p50 ms | 0.04 [0.04–0.04] |
| search c=1 p99 ms | 0.07 [0.06–0.10] |
| search c=16 req/s | 147,371 [145,034–186,287] |
| search c=16 CPU µs/req | 20.5 [15.9–21.9] |
| search c=16 p50 ms | 0.09 [0.08–0.09] |
| search c=16 p99 ms | 0.40 [0.20–0.45] |
| post_message c=1 req/s | 2,270 [1,932–2,796] |
| post_message c=1 CPU µs/req | 278 [260–648] |
| post_message c=1 p50 ms | 0.19 [0.18–0.40] |
| post_message c=1 p99 ms | 0.48 [0.47–1.20] |
| post_message c=16 req/s | 10,529 [9,840–13,431] |
| post_message c=16 CPU µs/req | 188 [186–223] |
| post_message c=16 p50 ms | 0.90 [0.90–1.07] |
| post_message c=16 p99 ms | 4.86 [4.59–5.01] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.19 2.74 2.73 | 4.22 3.84 3.29 |
| onCrack | 2 | 1.42 3.07 3.06 | 4.40 3.89 3.50 |
| onCrack | 3 | 1.20 2.98 3.21 | 3.52 3.34 3.20 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.08 | 1.28 | 2/10 **noisy** | 1.14 |
| onCrack | 2 | 1.07 | 1.35 | 1/10 **noisy** | 1.31 |
| onCrack | 3 | 1.08 | 1.13 | 5/10 **noisy** | 1.42 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 3,774,170 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 4,509,236 | 0 | 0 | 0 | 0 |
| onCrack | sidebar | 4,589,753 | 0 | 0 | 0 | 0 |
| onCrack | search | 4,413,784 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 326,418 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 90.0 [34.0–90.0] | 1/3 **←** | 0.92 |
| onCrack | room_show | 16 | 90.0 [30.0–90.2] | 1/3 **←** | 0.97 |
| onCrack | messages_page | 1 | 90.0 [30.0–90.0] | 1/3 **←** | 1.01 |
| onCrack | messages_page | 16 | 30.0 [30.0–44.0] | 3/3 | 1.00 |
| onCrack | sidebar | 1 | 30.0 [30.0–32.0] | 3/3 | 1.01 |
| onCrack | sidebar | 16 | 90.0 [50.0–90.0] | 1/3 **←** | 1.05 |
| onCrack | search | 1 | 32.0 [30.0–42.0] | 3/3 | 0.99 |
| onCrack | search | 16 | 90.0 [66.0–90.0] | 1/3 **←** | 1.01 |
| onCrack | post_message | 1 | 90.0 [34.0–91.4] | 1/3 **←** | 0.48 |
| onCrack | post_message | 16 | 90.4 [90.4–90.5] | 0/3 **←** | 1.05 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 149,908 | 149,908 | yes |
| onCrack | 1 | run c=1 | 18,157 | 18,157 | yes |
| onCrack | 1 | warm-up c=16 | 976,491 | 976,491 | yes |
| onCrack | 1 | run c=16 | 107,462 | 107,462 | yes |
| onCrack | 1 | **all** | 1,252,018 | 1,252,018 | yes |
| onCrack | 2 | warm-up c=1 | 227,912 | 227,912 | yes |
| onCrack | 2 | run c=1 | 22,366 | 22,366 | yes |
| onCrack | 2 | warm-up c=16 | 736,848 | 736,848 | yes |
| onCrack | 2 | run c=16 | 78,730 | 78,730 | yes |
| onCrack | 2 | **all** | 1,065,856 | 1,065,856 | yes |
| onCrack | 3 | warm-up c=1 | 301,131 | 301,131 | yes |
| onCrack | 3 | run c=1 | 15,460 | 15,460 | yes |
| onCrack | 3 | warm-up c=16 | 777,934 | 777,934 | yes |
| onCrack | 3 | run c=16 | 84,243 | 84,243 | yes |
| onCrack | 3 | **all** | 1,178,768 | 1,178,768 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| sidebar | 200 5,826 / 30,763 | 200 30,763 | 5,826 | – |
| search | 200 9,712 / 149,623 | 200 149,623 | 9,712 | – |
| post_message | – | – | 2,097 | – |
