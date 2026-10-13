```
date: 2026-10-07T10:27:46-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:56c3c35f8fd5e742ed90860e4b043c2f9496b320301af599f69c4b965b9dec96 2026-10-07T10:27:20.937724291-04:00 built from commit: 0f3e1202e2a9c6d094ba0073530d3f0af4df8dd5
repo HEAD: 0f3e120 (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-07 07:47:18), built with rust:1.98.1-trixie
schedule: apps oncrack, reps 3; suites: http; http secs 8, concs 1 16, routes room_show messages_page sidebar search post_message (in parts, --part 1/2 is one slice of them), warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 3. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 230 [218–239] |
| idle memory.current (MB) | 28.0 [28.0–28.0] |
| idle anon (MB) | 15.0 [15.0–15.0] |
| peak memory.current under load (MB) | 483 [475–525] |
| peak anon under load (MB) | 217 [217–218] |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | onCrack |
|---|---|
| room_show c=1 req/s | 11,821 [11,646–11,941] |
| room_show c=1 CPU µs/req | 152 [151–154] |
| room_show c=1 p50 ms | 0.08 [0.08–0.08] |
| room_show c=1 p99 ms | 0.12 [0.12–0.12] |
| room_show c=16 req/s | 98,146 [95,932–99,701] |
| room_show c=16 CPU µs/req | 31.8 [31.6–31.9] |
| room_show c=16 p50 ms | 0.13 [0.13–0.14] |
| room_show c=16 p99 ms | 0.42 [0.41–0.43] |
| messages_page c=1 req/s | 12,527 [12,267–12,682] |
| messages_page c=1 CPU µs/req | 148 [147–151] |
| messages_page c=1 p50 ms | 0.08 [0.08–0.08] |
| messages_page c=1 p99 ms | 0.12 [0.11–0.12] |
| messages_page c=16 req/s | 101,732 [101,459–101,789] |
| messages_page c=16 CPU µs/req | 30.3 [30.1–30.6] |
| messages_page c=16 p50 ms | 0.13 [0.13–0.13] |
| messages_page c=16 p99 ms | 0.46 [0.46–0.47] |
| sidebar c=1 req/s | 13,491 [13,129–13,775] |
| sidebar c=1 CPU µs/req | 138 [136–139] |
| sidebar c=1 p50 ms | 0.07 [0.07–0.07] |
| sidebar c=1 p99 ms | 0.11 [0.11–0.11] |
| sidebar c=16 req/s | 108,132 [74,972–109,109] |
| sidebar c=16 CPU µs/req | 27.2 [27.0–29.9] |
| sidebar c=16 p50 ms | 0.12 [0.12–0.23] |
| sidebar c=16 p99 ms | 0.36 [0.35–0.38] |
| search c=1 req/s | 12,595 [12,571–12,938] |
| search c=1 CPU µs/req | 145 [144–148] |
| search c=1 p50 ms | 0.08 [0.07–0.08] |
| search c=1 p99 ms | 0.11 [0.11–0.12] |
| search c=16 req/s | 74,061 [70,983–74,762] |
| search c=16 CPU µs/req | 31.2 [30.6–31.4] |
| search c=16 p50 ms | 0.23 [0.22–0.23] |
| search c=16 p99 ms | 0.37 [0.37–0.37] |
| post_message c=1 req/s | 3,123 [3,023–3,176] |
| post_message c=1 CPU µs/req | 622 [609–622] |
| post_message c=1 p50 ms | 0.30 [0.29–0.30] |
| post_message c=1 p99 ms | 0.56 [0.55–0.59] |
| post_message c=16 req/s | 12,953 [12,572–12,983] |
| post_message c=16 CPU µs/req | 237 [235–238] |
| post_message c=16 p50 ms | 1.07 [1.06–1.08] |
| post_message c=16 p99 ms | 5.54 [5.43–5.82] |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.48 2.12 2.07 | 3.97 3.19 2.79 |
| onCrack | 2 | 1.49 2.62 2.62 | 4.37 3.08 2.84 |
| onCrack | 3 | 1.47 2.47 2.65 | 4.00 3.31 3.08 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.03 | 1.01 | 0/10 | 1.07 |
| onCrack | 2 | 1.04 | 1.04 | 0/10 | 1.07 |
| onCrack | 3 | 1.02 | 1.05 | 0/10 | 1.05 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| onCrack | room_show | 2,633,605 | 0 | 0 | 0 | 0 |
| onCrack | messages_page | 2,739,840 | 0 | 0 | 0 | 0 |
| onCrack | sidebar | 2,660,948 | 0 | 0 | 0 | 0 |
| onCrack | search | 2,063,374 | 0 | 0 | 0 | 0 |
| onCrack | post_message | 382,680 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| onCrack | room_show | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | room_show | 16 | 58.0 [48.0–90.0] | 2/3 **←** | 0.99 |
| onCrack | messages_page | 1 | 30.0 [30.0–30.0] | 3/3 | 0.99 |
| onCrack | messages_page | 16 | 56.0 [30.0–90.0] | 2/3 **←** | 1.02 |
| onCrack | sidebar | 1 | 30.0 [30.0–36.0] | 3/3 | 1.00 |
| onCrack | sidebar | 16 | 34.0 [32.0–90.0] | 2/3 **←** | 0.99 |
| onCrack | search | 1 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | search | 16 | 30.0 [30.0–32.0] | 3/3 | 1.02 |
| onCrack | post_message | 1 | 30.0 [30.0–30.0] | 3/3 | 0.99 |
| onCrack | post_message | 16 | 30.0 [30.0–40.0] | 3/3 | 1.00 |

### Rows written by `post_message` (messages of the write room counted in the app's SQLite file around each run)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| onCrack | 1 | warm-up c=1 | 90,186 | 90,186 | yes |
| onCrack | 1 | run c=1 | 24,188 | 24,188 | yes |
| onCrack | 1 | warm-up c=16 | 375,869 | 375,869 | yes |
| onCrack | 1 | run c=16 | 100,585 | 100,585 | yes |
| onCrack | 1 | **all** | 590,828 | 590,828 | yes |
| onCrack | 2 | warm-up c=1 | 92,742 | 92,742 | yes |
| onCrack | 2 | run c=1 | 25,411 | 25,411 | yes |
| onCrack | 2 | warm-up c=16 | 392,009 | 392,009 | yes |
| onCrack | 2 | run c=16 | 103,635 | 103,635 | yes |
| onCrack | 2 | **all** | 613,797 | 613,797 | yes |
| onCrack | 3 | warm-up c=1 | 93,652 | 93,652 | yes |
| onCrack | 3 | run c=1 | 24,986 | 24,986 | yes |
| onCrack | 3 | warm-up c=16 | 512,264 | 512,264 | yes |
| onCrack | 3 | run c=16 | 103,875 | 103,875 | yes |
| onCrack | 3 | **all** | 734,777 | 734,777 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| room_show | 200 24,080 / 416,122 | 200 416,122 | 24,080 | – |
| messages_page | 200 15,967 / 383,844 | 200 383,844 | 15,967 | – |
| sidebar | 200 5,910 / 30,763 | 200 30,763 | 5,910 | – |
| search | 200 9,713 / 149,623 | 200 149,623 | 9,713 | – |
| post_message | – | – | 1,994 | – |
