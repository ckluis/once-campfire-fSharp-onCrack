```
date: 2026-10-07T08:50:27-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:75caf211cc3721a7ab4b6eebec7e21fa4f4ed4cc3859fff3436e87a21f28d21b 2026-10-07T08:50:08.575773277-04:00 built from commit: 23cf3346587c33001f160ef7aa7d9e86311706ec
repo HEAD: 23cf334 (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-07 07:47:18), built with rust:1.98.1-trixie
schedule: apps oncrack, reps 3; suites: http; http secs 8, concs 1 16, routes room_show messages_page sidebar search post_message (in parts, --part 1/2 is one slice of them), warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 3. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 224 [222–250] |
| idle memory.current (MB) | 28.0 [28.0–28.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 433 [431–468] |
| peak anon under load (MB) | 215 [215–216] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 12,004 [11,776–12,058] |
| room_show c=1 CPU µs/req | 151 [150–152] |
| room_show c=1 p50 ms | 0.08 [0.08–0.08] |
| room_show c=1 p99 ms | 0.12 [0.12–0.12] |
| room_show c=16 req/s | 102,722 [101,975–102,898] |
| room_show c=16 CPU µs/req | 32.4 [32.3–32.6] |
| room_show c=16 p50 ms | 0.13 [0.13–0.13] |
| room_show c=16 p99 ms | 0.41 [0.41–0.41] |
| messages_page c=1 req/s | 12,032 [11,812–12,249] |
| messages_page c=1 CPU µs/req | 154 [151–154] |
| messages_page c=1 p50 ms | 0.08 [0.08–0.08] |
| messages_page c=1 p99 ms | 0.12 [0.12–0.12] |
| messages_page c=16 req/s | 101,682 [94,641–106,328] |
| messages_page c=16 CPU µs/req | 29.8 [29.6–31.0] |
| messages_page c=16 p50 ms | 0.13 [0.12–0.13] |
| messages_page c=16 p99 ms | 0.45 [0.44–0.48] |
| sidebar c=1 req/s | 13,600 [13,459–13,666] |
| sidebar c=1 CPU µs/req | 138 [137–139] |
| sidebar c=1 p50 ms | 0.07 [0.07–0.07] |
| sidebar c=1 p99 ms | 0.11 [0.11–0.11] |
| sidebar c=16 req/s | 112,827 [106,386–117,590] |
| sidebar c=16 CPU µs/req | 26.6 [26.5–26.8] |
| sidebar c=16 p50 ms | 0.11 [0.11–0.12] |
| sidebar c=16 p99 ms | 0.35 [0.34–0.35] |
| search c=1 req/s | 12,885 [12,798–12,929] |
| search c=1 CPU µs/req | 145 [144–146] |
| search c=1 p50 ms | 0.07 [0.07–0.07] |
| search c=1 p99 ms | 0.11 [0.11–0.11] |
| search c=16 req/s | 72,311 [71,202–73,672] |
| search c=16 CPU µs/req | 31.1 [30.8–31.5] |
| search c=16 p50 ms | 0.23 [0.22–0.23] |
| search c=16 p99 ms | 0.37 [0.36–0.37] |
| post_message c=1 req/s | 3,026 [2,994–3,042] |
| post_message c=1 CPU µs/req | 635 [631–639] |
| post_message c=1 p50 ms | 0.31 [0.31–0.31] |
| post_message c=1 p99 ms | 0.56 [0.55–0.56] |
| post_message c=16 req/s | 8,631 [8,284–8,761] |
| post_message c=16 CPU µs/req | 357 [353–363] |
| post_message c=16 p50 ms | 1.58 [1.56–1.61] |
| post_message c=16 p99 ms | 6.13 [6.11–6.42] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.42 3.13 2.31 | 4.04 3.16 2.69 |
| onCrack | 2 | 1.33 2.52 2.49 | 5.22 3.55 3.04 |
| onCrack | 3 | 1.45 2.73 2.79 | 5.58 3.62 3.18 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.04 | 1.03 | 0/10 | 1.05 |
| onCrack | 2 | 1.03 | 1.03 | 0/10 | 1.04 |
| onCrack | 3 | 1.02 | 1.03 | 0/10 | 1.05 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 2,747,604 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 2,710,098 | 0 | 0 | 0 | 0 |
| onCrack | sidebar | 3,020,375 | 0 | 0 | 0 | 0 |
| onCrack | search | 2,046,475 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 277,947 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | room_show | 16 | 34.0 [30.0–36.0] | 3/3 | 1.01 |
| onCrack | messages_page | 1 | 90.0 [30.0–90.0] | 1/3 **←** | 1.00 |
| onCrack | messages_page | 16 | 38.0 [36.0–90.0] | 2/3 **←** | 1.00 |
| onCrack | sidebar | 1 | 30.0 [30.0–30.0] | 3/3 | 0.99 |
| onCrack | sidebar | 16 | 42.0 [30.0–88.0] | 3/3 | 1.02 |
| onCrack | search | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | search | 16 | 34.0 [30.0–56.0] | 3/3 | 0.98 |
| onCrack | post_message | 1 | 30.0 [30.0–30.0] | 3/3 | 0.99 |
| onCrack | post_message | 16 | 32.0 [30.0–44.0] | 3/3 | 1.01 |

### Rows written by `post_message` (messages of the write room counted in the app's SQLite file around each run)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 89,119 | 89,119 | yes |
| onCrack | 1 | run c=1 | 24,205 | 24,205 | yes |
| onCrack | 1 | warm-up c=16 | 260,276 | 260,276 | yes |
| onCrack | 1 | run c=16 | 70,109 | 70,109 | yes |
| onCrack | 1 | **all** | 443,709 | 443,709 | yes |
| onCrack | 2 | warm-up c=1 | 87,340 | 87,340 | yes |
| onCrack | 2 | run c=1 | 23,956 | 23,956 | yes |
| onCrack | 2 | warm-up c=16 | 382,179 | 382,179 | yes |
| onCrack | 2 | run c=16 | 66,284 | 66,284 | yes |
| onCrack | 2 | **all** | 559,759 | 559,759 | yes |
| onCrack | 3 | warm-up c=1 | 89,989 | 89,989 | yes |
| onCrack | 3 | run c=1 | 24,333 | 24,333 | yes |
| onCrack | 3 | warm-up c=16 | 275,135 | 275,135 | yes |
| onCrack | 3 | run c=16 | 69,060 | 69,060 | yes |
| onCrack | 3 | **all** | 458,517 | 458,517 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| sidebar | 200 5,910 / 30,763 | 200 30,763 | 5,910 | – |
| search | 200 9,713 / 149,623 | 200 149,623 | 9,713 | – |
| post_message | – | – | 1,993 | – |
