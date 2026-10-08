```
date: 2026-10-08T15:18:00-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:390e390e43faa666e99cfbc3a6bcc161d9a1c3709c952c908f48f7a979638129 2026-10-08T15:17:46.141811435-04:00 built from commit: 09415ba6bddbaa5b9d4904edf426c9b1ecee4ca8
repo HEAD: 09415ba (dirty: 0 files under src/ and rust/)
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
| cold start: docker run → /up 200 (ms) | 243 [190–249] |
| idle memory.current (MB) | 28.0 [28.0–29.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 733 [488–753] |
| peak anon under load (MB) | 181 [179–182] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 26,080 [25,852–26,151] |
| room_show c=1 CPU µs/req | 19.3 [19.1–19.4] |
| room_show c=1 p50 ms | 0.04 [0.04–0.04] |
| room_show c=1 p99 ms | 0.05 [0.05–0.05] |
| room_show c=16 req/s | 174,412 [174,354–175,796] |
| room_show c=16 CPU µs/req | 17.7 [17.7–17.9] |
| room_show c=16 p50 ms | 0.08 [0.08–0.08] |
| room_show c=16 p99 ms | 0.21 [0.21–0.21] |
| messages_page c=1 req/s | 25,963 [25,544–26,142] |
| messages_page c=1 CPU µs/req | 18.9 [18.8–19.3] |
| messages_page c=1 p50 ms | 0.04 [0.04–0.04] |
| messages_page c=1 p99 ms | 0.05 [0.05–0.05] |
| messages_page c=16 req/s | 184,722 [184,139–184,868] |
| messages_page c=16 CPU µs/req | 16.4 [16.3–16.4] |
| messages_page c=16 p50 ms | 0.08 [0.08–0.08] |
| messages_page c=16 p99 ms | 0.20 [0.20–0.20] |
| sidebar c=1 req/s | 26,723 [26,418–26,750] |
| sidebar c=1 CPU µs/req | 18.1 [17.9–18.2] |
| sidebar c=1 p50 ms | 0.04 [0.04–0.04] |
| sidebar c=1 p99 ms | 0.05 [0.05–0.05] |
| sidebar c=16 req/s | 197,204 [197,201–197,598] |
| sidebar c=16 CPU µs/req | 14.8 [14.8–14.8] |
| sidebar c=16 p50 ms | 0.07 [0.07–0.07] |
| sidebar c=16 p99 ms | 0.18 [0.18–0.19] |
| search c=1 req/s | 27,500 [27,254–27,555] |
| search c=1 CPU µs/req | 17.5 [17.5–17.7] |
| search c=1 p50 ms | 0.04 [0.04–0.04] |
| search c=1 p99 ms | 0.05 [0.05–0.05] |
| search c=16 req/s | 192,332 [192,252–193,711] |
| search c=16 CPU µs/req | 15.3 [15.3–15.4] |
| search c=16 p50 ms | 0.08 [0.08–0.08] |
| search c=16 p99 ms | 0.19 [0.19–0.19] |
| post_message c=1 req/s | 4,876 [4,127–4,951] |
| post_message c=1 CPU µs/req | 392 [389–392] |
| post_message c=1 p50 ms | 0.18 [0.18–0.18] |
| post_message c=1 p99 ms | 0.39 [0.37–0.39] |
| post_message c=16 req/s | 10,664 [10,362–12,293] |
| post_message c=16 CPU µs/req | 186 [185–186] |
| post_message c=16 p50 ms | 0.89 [0.89–0.90] |
| post_message c=16 p99 ms | 4.60 [4.57–4.63] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.17 2.20 2.84 | 4.62 3.25 2.98 |
| onCrack | 2 | 1.32 2.52 2.74 | 3.89 2.82 2.76 |
| onCrack | 3 | 1.34 2.28 2.57 | 3.37 2.89 2.73 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.05 | 1.04 | 0/10 | 1.09 |
| onCrack | 2 | 1.07 | 1.07 | 0/10 | 1.09 |
| onCrack | 3 | 1.06 | 1.04 | 0/10 | 1.09 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 4,821,371 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 5,051,219 | 0 | 0 | 0 | 0 |
| onCrack | sidebar | 5,375,341 | 0 | 0 | 0 | 0 |
| onCrack | search | 5,285,024 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 384,694 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | room_show | 16 | 30.0 [30.0–36.0] | 3/3 | 0.99 |
| onCrack | messages_page | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | messages_page | 16 | 30.0 [30.0–32.0] | 3/3 | 0.99 |
| onCrack | sidebar | 1 | 30.0 [30.0–30.0] | 3/3 | 1.02 |
| onCrack | sidebar | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | search | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | search | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | post_message | 1 | 30.0 [30.0–60.0] | 3/3 | 0.98 |
| onCrack | post_message | 16 | 90.2 [30.0–91.4] | 1/3 **←** | 0.89 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 282,597 | 282,597 | yes |
| onCrack | 1 | run c=1 | 33,018 | 33,018 | yes |
| onCrack | 1 | warm-up c=16 | 1,081,679 | 1,081,679 | yes |
| onCrack | 1 | run c=16 | 83,007 | 83,007 | yes |
| onCrack | 1 | **all** | 1,480,301 | 1,480,301 | yes |
| onCrack | 2 | warm-up c=1 | 144,788 | 144,788 | yes |
| onCrack | 2 | run c=1 | 39,606 | 39,606 | yes |
| onCrack | 2 | warm-up c=16 | 454,838 | 454,838 | yes |
| onCrack | 2 | run c=16 | 91,700 | 91,700 | yes |
| onCrack | 2 | **all** | 730,932 | 730,932 | yes |
| onCrack | 3 | warm-up c=1 | 144,847 | 144,847 | yes |
| onCrack | 3 | run c=1 | 39,007 | 39,007 | yes |
| onCrack | 3 | warm-up c=16 | 1,146,547 | 1,146,547 | yes |
| onCrack | 3 | run c=16 | 98,356 | 98,356 | yes |
| onCrack | 3 | **all** | 1,428,757 | 1,428,757 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| sidebar | 200 5,826 / 30,763 | 200 30,763 | 5,826 | – |
| search | 200 9,713 / 149,623 | 200 149,623 | 9,713 | – |
| post_message | – | – | 2,097 | – |
