```
date: 2026-10-07T07:47:18-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:78b7c9f9bcdc06887dfb0bdd2d47fca8279c7492e642a36a5f37caace362c3d1 2026-10-07T07:46:54.565800272-04:00 built from commit: 2de7519d49865f7514a6973540c2d781d32c5dca
repo HEAD: 2de7519 (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-07 07:47:18), built with rust:1.98.1-trixie
schedule: apps oncrack, reps 3; suites: http; http secs 8, concs 1 16, routes room_show messages_page sidebar search post_message (in parts, --part 1/2 is one slice of them), warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 3. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 238 [201–249] |
| idle memory.current (MB) | 27.0 [27.0–28.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 424 [416–425] |
| peak anon under load (MB) | 214 [214–217] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 7,450 [7,440–7,468] |
| room_show c=1 CPU µs/req | 211 [209–213] |
| room_show c=1 p50 ms | 0.13 [0.13–0.13] |
| room_show c=1 p99 ms | 0.18 [0.18–0.18] |
| room_show c=16 req/s | 38,994 [38,728–39,005] |
| room_show c=16 CPU µs/req | 91.6 [91.5–92.1] |
| room_show c=16 p50 ms | 0.39 [0.38–0.39] |
| room_show c=16 p99 ms | 1.08 [1.07–1.09] |
| messages_page c=1 req/s | 8,148 [8,028–8,161] |
| messages_page c=1 CPU µs/req | 203 [202–204] |
| messages_page c=1 p50 ms | 0.12 [0.12–0.12] |
| messages_page c=1 p99 ms | 0.17 [0.17–0.18] |
| messages_page c=16 req/s | 41,859 [41,372–42,306] |
| messages_page c=16 CPU µs/req | 84.9 [84.2–85.3] |
| messages_page c=16 p50 ms | 0.36 [0.36–0.36] |
| messages_page c=16 p99 ms | 1.02 [1.00–1.03] |
| sidebar c=1 req/s | 7,620 [7,602–7,662] |
| sidebar c=1 CPU µs/req | 190 [189–194] |
| sidebar c=1 p50 ms | 0.12 [0.12–0.12] |
| sidebar c=1 p99 ms | 0.18 [0.18–0.19] |
| sidebar c=16 req/s | 37,894 [37,615–37,950] |
| sidebar c=16 CPU µs/req | 95.1 [95.1–95.9] |
| sidebar c=16 p50 ms | 0.39 [0.39–0.40] |
| sidebar c=16 p99 ms | 1.07 [1.06–1.07] |
| search c=1 req/s | 5,669 [5,652–5,803] |
| search c=1 CPU µs/req | 328 [328–329] |
| search c=1 p50 ms | 0.17 [0.17–0.17] |
| search c=1 p99 ms | 0.22 [0.22–0.22] |
| search c=16 req/s | 33,931 [33,857–33,994] |
| search c=16 CPU µs/req | 108 [108–108] |
| search c=16 p50 ms | 0.44 [0.44–0.45] |
| search c=16 p99 ms | 1.30 [1.29–1.32] |
| post_message c=1 req/s | 2,970 [2,885–2,971] |
| post_message c=1 CPU µs/req | 642 [640–646] |
| post_message c=1 p50 ms | 0.32 [0.31–0.32] |
| post_message c=1 p99 ms | 0.57 [0.55–0.63] |
| post_message c=16 req/s | 8,566 [8,492–8,803] |
| post_message c=16 CPU µs/req | 360 [356–361] |
| post_message c=16 p50 ms | 1.58 [1.56–1.59] |
| post_message c=16 p99 ms | 6.15 [6.06–6.28] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.25 1.58 1.99 | 5.16 3.28 2.60 |
| onCrack | 2 | 1.38 2.52 2.39 | 3.88 3.12 2.68 |
| onCrack | 3 | 1.44 2.54 2.51 | 3.96 3.09 2.73 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.03 | 1.03 | 0/10 | 1.06 |
| onCrack | 2 | 1.01 | 1.03 | 0/10 | 1.05 |
| onCrack | 3 | 1.04 | 1.06 | 0/10 | 1.05 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 1,112,850 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 1,199,082 | 0 | 0 | 0 | 0 |
| onCrack | sidebar | 1,090,811 | 0 | 0 | 0 | 0 |
| onCrack | search | 951,318 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 277,576 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | room_show | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | messages_page | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | messages_page | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | sidebar | 1 | 30.0 [30.0–32.0] | 3/3 | 1.00 |
| onCrack | sidebar | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | search | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | search | 16 | 30.0 [30.0–30.0] | 3/3 | 1.01 |
| onCrack | post_message | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | post_message | 16 | 30.0 [30.0–32.0] | 3/3 | 0.99 |

### Rows written by `post_message` (messages of the write room counted in the app's SQLite file around each run)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 86,388 | 86,388 | yes |
| onCrack | 1 | run c=1 | 23,082 | 23,082 | yes |
| onCrack | 1 | warm-up c=16 | 228,843 | 228,843 | yes |
| onCrack | 1 | run c=16 | 70,445 | 70,445 | yes |
| onCrack | 1 | **all** | 408,758 | 408,758 | yes |
| onCrack | 2 | warm-up c=1 | 87,849 | 87,849 | yes |
| onCrack | 2 | run c=1 | 23,769 | 23,769 | yes |
| onCrack | 2 | warm-up c=16 | 274,940 | 274,940 | yes |
| onCrack | 2 | run c=16 | 67,974 | 67,974 | yes |
| onCrack | 2 | **all** | 454,532 | 454,532 | yes |
| onCrack | 3 | warm-up c=1 | 87,656 | 87,656 | yes |
| onCrack | 3 | run c=1 | 23,765 | 23,765 | yes |
| onCrack | 3 | warm-up c=16 | 262,931 | 262,931 | yes |
| onCrack | 3 | run c=16 | 68,541 | 68,541 | yes |
| onCrack | 3 | **all** | 442,893 | 442,893 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| sidebar | 200 5,910 / 30,763 | 200 30,763 | 5,910 | – |
| search | 200 9,713 / 149,623 | 200 149,623 | 9,713 | – |
| post_message | – | – | 1,993 | – |
