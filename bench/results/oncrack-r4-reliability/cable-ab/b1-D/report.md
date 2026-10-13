```
date: 2026-10-10T14:59:21-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: CAMPFIRE_CABLE_PRESSURE=on
user agent: (none)
oncrack image: campfire-oncrack:app sha256:ec78594c26d163af3addc5127a329fd423d17d1ba08a7f73dc7beabd90727d5b 2026-10-10T14:20:40.222413623-04:00 built from commit: f5429fcb9c75bcc06e9a6e2c022daee938d801c5
repo HEAD: f5429fc (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-10 14:46:23), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: cable; http secs 8, concs 1 16 64, routes up, warm-up 30s at each route and concentration, idle 10s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 255 |
| idle memory.current (MB) | 29.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 494 |
| peak anon under load (MB) | 273 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

| Metric | onCrack |
|---|---|

### Action Cable fan-out (one room; chatter.js subscriptions per client)

| Metric | onCrack |
|---|---|
| 1000 clients: subscribed | 1,000 |
| 1000 clients: connect+subscribe all (s) | 0.26 |
| 1000 clients: paced post→one client p50 ms | 5.77 |
| 1000 clients: paced post→all clients p50 ms | 7.32 |
| 1000 clients: paced post→all clients p99 ms | 15.5 |
| 1000 clients: max sustained msgs/s (delivered to all) | 1,778 |
| 1000 clients: deliveries/s (client×message) | 1,777,497 |
| 1000 clients: saturated post→all p50 ms | 27.2 |
| 1000 clients: saturated POST p50 ms | 1.46 |
| 2000 clients: subscribed | 2,000 |
| 2000 clients: connect+subscribe all (s) | 0.31 |
| 2000 clients: paced post→one client p50 ms | 4.87 |
| 2000 clients: paced post→all clients p50 ms | 6.97 |
| 2000 clients: paced post→all clients p99 ms | 15.6 |
| 2000 clients: max sustained msgs/s (delivered to all) | 898 |
| 2000 clients: deliveries/s (client×message) | 1,795,516 |
| 2000 clients: saturated post→all p50 ms | 73.6 |
| 2000 clients: saturated POST p50 ms | 3.04 |

### Memory during cable fan-out, by process (MB, peak within the phase)

App process: Rails' Puma master and workers (Action Cable runs in them), or the Rust and F# ports' one campfire
process (its front server included). Pss counts pages shared between forked workers once;
RssAnon counts them in every process.

| Metric | onCrack |
|---|---|
| 1000 clients, all subscribed, idle: app process Pss | 178 |
| 1000 clients, all subscribed, idle: app process RssAnon | 96.6 |
| 1000 clients, all subscribed, idle: app + Redis + Thruster Pss | 178 |
| 1000 clients, all subscribed, idle: whole container Pss | 178 |
| 1000 clients, saturated fan-out: app process Pss | 293 |
| 1000 clients, saturated fan-out: app process RssAnon | 206 |
| 1000 clients, saturated fan-out: app + Redis + Thruster Pss | 293 |
| 1000 clients, saturated fan-out: whole container Pss | 293 |
| 2000 clients, all subscribed, idle: app process Pss | 300 |
| 2000 clients, all subscribed, idle: app process RssAnon | 212 |
| 2000 clients, all subscribed, idle: app + Redis + Thruster Pss | 300 |
| 2000 clients, all subscribed, idle: whole container Pss | 300 |
| 2000 clients, saturated fan-out: app process Pss | 362 |
| 2000 clients, saturated fan-out: app process RssAnon | 274 |
| 2000 clients, saturated fan-out: app + Redis + Thruster Pss | 362 |
| 2000 clients, saturated fan-out: whole container Pss | 362 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.45 2.29 2.75 | 3.20 2.55 2.80 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.10 | 1.08 | 0/0 | nan |

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
