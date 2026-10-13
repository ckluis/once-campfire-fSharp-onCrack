```
date: 2026-10-13T08:55:00-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: CAMPFIRE_FRESH_AUTH=0
user agent: (none)
oncrack image: campfire-oncrack:r3final sha256:e34e485ff87ddd3d1fdb7f5dbebe6f2a1a563b3b8f6ccb5f403f31b6fbc753a4 2026-10-13T04:46:33.001661448-04:00 built from commit: 37c5988
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
| cold start: docker run → /up 200 (ms) | 262 [258–332] |
| idle memory.current (MB) | 28.0 [28.0–29.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 459 [398–685] |
| peak anon under load (MB) | 178 [178–180] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 22,144 [3,253–24,375] |
| room_show c=1 CPU µs/req | 22.6 [21.1–115.0] |
| room_show c=1 p50 ms | 0.05 [0.04–0.13] |
| room_show c=1 p99 ms | 0.11 [0.06–3.49] |
| room_show c=16 req/s | 152,856 [144,689–157,028] |
| room_show c=16 CPU µs/req | 22.0 [20.7–23.5] |
| room_show c=16 p50 ms | 0.10 [0.10–0.10] |
| room_show c=16 p99 ms | 0.25 [0.24–0.33] |
| messages_page c=1 req/s | 21,188 [6,528–22,422] |
| messages_page c=1 CPU µs/req | 23.2 [22.1–72.1] |
| messages_page c=1 p50 ms | 0.05 [0.05–0.11] |
| messages_page c=1 p99 ms | 0.06 [0.06–0.93] |
| messages_page c=16 req/s | 125,689 [110,322–180,418] |
| messages_page c=16 CPU µs/req | 23.2 [16.7–24.7] |
| messages_page c=16 p50 ms | 0.10 [0.08–0.11] |
| messages_page c=16 p99 ms | 0.70 [0.20–0.74] |
| sidebar c=1 req/s | 23,011 [3,905–27,785] |
| sidebar c=1 CPU µs/req | 21.1 [17.9–105.8] |
| sidebar c=1 p50 ms | 0.04 [0.04–0.12] |
| sidebar c=1 p99 ms | 0.15 [0.05–2.34] |
| sidebar c=16 req/s | 159,952 [24,001–185,408] |
| sidebar c=16 CPU µs/req | 20.4 [16.3–68.8] |
| sidebar c=16 p50 ms | 0.09 [0.08–0.18] |
| sidebar c=16 p99 ms | 0.39 [0.20–9.15] |
| search c=1 req/s | 15,570 [2,956–16,470] |
| search c=1 CPU µs/req | 31.8 [30.4–162.3] |
| search c=1 p50 ms | 0.05 [0.05–0.14] |
| search c=1 p99 ms | 0.22 [0.21–3.90] |
| search c=16 req/s | 150,571 [131,973–163,353] |
| search c=16 CPU µs/req | 21.4 [19.9–22.5] |
| search c=16 p50 ms | 0.09 [0.09–0.10] |
| search c=16 p99 ms | 0.40 [0.33–0.48] |
| post_message c=1 req/s | 3,257 [962–4,414] |
| post_message c=1 CPU µs/req | 360 [295–1,203] |
| post_message c=1 p50 ms | 0.21 [0.20–0.88] |
| post_message c=1 p99 ms | 2.02 [0.51–5.12] |
| post_message c=16 req/s | 12,371 [8,011–12,846] |
| post_message c=16 CPU µs/req | 210 [185–303] |
| post_message c=16 p50 ms | 1.00 [0.88–1.45] |
| post_message c=16 p99 ms | 4.65 [4.47–6.18] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.37 2.88 2.83 | 4.42 3.67 3.19 |
| onCrack | 2 | 0.91 2.62 2.86 | 2.77 2.73 2.81 |
| onCrack | 3 | 1.32 2.34 2.67 | 3.29 2.99 2.76 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.08 | 1.05 | 3/10 **noisy** | 1.15 |
| onCrack | 2 | 1.09 | 1.70 | 7/10 **noisy** | 4.55 |
| onCrack | 3 | 1.09 | 1.40 | 7/10 **noisy** | 2.43 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 4,034,947 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 3,732,718 | 0 | 0 | 0 | 0 |
| onCrack | sidebar | 3,392,683 | 0 | 0 | 0 | 0 |
| onCrack | search | 3,847,510 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 339,114 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 90.0 [38.0–90.2] | 1/3 **←** | 1.00 |
| onCrack | room_show | 16 | 56.0 [46.0–56.1] | 3/3 | 1.04 |
| onCrack | messages_page | 1 | 90.0 [30.0–90.1] | 1/3 **←** | 1.00 |
| onCrack | messages_page | 16 | 30.0 [30.0–90.6] | 2/3 **←** | 1.00 |
| onCrack | sidebar | 1 | 90.0 [30.0–90.0] | 1/3 **←** | 0.98 |
| onCrack | sidebar | 16 | 62.0 [50.2–90.0] | 2/3 **←** | 0.99 |
| onCrack | search | 1 | 90.0 [90.0–90.1] | 0/3 **←** | 1.08 |
| onCrack | search | 16 | 90.0 [44.2–90.1] | 1/3 **←** | 1.10 |
| onCrack | post_message | 1 | 90.2 [32.0–90.5] | 1/3 **←** | 1.05 |
| onCrack | post_message | 16 | 32.0 [30.0–90.6] | 2/3 **←** | 1.05 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 200,190 | 200,190 | yes |
| onCrack | 1 | run c=1 | 7,694 | 7,694 | yes |
| onCrack | 1 | warm-up c=16 | 970,720 | 970,720 | yes |
| onCrack | 1 | run c=16 | 103,159 | 103,159 | yes |
| onCrack | 1 | **all** | 1,281,763 | 1,281,763 | yes |
| onCrack | 2 | warm-up c=1 | 63,069 | 63,069 | yes |
| onCrack | 2 | run c=1 | 26,062 | 26,062 | yes |
| onCrack | 2 | warm-up c=16 | 326,121 | 326,121 | yes |
| onCrack | 2 | run c=16 | 64,102 | 64,102 | yes |
| onCrack | 2 | **all** | 479,354 | 479,354 | yes |
| onCrack | 3 | warm-up c=1 | 232,808 | 232,808 | yes |
| onCrack | 3 | run c=1 | 35,312 | 35,312 | yes |
| onCrack | 3 | warm-up c=16 | 266,498 | 266,498 | yes |
| onCrack | 3 | run c=16 | 102,785 | 102,785 | yes |
| onCrack | 3 | **all** | 637,403 | 637,403 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| sidebar | 200 5,826 / 30,763 | 200 30,763 | 5,826 | – |
| search | 200 9,712 / 149,623 | 200 149,623 | 9,712 | – |
| post_message | – | – | 2,097 | – |
