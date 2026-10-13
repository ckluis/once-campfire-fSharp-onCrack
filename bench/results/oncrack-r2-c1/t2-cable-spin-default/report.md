```
date: 2026-10-08T17:23:48-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:390e390e43faa666e99cfbc3a6bcc161d9a1c3709c952c908f48f7a979638129 2026-10-08T15:17:46.141811435-04:00 built from commit: 09415ba6bddbaa5b9d4904edf426c9b1ecee4ca8
oncrack build: MOUNTED /var/tmp/campfire-mounted over /opt/campfire (e29ee2b (dirty files under src/: 1) at 2026-10-08T20:32:42Z)
repo HEAD: e29ee2b (dirty: 1 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 11:27:25), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: cable; http secs 8, concs 1 16 64, routes up, warm-up 30s at each route and concentration, idle 10s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 215 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 444 |
| peak anon under load (MB) | 218 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

| Metric | onCrack |
|---|---|

### Action Cable fan-out (one room; chatter.js subscriptions per client)

| Metric | onCrack |
|---|---|
| 100 clients: subscribed | 100 |
| 100 clients: connect+subscribe all (s) | 0.07 |
| 100 clients: paced post→one client p50 ms | 4.63 |
| 100 clients: paced post→all clients p50 ms | 5.11 |
| 100 clients: paced post→all clients p99 ms | 21.3 |
| 100 clients: max sustained msgs/s (delivered to all) | 5,123 |
| 100 clients: deliveries/s (client×message) | 512,275 |
| 100 clients: saturated post→all p50 ms | 1.39 |
| 100 clients: saturated POST p50 ms | 0.71 |
| 500 clients: subscribed | 500 |
| 500 clients: connect+subscribe all (s) | 0.12 |
| 500 clients: paced post→one client p50 ms | 5.03 |
| 500 clients: paced post→all clients p50 ms | 7.00 |
| 500 clients: paced post→all clients p99 ms | 9.82 |
| 500 clients: max sustained msgs/s (delivered to all) | 1,530 |
| 500 clients: deliveries/s (client×message) | 765,200 |
| 500 clients: saturated post→all p50 ms | 7.58 |
| 500 clients: saturated POST p50 ms | 2.35 |
| 1000 clients: subscribed | 1,000 |
| 1000 clients: connect+subscribe all (s) | 0.12 |
| 1000 clients: paced post→one client p50 ms | 7.06 |
| 1000 clients: paced post→all clients p50 ms | 10.4 |
| 1000 clients: paced post→all clients p99 ms | 15.5 |
| 1000 clients: max sustained msgs/s (delivered to all) | 822 |
| 1000 clients: deliveries/s (client×message) | 821,466 |
| 1000 clients: saturated post→all p50 ms | 17.8 |
| 1000 clients: saturated POST p50 ms | 4.24 |

### Memory during cable fan-out, by process (MB, peak within the phase)

App process: Rails' Puma master and workers (Action Cable runs in them), or the Rust and F# ports' one campfire
process (its front server included). Pss counts pages shared between forked workers once;
RssAnon counts them in every process.

| Metric | onCrack |
|---|---|
| 100 clients, all subscribed, idle: app process Pss | 113 |
| 100 clients, all subscribed, idle: app process RssAnon | 33.1 |
| 100 clients, all subscribed, idle: app + Redis + Thruster Pss | 113 |
| 100 clients, all subscribed, idle: whole container Pss | 113 |
| 100 clients, saturated fan-out: app process Pss | 271 |
| 100 clients, saturated fan-out: app process RssAnon | 185 |
| 100 clients, saturated fan-out: app + Redis + Thruster Pss | 271 |
| 100 clients, saturated fan-out: whole container Pss | 271 |
| 500 clients, all subscribed, idle: app process Pss | 269 |
| 500 clients, all subscribed, idle: app process RssAnon | 182 |
| 500 clients, all subscribed, idle: app + Redis + Thruster Pss | 269 |
| 500 clients, all subscribed, idle: whole container Pss | 269 |
| 500 clients, saturated fan-out: app process Pss | 285 |
| 500 clients, saturated fan-out: app process RssAnon | 198 |
| 500 clients, saturated fan-out: app + Redis + Thruster Pss | 285 |
| 500 clients, saturated fan-out: whole container Pss | 285 |
| 1000 clients, all subscribed, idle: app process Pss | 286 |
| 1000 clients, all subscribed, idle: app process RssAnon | 198 |
| 1000 clients, all subscribed, idle: app + Redis + Thruster Pss | 286 |
| 1000 clients, all subscribed, idle: whole container Pss | 286 |
| 1000 clients, saturated fan-out: app process Pss | 307 |
| 1000 clients, saturated fan-out: app process RssAnon | 219 |
| 1000 clients, saturated fan-out: app + Redis + Thruster Pss | 307 |
| 1000 clients, saturated fan-out: whole container Pss | 307 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.33 2.09 2.34 | 3.75 2.63 2.50 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.04 | 1.07 | 0/0 | nan |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | onCrack gzip wire / decoded | onCrack identity | onCrack c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | – | – |
