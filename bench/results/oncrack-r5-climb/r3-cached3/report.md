```
date: 2026-10-13T10:58:41-04:00
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
| cold start: docker run → /up 200 (ms) | 242 [220–267] |
| idle memory.current (MB) | 28.0 [28.0–29.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 616 [550–713] |
| peak anon under load (MB) | 181 [180–181] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 25,732 [24,633–26,031] |
| room_show c=1 CPU µs/req | 19.4 [19.0–20.4] |
| room_show c=1 p50 ms | 0.04 [0.04–0.04] |
| room_show c=1 p99 ms | 0.05 [0.05–0.06] |
| room_show c=16 req/s | 176,893 [176,267–177,291] |
| room_show c=16 CPU µs/req | 17.5 [17.5–17.7] |
| room_show c=16 p50 ms | 0.08 [0.08–0.08] |
| room_show c=16 p99 ms | 0.21 [0.21–0.21] |
| messages_page c=1 req/s | 25,126 [23,637–25,590] |
| messages_page c=1 CPU µs/req | 19.5 [19.2–20.8] |
| messages_page c=1 p50 ms | 0.04 [0.04–0.04] |
| messages_page c=1 p99 ms | 0.05 [0.05–0.05] |
| messages_page c=16 req/s | 185,303 [180,626–185,355] |
| messages_page c=16 CPU µs/req | 16.5 [16.3–16.8] |
| messages_page c=16 p50 ms | 0.08 [0.08–0.08] |
| messages_page c=16 p99 ms | 0.20 [0.20–0.21] |
| sidebar c=1 req/s | 25,572 [25,236–26,010] |
| sidebar c=1 CPU µs/req | 18.7 [18.6–19.0] |
| sidebar c=1 p50 ms | 0.04 [0.04–0.04] |
| sidebar c=1 p99 ms | 0.05 [0.05–0.12] |
| sidebar c=16 req/s | 197,055 [178,814–197,798] |
| sidebar c=16 CPU µs/req | 15.0 [14.9–17.8] |
| sidebar c=16 p50 ms | 0.07 [0.07–0.08] |
| sidebar c=16 p99 ms | 0.19 [0.19–0.24] |
| search c=1 req/s | 24,542 [24,509–25,331] |
| search c=1 CPU µs/req | 19.7 [18.9–19.9] |
| search c=1 p50 ms | 0.04 [0.04–0.04] |
| search c=1 p99 ms | 0.05 [0.05–0.05] |
| search c=16 req/s | 191,404 [189,437–192,927] |
| search c=16 CPU µs/req | 15.6 [15.6–15.7] |
| search c=16 p50 ms | 0.08 [0.08–0.08] |
| search c=16 p99 ms | 0.19 [0.19–0.19] |
| post_message c=1 req/s | 3,533 [2,140–5,038] |
| post_message c=1 CPU µs/req | 258 [251–298] |
| post_message c=1 p50 ms | 0.18 [0.17–0.20] |
| post_message c=1 p99 ms | 0.33 [0.30–0.78] |
| post_message c=16 req/s | 8,057 [7,626–10,891] |
| post_message c=16 CPU µs/req | 181 [181–199] |
| post_message c=16 p50 ms | 0.88 [0.88–0.93] |
| post_message c=16 p99 ms | 4.69 [4.56–4.79] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.37 2.60 2.61 | 2.53 2.77 2.74 |
| onCrack | 2 | 1.27 2.40 2.61 | 3.28 2.98 2.83 |
| onCrack | 3 | 1.47 2.51 2.68 | 3.13 3.07 2.91 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.05 | 1.07 | 3/10 **noisy** | 1.15 |
| onCrack | 2 | 1.07 | 1.04 | 0/10 | 1.09 |
| onCrack | 3 | 1.04 | 1.07 | 0/10 | 1.07 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 4,854,981 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 5,005,270 | 0 | 0 | 0 | 0 |
| onCrack | sidebar | 5,204,208 | 0 | 0 | 0 | 0 |
| onCrack | search | 5,185,370 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 304,891 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 30.0 [30.0–34.0] | 3/3 | 1.01 |
| onCrack | room_show | 16 | 30.0 [30.0–74.0] | 3/3 | 1.02 |
| onCrack | messages_page | 1 | 30.0 [30.0–30.0] | 3/3 | 1.02 |
| onCrack | messages_page | 16 | 30.0 [30.0–56.0] | 3/3 | 1.00 |
| onCrack | sidebar | 1 | 32.0 [32.0–36.0] | 3/3 | 1.03 |
| onCrack | sidebar | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | search | 1 | 38.0 [30.0–90.0] | 2/3 **←** | 1.02 |
| onCrack | search | 16 | 30.0 [30.0–44.0] | 3/3 | 1.01 |
| onCrack | post_message | 1 | 90.5 [30.0–91.8] | 1/3 **←** | 1.00 |
| onCrack | post_message | 16 | 91.1 [30.0–91.2] | 1/3 **←** | 0.90 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 261,233 | 261,233 | yes |
| onCrack | 1 | run c=1 | 19,225 | 19,225 | yes |
| onCrack | 1 | warm-up c=16 | 747,267 | 747,267 | yes |
| onCrack | 1 | run c=16 | 63,743 | 63,743 | yes |
| onCrack | 1 | **all** | 1,091,468 | 1,091,468 | yes |
| onCrack | 2 | warm-up c=1 | 339,419 | 339,419 | yes |
| onCrack | 2 | run c=1 | 30,012 | 30,012 | yes |
| onCrack | 2 | warm-up c=16 | 472,091 | 472,091 | yes |
| onCrack | 2 | run c=16 | 64,464 | 64,464 | yes |
| onCrack | 2 | **all** | 905,986 | 905,986 | yes |
| onCrack | 3 | warm-up c=1 | 147,134 | 147,134 | yes |
| onCrack | 3 | run c=1 | 40,309 | 40,309 | yes |
| onCrack | 3 | warm-up c=16 | 1,115,932 | 1,115,932 | yes |
| onCrack | 3 | run c=16 | 87,138 | 87,138 | yes |
| onCrack | 3 | **all** | 1,390,513 | 1,390,513 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| sidebar | 200 5,826 / 30,763 | 200 30,763 | 5,826 | – |
| search | 200 9,712 / 149,623 | 200 149,623 | 9,712 | – |
| post_message | – | – | 2,096 | – |
