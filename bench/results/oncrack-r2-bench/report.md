```
date: 2026-10-08T06:16:16-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
reference image: campfire-reference:app sha256:d2ca3b5d7a7f79e78164fb73024811dfaae06d416458c10379c1e9fff12fd00d 2026-10-05T12:04:17.590477719-04:00 built from commit: 
rust image: campfire-rust:app sha256:d582a01d3a4ae9c5fd4bc9cd7b0262e1a5d4440cc0058d200b50ad9b27e1365c 2026-10-05T23:48:02.375329666-04:00 built from commit: 
fsharp image: campfire-fsharp:app sha256:421f335c3ff8ee640991228ffe18bb750f2a37a4bd5ad9da64e0a0da5cb1ae0c 2026-10-07T04:18:34.342866793-04:00 built from commit: 2e6c08e242191cb9c982ecc0f2c06e56d2e9855e
oncrack image: campfire-oncrack:app sha256:3fd0dd609e3ccca63edac303f0f2c0098052ecf10e090e48da4b99694d452775 2026-10-07T18:06:59.581414571-04:00 built from commit: da1e92f56d59f65de6d3225a503e49d6bc06fed6
repo HEAD: 2ed2e5e (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 06:11:29), built with rust:1.98.1-trixie
seed: crowd (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps reference,rust,fsharp,oncrack, reps 3; suites: http; http secs 8, concs 1 16, routes mixed spread spread_mixed search_spread, warm-up 30s at each route and concentration, idle 5s
log retention: 2 x 10m (json-file)
```

Reps: reference 1, rust 3, fsharp 3, oncrack 3. Cells: median [min–max].

### Startup and memory

| Metric | Rails | Rust | F# | onCrack | Rust adv. | F# adv. | onCrack adv. | onCrack / F# |
|---|---|---|---|---|---|---|---|---|
| cold start: docker run → /up 200 (ms) | 2,346 | 111 [106–130] | 237 [232–256] | 242 [226–252] | 21.1× | 0.47× | 0.46× | 0.98× |
| idle memory.current (MB) | 322 | 16.0 [16.0–16.0] | 28.0 [27.0–28.0] | 28.0 [28.0–28.0] | 20.1× | 0.57× | 0.57× | 1.00× |
| idle anon (MB) | 293 | 15.0 [15.0–15.0] | 15.0 [15.0–15.0] | 15.0 [15.0–15.0] | 19.5× | 1.00× | 1.00× | 1.00× |
| peak memory.current under load (MB) | 1,090 | 291 [290–296] | 495 [472–498] | 691 [599–699] | 3.7× | 0.59× | 0.42× | 0.72× |
| peak anon under load (MB) | 1,049 | 220 [218–220] | 409 [397–417] | 602 [511–609] | 4.8× | 0.54× | 0.37× | 0.68× |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

`CPU µs/req` is the container's CPU (cgroup cpu.stat, user + system, unprofiled) over the run divided by its requests; for CPU a ratio below 1 means the first app spends more per request.

| Metric | Rails | Rust | F# | onCrack | Rust adv. | F# adv. | onCrack adv. | onCrack / F# |
|---|---|---|---|---|---|---|---|---|
| mixed c=16 req/s (all lanes) | 249 | 19,285 [19,100–19,314] | 24,984 [24,780–25,174] | 44,363 [41,829–44,516] | 77.4× | 1.30× | 2.30× | 1.78× |
| mixed c=16 CPU µs/req (all lanes) | 11,664 | 176 [176–177] | 149 [148–150] | 84.3 [84.2–87.9] | 66.3× | 1.18× | 2.09× | 1.77× |
| mixed c=16 posts req/s | 30.5 | 688 [682–690] | 753 [752–754] | 1,079 [1,069–1,093] | 22.6× | 1.09× | 1.57× | 1.43× |
| mixed c=16 posts p50 ms | 21.8 | 1.41 [1.40–1.42] | 1.25 [1.24–1.25] | 0.85 [0.84–0.86] | 15.5× | 1.13× | 1.66× | 1.47× |
| mixed c=16 posts p99 ms | 90.7 | 2.50 [2.44–2.50] | 3.62 [3.54–3.70] | 2.40 [2.31–2.46] | 36.3× | 0.69× | 1.04× | 1.50× |
| mixed c=16 reads req/s | 219 | 18,597 [18,418–18,623] | 24,232 [24,027–24,420] | 43,283 [40,760–43,423] | 85.0× | 1.30× | 2.33× | 1.79× |
| mixed c=16 reads p50 ms | 71.9 | 0.84 [0.83–0.84] | 0.66 [0.65–0.67] | 0.20 [0.19–0.24] | 86.0× | 1.26× | 4.29× | 3.40× |
| mixed c=16 reads p99 ms | 143 | 1.78 [1.78–1.78] | 1.56 [1.55–1.61] | 1.11 [1.10–1.14] | 80.5× | 1.14× | 1.60× | 1.40× |
| spread c=16 req/s (all lanes) | 589 | 25,655 [25,558–25,747] | 29,902 [29,740–30,123] | 28,547 [28,524–28,808] | 43.6× | 1.17× | 1.11× | 0.95× |
| spread c=16 CPU µs/req (all lanes) | 5,102 | 143 [143–144] | 125 [124–126] | 134 [133–134] | 35.7× | 1.14× | 1.06× | 0.93× |
| spread c=16 reads req/s | 589 | 25,655 [25,558–25,747] | 29,902 [29,740–30,123] | 28,547 [28,524–28,808] | 43.6× | 1.17× | 1.11× | 0.95× |
| spread c=16 reads p50 ms | 26.0 | 0.59 [0.59–0.59] | 0.51 [0.50–0.51] | 0.53 [0.53–0.53] | 43.9× | 1.17× | 1.11× | 0.95× |
| spread c=16 reads p99 ms | 53.8 | 1.29 [1.28–1.30] | 1.11 [1.11–1.11] | 1.29 [1.24–1.30] | 41.8× | 1.16× | 1.00× | 0.86× |
| spread_mixed c=16 req/s (all lanes) | 271 | 13,473 [13,250–13,713] | 13,980 [13,966–13,997] | 13,567 [13,384–13,590] | 49.7× | 1.04× | 1.01× | 0.97× |
| spread_mixed c=16 CPU µs/req (all lanes) | 10,740 | 268 [264–272] | 274 [274–275] | 284 [284–287] | 40.1× | 0.98× | 0.94× | 0.96× |
| spread_mixed c=16 posts req/s | 5.80 | 319 [318–329] | 393 [392–396] | 337 [331–338] | 55.0× | 1.23× | 1.06× | 0.86× |
| spread_mixed c=16 posts p50 ms | 185 | 2.94 [2.88–2.97] | 2.29 [2.28–2.29] | 2.67 [2.65–2.71] | 63.0× | 1.28× | 1.10× | 0.86× |
| spread_mixed c=16 posts p99 ms | 249 | 6.43 [6.39–6.68] | 6.34 [6.23–6.59] | 7.38 [7.04–7.76] | 38.8× | 1.01× | 0.87× | 0.86× |
| spread_mixed c=16 reads req/s | 265 | 13,155 [12,931–13,384] | 13,584 [13,573–13,605] | 13,229 [13,054–13,253] | 49.6× | 1.03× | 1.01× | 0.97× |
| spread_mixed c=16 reads p50 ms | 66.6 | 1.14 [1.12–1.16] | 1.08 [1.08–1.08] | 1.11 [1.11–1.12] | 58.5× | 1.05× | 1.03× | 0.98× |
| spread_mixed c=16 reads p99 ms | 125 | 2.78 [2.65–2.81] | 2.94 [2.90–2.98] | 3.15 [3.10–3.21] | 45.0× | 0.95× | 0.88× | 0.93× |
| search_spread c=16 req/s (all lanes) | 826 | 8,468 [8,358–8,989] | 18,942 [18,868–19,076] | 17,802 [17,388–17,808] | 10.2× | 2.24× | 2.10× | 0.94× |
| search_spread c=16 CPU µs/req (all lanes) | 3,548 | 415 [393–420] | 186 [185–187] | 204 [204–205] | 8.5× | 2.23× | 2.04× | 0.91× |
| search_spread c=16 reads req/s | 826 | 8,468 [8,358–8,989] | 18,942 [18,868–19,076] | 17,802 [17,388–17,808] | 10.2× | 2.24× | 2.10× | 0.94× |
| search_spread c=16 reads p50 ms | 18.3 | 1.07 [1.01–1.11] | 0.63 [0.63–0.64] | 0.69 [0.69–0.70] | 17.1× | 1.69× | 1.55× | 0.92× |
| search_spread c=16 reads p99 ms | 39.9 | 19.2 [15.3–25.6] | 4.99 [4.70–5.28] | 5.39 [5.36–5.56] | 2.1× | 3.86× | 3.57× | 0.93× |

Realistic workloads (bench/lib/realistic.py), seed `crowd`; lanes, their connections (c is the measured concurrency) and targets:

| Workload | Lane | Connections | Pick | Targets | Users |
|---|---|---|---|---|---|
| mixed | reads | c | cycle | 1 | 1 |
| mixed | posts | 1 | cycle | 1 | 1 |
| spread | reads | c | random | 2,112 | 525 |
| spread_mixed | reads | c | random | 2,112 | 525 |
| spread_mixed | posts | 1 | random | 108 | 31 |
| search_spread | reads | c | random | 104,800 | 524 |

Sign-in of the seed's people before the workloads, per rep: Rails 25.6 s, Rust 24.7 s, Rust 24.7 s, Rust 24.7 s, F# 31.3 s, F# 31.2 s, F# 31.2 s, onCrack 31.2 s, onCrack 31.2 s, onCrack 31.3 s.

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| Rails | 1 | 0.39 0.61 0.28 | 3.69 2.96 1.66 |
| Rust | 1 | 1.35 2.41 1.56 | 6.11 4.33 2.56 |
| Rust | 2 | 1.32 3.02 3.18 | 4.54 4.38 3.75 |
| Rust | 3 | 1.30 3.41 3.46 | 5.52 4.88 4.10 |
| F# | 1 | 1.35 3.18 2.32 | 5.75 4.26 2.90 |
| F# | 2 | 1.40 3.09 3.14 | 5.39 4.03 3.49 |
| F# | 3 | 1.33 3.67 3.74 | 5.85 4.47 4.02 |
| onCrack | 1 | 1.39 3.20 2.64 | 5.81 4.33 3.19 |
| onCrack | 2 | 1.45 2.98 3.02 | 4.95 4.01 3.42 |
| onCrack | 3 | 1.32 3.32 3.65 | 5.61 4.19 3.91 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| Rails | 1 | 1.03 | 1.06 | 1/4 **noisy** | 1.10 |
| Rust | 1 | 1.05 | 1.06 | 0/4 | 1.10 |
| Rust | 2 | 1.06 | 1.07 | 0/4 | 1.07 |
| Rust | 3 | 1.08 | 1.04 | 0/4 | 1.07 |
| F# | 1 | 1.07 | 1.05 | 0/4 | 1.09 |
| F# | 2 | 1.07 | 1.05 | 0/4 | 1.09 |
| F# | 3 | 1.04 | 1.07 | 0/4 | 1.06 |
| onCrack | 1 | 1.02 | 1.04 | 0/4 | 1.09 |
| onCrack | 2 | 1.05 | 1.07 | 0/4 | 1.07 |
| onCrack | 3 | 1.06 | 1.05 | 0/4 | 1.08 |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|
| Rails | mixed | 2,009 | 0 | 0 | 0 | 0 |
| Rails | spread | 4,724 | 0 | 0 | 0 | 0 |
| Rails | spread_mixed | 2,184 | 0 | 0 | 0 | 0 |
| Rails | search_spread | 6,630 | 0 | 0 | 0 | 0 |
| Rust | mixed | 461,636 | 0 | 0 | 0 | 0 |
| Rust | spread | 615,722 | 0 | 0 | 0 | 0 |
| Rust | spread_mixed | 323,539 | 0 | 0 | 0 | 0 |
| Rust | search_spread | 207,183 | 0 | 0 | 0 | 0 |
| F# | mixed | 599,564 | 0 | 0 | 0 | 0 |
| F# | spread | 718,164 | 0 | 0 | 0 | 0 |
| F# | spread_mixed | 335,589 | 0 | 0 | 0 | 0 |
| F# | search_spread | 455,119 | 0 | 0 | 0 | 0 |
| onCrack | mixed | 1,045,761 | 0 | 0 | 0 | 0 |
| onCrack | spread | 687,078 | 0 | 0 | 0 | 0 |
| onCrack | spread_mixed | 324,375 | 0 | 0 | 0 | 0 |
| onCrack | search_spread | 424,192 | 0 | 0 | 0 | 0 |

### Warm-up before each measured run (the app runs the route at the measured concurrency until its throughput is flat; bench/lib/warmup.py)

`measured / warm-up tail` is the measured run's requests a second over the mean of the last three 2 s warm-up windows: well above 1 would mean the app was still speeding up when measurement began, well below 1 that it was slowing down.

| App | Route | c | warm-up seconds | settled | measured / warm-up tail |
|---|---|---|---|---|---|
| Rails | mixed | 16 | 30.8 | 1/1 | 1.02 |
| Rails | spread | 16 | 30.4 | 1/1 | 1.01 |
| Rails | spread_mixed | 16 | 90.2 | 0/1 **←** | 1.02 |
| Rails | search_spread | 16 | 30.2 | 1/1 | 1.00 |
| Rust | mixed | 16 | 90.0 [90.0–90.0] | 0/3 **←** | 1.00 |
| Rust | spread | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| Rust | spread_mixed | 16 | 30.0 [30.0–32.0] | 3/3 | 0.99 |
| Rust | search_spread | 16 | 30.2 [30.2–30.4] | 3/3 | 0.95 |
| F# | mixed | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| F# | spread | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| F# | spread_mixed | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| F# | search_spread | 16 | 30.0 [30.0–30.0] | 3/3 | 0.97 |
| onCrack | mixed | 16 | 30.0 [30.0–30.0] | 3/3 | 1.00 |
| onCrack | spread | 16 | 30.0 [30.0–30.0] | 3/3 | 1.01 |
| onCrack | spread_mixed | 16 | 30.0 [30.0–30.0] | 3/3 | 0.99 |
| onCrack | search_spread | 16 | 30.0 [30.0–30.1] | 3/3 | 0.98 |

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|
| Rails | 1 | mixed warm-up c=16 | 861 | 861 | yes |
| Rails | 1 | mixed run c=16 | 246 | 246 | yes |
| Rails | 1 | spread_mixed warm-up c=16 | 504 | 504 | yes |
| Rails | 1 | spread_mixed run c=16 | 47 | 47 | yes |
| Rails | 1 | **all** | 1,658 | 1,658 | yes |
| Rust | 1 | mixed warm-up c=16 | 62,201 | 62,201 | yes |
| Rust | 1 | mixed run c=16 | 5,503 | 5,503 | yes |
| Rust | 1 | spread_mixed warm-up c=16 | 9,620 | 9,620 | yes |
| Rust | 1 | spread_mixed run c=16 | 2,553 | 2,553 | yes |
| Rust | 1 | **all** | 79,877 | 79,877 | yes |
| Rust | 2 | mixed warm-up c=16 | 61,758 | 61,758 | yes |
| Rust | 2 | mixed run c=16 | 5,453 | 5,453 | yes |
| Rust | 2 | spread_mixed warm-up c=16 | 9,759 | 9,759 | yes |
| Rust | 2 | spread_mixed run c=16 | 2,630 | 2,630 | yes |
| Rust | 2 | **all** | 79,600 | 79,600 | yes |
| Rust | 3 | mixed warm-up c=16 | 61,949 | 61,949 | yes |
| Rust | 3 | mixed run c=16 | 5,525 | 5,525 | yes |
| Rust | 3 | spread_mixed warm-up c=16 | 10,188 | 10,188 | yes |
| Rust | 3 | spread_mixed run c=16 | 2,546 | 2,546 | yes |
| Rust | 3 | **all** | 80,208 | 80,208 | yes |
| F# | 1 | mixed warm-up c=16 | 22,139 | 22,139 | yes |
| F# | 1 | mixed run c=16 | 6,023 | 6,023 | yes |
| F# | 1 | spread_mixed warm-up c=16 | 11,784 | 11,784 | yes |
| F# | 1 | spread_mixed run c=16 | 3,164 | 3,164 | yes |
| F# | 1 | **all** | 43,110 | 43,110 | yes |
| F# | 2 | mixed warm-up c=16 | 22,162 | 22,162 | yes |
| F# | 2 | mixed run c=16 | 6,032 | 6,032 | yes |
| F# | 2 | spread_mixed warm-up c=16 | 11,808 | 11,808 | yes |
| F# | 2 | spread_mixed run c=16 | 3,148 | 3,148 | yes |
| F# | 2 | **all** | 43,150 | 43,150 | yes |
| F# | 3 | mixed warm-up c=16 | 22,390 | 22,390 | yes |
| F# | 3 | mixed run c=16 | 6,020 | 6,020 | yes |
| F# | 3 | spread_mixed warm-up c=16 | 11,777 | 11,777 | yes |
| F# | 3 | spread_mixed run c=16 | 3,136 | 3,136 | yes |
| F# | 3 | **all** | 43,323 | 43,323 | yes |
| onCrack | 1 | mixed warm-up c=16 | 31,572 | 31,572 | yes |
| onCrack | 1 | mixed run c=16 | 8,552 | 8,552 | yes |
| onCrack | 1 | spread_mixed warm-up c=16 | 9,983 | 9,983 | yes |
| onCrack | 1 | spread_mixed run c=16 | 2,646 | 2,646 | yes |
| onCrack | 1 | **all** | 52,753 | 52,753 | yes |
| onCrack | 2 | mixed warm-up c=16 | 31,762 | 31,762 | yes |
| onCrack | 2 | mixed run c=16 | 8,636 | 8,636 | yes |
| onCrack | 2 | spread_mixed warm-up c=16 | 10,189 | 10,189 | yes |
| onCrack | 2 | spread_mixed run c=16 | 2,697 | 2,697 | yes |
| onCrack | 2 | **all** | 53,284 | 53,284 | yes |
| onCrack | 3 | mixed warm-up c=16 | 31,580 | 31,580 | yes |
| onCrack | 3 | mixed run c=16 | 8,744 | 8,744 | yes |
| onCrack | 3 | spread_mixed warm-up c=16 | 10,139 | 10,139 | yes |
| onCrack | 3 | spread_mixed run c=16 | 2,704 | 2,704 | yes |
| onCrack | 3 | **all** | 53,167 | 53,167 | yes |

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | Rails gzip wire / decoded | Rust gzip wire / decoded | F# gzip wire / decoded | onCrack gzip wire / decoded | Rails identity | Rust identity | F# identity | onCrack identity | Rails c=16 avg | Rust c=16 avg | F# c=16 avg | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| post_message | – | – | – | – | – | – | – | – | – | – | – | – | –; – |
