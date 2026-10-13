```
date: 2026-10-10T06:32:25-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: CAMPFIRE_CABLE_GATHER=off
user agent: (none)
oncrack image: campfire-oncrack:app sha256:22063e6d63ab2578c96e790bb709a3f616b1fe327d2916bf6b6098cec90f48c4 2026-10-10T05:34:09.102704331-04:00 built from commit: 2352dfa15b64dc493646dd77d5980d8181a0af10
repo HEAD: 2352dfa (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-10 02:25:45), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: cable; http secs 8, concs 1 16 64, routes up, warm-up 30s at each route and concentration, idle 10s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 201 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 442 |
| peak anon under load (MB) | 241 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

| Metric | onCrack |
|---|---|

### Action Cable fan-out (one room; chatter.js subscriptions per client)

| Metric | onCrack |
|---|---|
| 100 clients: subscribed | 100 |
| 100 clients: connect+subscribe all (s) | 0.05 |
| 100 clients: paced post→one client p50 ms | 4.38 |
| 100 clients: paced post→all clients p50 ms | 4.64 |
| 100 clients: paced post→all clients p99 ms | 16.9 |
| 100 clients: max sustained msgs/s (delivered to all) | 3,561 |
| 100 clients: deliveries/s (client×message) | 356,143 |
| 100 clients: saturated post→all p50 ms | 1.72 |
| 100 clients: saturated POST p50 ms | 0.86 |
| 500 clients: subscribed | 500 |
| 500 clients: connect+subscribe all (s) | 0.10 |
| 500 clients: paced post→one client p50 ms | 5.09 |
| 500 clients: paced post→all clients p50 ms | 7.00 |
| 500 clients: paced post→all clients p99 ms | 9.99 |
| 500 clients: max sustained msgs/s (delivered to all) | 1,154 |
| 500 clients: deliveries/s (client×message) | 576,786 |
| 500 clients: saturated post→all p50 ms | 16.3 |
| 500 clients: saturated POST p50 ms | 2.67 |
| 1000 clients: subscribed | 1,000 |
| 1000 clients: connect+subscribe all (s) | 0.10 |
| 1000 clients: paced post→one client p50 ms | 6.66 |
| 1000 clients: paced post→all clients p50 ms | 9.64 |
| 1000 clients: paced post→all clients p99 ms | 13.4 |
| 1000 clients: max sustained msgs/s (delivered to all) | 731 |
| 1000 clients: deliveries/s (client×message) | 731,026 |
| 1000 clients: saturated post→all p50 ms | 51.0 |
| 1000 clients: saturated POST p50 ms | 4.03 |
| 2000 clients: subscribed | 2,000 |
| 2000 clients: connect+subscribe all (s) | 0.21 |
| 2000 clients: paced post→one client p50 ms | 8.94 |
| 2000 clients: paced post→all clients p50 ms | 13.4 |
| 2000 clients: paced post→all clients p99 ms | 62.1 |
| 2000 clients: max sustained msgs/s (delivered to all) | 408 |
| 2000 clients: deliveries/s (client×message) | 815,841 |
| 2000 clients: saturated post→all p50 ms | 163 |
| 2000 clients: saturated POST p50 ms | 5.33 |

### Memory during cable fan-out, by process (MB, peak within the phase)

App process: Rails' Puma master and workers (Action Cable runs in them), or the Rust and F# ports' one campfire
process (its front server included). Pss counts pages shared between forked workers once;
RssAnon counts them in every process.

| Metric | onCrack |
|---|---|
| 100 clients, all subscribed, idle: app process Pss | 114 |
| 100 clients, all subscribed, idle: app process RssAnon | 32.9 |
| 100 clients, all subscribed, idle: app + Redis + Thruster Pss | 114 |
| 100 clients, all subscribed, idle: whole container Pss | 114 |
| 100 clients, saturated fan-out: app process Pss | 265 |
| 100 clients, saturated fan-out: app process RssAnon | 177 |
| 100 clients, saturated fan-out: app + Redis + Thruster Pss | 265 |
| 100 clients, saturated fan-out: whole container Pss | 265 |
| 500 clients, all subscribed, idle: app process Pss | 266 |
| 500 clients, all subscribed, idle: app process RssAnon | 177 |
| 500 clients, all subscribed, idle: app + Redis + Thruster Pss | 266 |
| 500 clients, all subscribed, idle: whole container Pss | 266 |
| 500 clients, saturated fan-out: app process Pss | 278 |
| 500 clients, saturated fan-out: app process RssAnon | 189 |
| 500 clients, saturated fan-out: app + Redis + Thruster Pss | 278 |
| 500 clients, saturated fan-out: whole container Pss | 278 |
| 1000 clients, all subscribed, idle: app process Pss | 277 |
| 1000 clients, all subscribed, idle: app process RssAnon | 188 |
| 1000 clients, all subscribed, idle: app + Redis + Thruster Pss | 277 |
| 1000 clients, all subscribed, idle: whole container Pss | 277 |
| 1000 clients, saturated fan-out: app process Pss | 290 |
| 1000 clients, saturated fan-out: app process RssAnon | 200 |
| 1000 clients, saturated fan-out: app + Redis + Thruster Pss | 290 |
| 1000 clients, saturated fan-out: whole container Pss | 290 |
| 2000 clients, all subscribed, idle: app process Pss | 302 |
| 2000 clients, all subscribed, idle: app process RssAnon | 212 |
| 2000 clients, all subscribed, idle: app + Redis + Thruster Pss | 302 |
| 2000 clients, all subscribed, idle: whole container Pss | 302 |
| 2000 clients, saturated fan-out: app process Pss | 332 |
| 2000 clients, saturated fan-out: app process RssAnon | 242 |
| 2000 clients, saturated fan-out: app + Redis + Thruster Pss | 332 |
| 2000 clients, saturated fan-out: whole container Pss | 332 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.44 1.79 2.15 | 4.27 2.49 2.36 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.07 | 1.12 | 0/0 | nan |

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
