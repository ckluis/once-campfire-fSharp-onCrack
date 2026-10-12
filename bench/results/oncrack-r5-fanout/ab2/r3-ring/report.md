```
date: 2026-10-12T14:28:18-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: CAMPFIRE_CABLE_LOG=ring
user agent: (none)
oncrack image: campfire-oncrack:app sha256:ecfb867a2f579135edd81d2ee703eb49b3491da8fb73e6981e3acea24909a61b 2026-10-10T16:33:47.023147364-04:00 built from commit: ea1f85b4b66e9f2f6756bdd428772e5aed29703f
oncrack build: MOUNTED /var/tmp/campfire-r52c over /opt/campfire (db83b63 (dirty files under src/: 0) at 2026-10-12T16:41:40Z)
repo HEAD: b65d116 (dirty: 3 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-10 23:47:11), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: cable; http secs 8, concs 1 16 64, routes up, warm-up 30s at each route and concentration, idle 10s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 222 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 402 |
| peak anon under load (MB) | 235 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

| Metric | onCrack |
|---|---|

### Action Cable fan-out (one room; chatter.js subscriptions per client)

| Metric | onCrack |
|---|---|
| 1000 clients: subscribed | 1,000 |
| 1000 clients: connect+subscribe all (s) | 0.21 |
| 1000 clients: paced post→one client p50 ms | 4.49 |
| 1000 clients: paced post→all clients p50 ms | 5.67 |
| 1000 clients: paced post→all clients p99 ms | 17.0 |
| 1000 clients: max sustained msgs/s (delivered to all) | 1,593 |
| 1000 clients: deliveries/s (client×message) | 1,592,664 |
| 1000 clients: saturated post→all p50 ms | 27.5 |
| 1000 clients: saturated POST p50 ms | 1.72 |
| 2000 clients: subscribed | 2,000 |
| 2000 clients: connect+subscribe all (s) | 0.31 |
| 2000 clients: paced post→one client p50 ms | 5.12 |
| 2000 clients: paced post→all clients p50 ms | 7.44 |
| 2000 clients: paced post→all clients p99 ms | 15.6 |
| 2000 clients: max sustained msgs/s (delivered to all) | 474 |
| 2000 clients: deliveries/s (client×message) | 947,469 |
| 2000 clients: saturated post→all p50 ms | 86.0 |
| 2000 clients: saturated POST p50 ms | 4.18 |

### Memory during cable fan-out, by process (MB, peak within the phase)

App process: Rails' Puma master and workers (Action Cable runs in them), or the Rust and F# ports' one campfire
process (its front server included). Pss counts pages shared between forked workers once;
RssAnon counts them in every process.

| Metric | onCrack |
|---|---|
| 1000 clients, all subscribed, idle: app process Pss | 178 |
| 1000 clients, all subscribed, idle: app process RssAnon | 95.7 |
| 1000 clients, all subscribed, idle: app + Redis + Thruster Pss | 178 |
| 1000 clients, all subscribed, idle: whole container Pss | 178 |
| 1000 clients, saturated fan-out: app process Pss | 294 |
| 1000 clients, saturated fan-out: app process RssAnon | 206 |
| 1000 clients, saturated fan-out: app + Redis + Thruster Pss | 294 |
| 1000 clients, saturated fan-out: whole container Pss | 294 |
| 2000 clients, all subscribed, idle: app process Pss | 304 |
| 2000 clients, all subscribed, idle: app process RssAnon | 215 |
| 2000 clients, all subscribed, idle: app + Redis + Thruster Pss | 304 |
| 2000 clients, all subscribed, idle: whole container Pss | 304 |
| 2000 clients, saturated fan-out: app process Pss | 324 |
| 2000 clients, saturated fan-out: app process RssAnon | 234 |
| 2000 clients, saturated fan-out: app + Redis + Thruster Pss | 324 |
| 2000 clients, saturated fan-out: whole container Pss | 324 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.45 2.14 2.17 | 3.28 2.49 2.28 |

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
