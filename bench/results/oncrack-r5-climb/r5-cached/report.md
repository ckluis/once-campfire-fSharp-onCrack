```
date: 2026-10-13T08:05:59-04:00
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
| cold start: docker run → /up 200 (ms) | 268 [233–274] |
| idle memory.current (MB) | 28.0 [28.0–29.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 589 [467–683] |
| peak anon under load (MB) | 183 [181–185] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 15,964 [14,611–23,366] |
| room_show c=1 CPU µs/req | 30.2 [21.7–34.7] |
| room_show c=1 p50 ms | 0.05 [0.04–0.06] |
| room_show c=1 p99 ms | 0.17 [0.06–0.17] |
| room_show c=16 req/s | 98,740 [37,756–139,056] |
| room_show c=16 CPU µs/req | 26.8 [24.7–45.1] |
| room_show c=16 p50 ms | 0.12 [0.11–0.12] |
| room_show c=16 p99 ms | 0.83 [0.40–6.66] |
| messages_page c=1 req/s | 22,846 [22,743–24,516] |
| messages_page c=1 CPU µs/req | 21.8 [20.4–22.2] |
| messages_page c=1 p50 ms | 0.04 [0.04–0.05] |
| messages_page c=1 p99 ms | 0.08 [0.07–0.14] |
| messages_page c=16 req/s | 156,956 [126,638–160,063] |
| messages_page c=16 CPU µs/req | 21.4 [20.5–24.2] |
| messages_page c=16 p50 ms | 0.09 [0.09–0.11] |
| messages_page c=16 p99 ms | 0.29 [0.28–0.42] |
| sidebar c=1 req/s | 23,668 [3,280–30,859] |
| sidebar c=1 CPU µs/req | 19.7 [16.4–126.0] |
| sidebar c=1 p50 ms | 0.04 [0.02–0.12] |
| sidebar c=1 p99 ms | 0.12 [0.10–3.55] |
| sidebar c=16 req/s | 176,224 [132,057–177,347] |
| sidebar c=16 CPU µs/req | 18.8 [16.9–21.6] |
| sidebar c=16 p50 ms | 0.09 [0.08–0.09] |
| sidebar c=16 p99 ms | 0.26 [0.21–0.54] |
| search c=1 req/s | 22,871 [7,250–22,972] |
| search c=1 CPU µs/req | 21.4 [20.5–65.8] |
| search c=1 p50 ms | 0.05 [0.04–0.10] |
| search c=1 p99 ms | 0.10 [0.06–0.73] |
| search c=16 req/s | 181,946 [157,925–190,599] |
| search c=16 CPU µs/req | 17.0 [15.6–21.1] |
| search c=16 p50 ms | 0.08 [0.08–0.09] |
| search c=16 p99 ms | 0.20 [0.19–0.33] |
| post_message c=1 req/s | 2,060 [499–2,309] |
| post_message c=1 CPU µs/req | 435 [303–2,041] |
| post_message c=1 p50 ms | 0.21 [0.20–1.06] |
| post_message c=1 p99 ms | 3.52 [0.84–21.34] |
| post_message c=16 req/s | 8,912 [7,089–11,928] |
| post_message c=16 CPU µs/req | 212 [209–407] |
| post_message c=16 p50 ms | 1.01 [0.95–1.98] |
| post_message c=16 p99 ms | 6.15 [5.78–7.37] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 0.33 0.29 0.79 | 3.65 2.83 2.00 |
| onCrack | 2 | 0.44 1.66 1.68 | 3.47 3.07 2.47 |
| onCrack | 3 | 1.25 2.49 2.31 | 4.08 3.60 3.04 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.08 | 1.15 | 8/10 **noisy** | 2.98 |
| onCrack | 2 | 1.09 | 1.09 | 6/10 **noisy** | 3.30 |
| onCrack | 3 | 1.07 | 1.48 | 5/10 **noisy** | 2.39 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 2,636,323 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 4,110,301 | 0 | 0 | 0 | 0 |
| onCrack | sidebar | 4,347,683 | 0 | 0 | 0 | 0 |
| onCrack | search | 4,668,690 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 273,196 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 90.1 [90.0–90.1] | 0/3 **←** | 1.31 |
| onCrack | room_show | 16 | 90.0 [58.2–90.5] | 1/3 **←** | 0.96 |
| onCrack | messages_page | 1 | 62.0 [32.0–72.1] | 3/3 | 1.02 |
| onCrack | messages_page | 16 | 32.0 [32.0–58.0] | 3/3 | 0.88 |
| onCrack | sidebar | 1 | 44.0 [30.0–90.1] | 2/3 **←** | 1.11 |
| onCrack | sidebar | 16 | 62.0 [32.0–90.1] | 2/3 **←** | 0.95 |
| onCrack | search | 1 | 90.0 [32.0–90.2] | 1/3 **←** | 0.98 |
| onCrack | search | 16 | 90.0 [66.2–90.0] | 2/3 **←** | 1.10 |
| onCrack | post_message | 1 | 90.4 [90.3–91.6] | 0/3 **←** | 1.10 |
| onCrack | post_message | 16 | 90.8 [90.7–90.9] | 0/3 **←** | 1.40 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 201,493 | 201,493 | yes |
| onCrack | 1 | run c=1 | 3,992 | 3,992 | yes |
| onCrack | 1 | warm-up c=16 | 386,884 | 386,884 | yes |
| onCrack | 1 | run c=16 | 56,728 | 56,728 | yes |
| onCrack | 1 | **all** | 649,097 | 649,097 | yes |
| onCrack | 2 | warm-up c=1 | 251,629 | 251,629 | yes |
| onCrack | 2 | run c=1 | 20,502 | 20,502 | yes |
| onCrack | 2 | warm-up c=16 | 656,036 | 656,036 | yes |
| onCrack | 2 | run c=16 | 80,060 | 80,060 | yes |
| onCrack | 2 | **all** | 1,008,227 | 1,008,227 | yes |
| onCrack | 3 | warm-up c=1 | 317,887 | 317,887 | yes |
| onCrack | 3 | run c=1 | 16,482 | 16,482 | yes |
| onCrack | 3 | warm-up c=16 | 867,478 | 867,478 | yes |
| onCrack | 3 | run c=16 | 95,432 | 95,432 | yes |
| onCrack | 3 | **all** | 1,297,279 | 1,297,279 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| sidebar | 200 5,826 / 30,763 | 200 30,763 | 5,826 | – |
| search | 200 9,712 / 149,623 | 200 149,623 | 9,712 | – |
| post_message | – | – | 2,097 | – |
