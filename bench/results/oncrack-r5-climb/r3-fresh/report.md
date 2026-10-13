```
date: 2026-10-13T05:20:01-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
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
| cold start: docker run → /up 200 (ms) | 294 [228–305] |
| idle memory.current (MB) | 28.0 [28.0–29.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 696 [677–702] |
| peak anon under load (MB) | 181 [179–185] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 23,707 [23,216–24,015] |
| room_show c=1 CPU µs/req | 22.2 [22.0–22.8] |
| room_show c=1 p50 ms | 0.04 [0.04–0.04] |
| room_show c=1 p99 ms | 0.06 [0.06–0.06] |
| room_show c=16 req/s | 147,899 [141,822–149,480] |
| room_show c=16 CPU µs/req | 21.2 [20.7–22.4] |
| room_show c=16 p50 ms | 0.10 [0.10–0.10] |
| room_show c=16 p99 ms | 0.26 [0.26–0.28] |
| messages_page c=1 req/s | 24,114 [21,633–25,226] |
| messages_page c=1 CPU µs/req | 22.1 [21.1–24.2] |
| messages_page c=1 p50 ms | 0.04 [0.04–0.04] |
| messages_page c=1 p99 ms | 0.07 [0.06–0.16] |
| messages_page c=16 req/s | 154,724 [141,102–157,464] |
| messages_page c=16 CPU µs/req | 20.0 [19.5–23.1] |
| messages_page c=16 p50 ms | 0.09 [0.09–0.10] |
| messages_page c=16 p99 ms | 0.25 [0.24–0.30] |
| sidebar c=1 req/s | 24,920 [23,664–25,078] |
| sidebar c=1 CPU µs/req | 20.6 [20.5–21.7] |
| sidebar c=1 p50 ms | 0.04 [0.04–0.04] |
| sidebar c=1 p99 ms | 0.06 [0.05–0.06] |
| sidebar c=16 req/s | 166,078 [159,651–167,657] |
| sidebar c=16 CPU µs/req | 18.2 [17.9–19.1] |
| sidebar c=16 p50 ms | 0.09 [0.09–0.09] |
| sidebar c=16 p99 ms | 0.23 [0.23–0.25] |
| search c=1 req/s | 24,664 [21,595–24,955] |
| search c=1 CPU µs/req | 21.1 [20.8–23.9] |
| search c=1 p50 ms | 0.04 [0.04–0.04] |
| search c=1 p99 ms | 0.06 [0.06–0.17] |
| search c=16 req/s | 161,081 [146,114–162,264] |
| search c=16 CPU µs/req | 18.8 [18.5–22.6] |
| search c=16 p50 ms | 0.09 [0.09–0.10] |
| search c=16 p99 ms | 0.24 [0.24–0.31] |
| post_message c=1 req/s | 3,645 [3,469–4,976] |
| post_message c=1 CPU µs/req | 260 [257–282] |
| post_message c=1 p50 ms | 0.18 [0.18–0.20] |
| post_message c=1 p99 ms | 0.32 [0.31–0.36] |
| post_message c=16 req/s | 11,463 [11,184–12,202] |
| post_message c=16 CPU µs/req | 188 [186–189] |
| post_message c=16 p50 ms | 0.89 [0.87–0.89] |
| post_message c=16 p99 ms | 4.51 [4.51–4.52] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.34 2.86 3.04 | 3.02 3.11 3.05 |
| onCrack | 2 | 0.91 2.40 2.81 | 3.40 2.77 2.70 |
| onCrack | 3 | 1.39 2.31 2.55 | 4.66 3.62 2.99 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.10 | 1.12 | 0/10 | 1.09 |
| onCrack | 2 | 1.09 | 1.09 | 2/10 **noisy** | 1.11 |
| onCrack | 3 | 1.04 | 1.04 | 0/10 | 1.09 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 4,081,265 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 4,194,261 | 0 | 0 | 0 | 0 |
| onCrack | sidebar | 4,536,582 | 0 | 0 | 0 | 0 |
| onCrack | search | 4,325,557 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 385,488 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 38.0 [30.0–60.0] | 3/3 | 1.01 |
| onCrack | room_show | 16 | 30.0 [30.0–30.0] | 3/3 | 0.99 |
| onCrack | messages_page | 1 | 32.0 [30.0–90.0] | 2/3 **←** | 1.01 |
| onCrack | messages_page | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | sidebar | 1 | 30.0 [30.0–38.0] | 3/3 | 1.00 |
| onCrack | sidebar | 16 | 30.0 [30.0–30.0] | 3/3 | 0.99 |
| onCrack | search | 1 | 30.0 [30.0–90.0] | 2/3 **←** | 1.02 |
| onCrack | search | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | post_message | 1 | 30.0 [30.0–90.7] | 2/3 **←** | 1.00 |
| onCrack | post_message | 16 | 90.7 [90.3–90.9] | 0/3 **←** | 1.11 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 144,535 | 144,535 | yes |
| onCrack | 1 | run c=1 | 39,811 | 39,811 | yes |
| onCrack | 1 | warm-up c=16 | 1,048,283 | 1,048,283 | yes |
| onCrack | 1 | run c=16 | 91,714 | 91,714 | yes |
| onCrack | 1 | **all** | 1,324,343 | 1,324,343 | yes |
| onCrack | 2 | warm-up c=1 | 235,703 | 235,703 | yes |
| onCrack | 2 | run c=1 | 29,162 | 29,162 | yes |
| onCrack | 2 | warm-up c=16 | 958,345 | 958,345 | yes |
| onCrack | 2 | run c=16 | 95,906 | 95,906 | yes |
| onCrack | 2 | **all** | 1,319,116 | 1,319,116 | yes |
| onCrack | 3 | warm-up c=1 | 141,827 | 141,827 | yes |
| onCrack | 3 | run c=1 | 31,263 | 31,263 | yes |
| onCrack | 3 | warm-up c=16 | 988,683 | 988,683 | yes |
| onCrack | 3 | run c=16 | 97,632 | 97,632 | yes |
| onCrack | 3 | **all** | 1,259,405 | 1,259,405 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| sidebar | 200 5,826 / 30,763 | 200 30,763 | 5,826 | – |
| search | 200 9,712 / 149,623 | 200 149,623 | 9,712 | – |
| post_message | – | – | 2,097 | – |
