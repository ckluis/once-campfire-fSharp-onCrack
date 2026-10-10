```
date: 2026-10-10T03:02:09-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: CAMPFIRE_CABLE_GATHER=off
user agent: (none)
oncrack image: campfire-oncrack:app sha256:69deaa8cdf6089b47d27a5751547c4215224b8f4a7a22932339cde2879ba6ede 2026-10-09T15:26:31.696372684-04:00 built from commit: 191c468cf72ad09acee911208dec5eec811020dc
oncrack build: MOUNTED /var/tmp/campfire-mounted over /opt/campfire (2bc263f (dirty files under src/: 4) at 2026-10-10T06:57:55Z)
repo HEAD: 2bc263f (dirty: 4 files under src/ and rust/)
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
| peak memory.current under load (MB) | 411 |
| peak anon under load (MB) | 262 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

| Metric | onCrack |
|---|---|

### Action Cable fan-out (one room; chatter.js subscriptions per client)

| Metric | onCrack |
|---|---|
| 1000 clients: subscribed | 1,000 |
| 1000 clients: connect+subscribe all (s) | 0.21 |
| 1000 clients: paced post→one client p50 ms | 8.05 |
| 1000 clients: paced post→all clients p50 ms | 11.2 |
| 1000 clients: paced post→all clients p99 ms | 25.5 |
| 1000 clients: max sustained msgs/s (delivered to all) | 1,807 |
| 1000 clients: deliveries/s (client×message) | 1,807,326 |
| 1000 clients: saturated post→all p50 ms | 37.7 |
| 1000 clients: saturated POST p50 ms | 1.11 |
| 2000 clients: subscribed | 2,000 |
| 2000 clients: connect+subscribe all (s) | 0.26 |
| 2000 clients: paced post→one client p50 ms | 9.78 |
| 2000 clients: paced post→all clients p50 ms | 14.8 |
| 2000 clients: paced post→all clients p99 ms | 19.2 |
| 2000 clients: max sustained msgs/s (delivered to all) | 911 |
| 2000 clients: deliveries/s (client×message) | 1,822,693 |
| 2000 clients: saturated post→all p50 ms | 101 |
| 2000 clients: saturated POST p50 ms | 1.68 |

### Memory during cable fan-out, by process (MB, peak within the phase)

App process: Rails' Puma master and workers (Action Cable runs in them), or the Rust and F# ports' one campfire
process (its front server included). Pss counts pages shared between forked workers once;
RssAnon counts them in every process.

| Metric | onCrack |
|---|---|
| 1000 clients, all subscribed, idle: app process Pss | 178 |
| 1000 clients, all subscribed, idle: app process RssAnon | 96.8 |
| 1000 clients, all subscribed, idle: app + Redis + Thruster Pss | 178 |
| 1000 clients, all subscribed, idle: whole container Pss | 178 |
| 1000 clients, saturated fan-out: app process Pss | 299 |
| 1000 clients, saturated fan-out: app process RssAnon | 212 |
| 1000 clients, saturated fan-out: app + Redis + Thruster Pss | 299 |
| 1000 clients, saturated fan-out: whole container Pss | 299 |
| 2000 clients, all subscribed, idle: app process Pss | 293 |
| 2000 clients, all subscribed, idle: app process RssAnon | 205 |
| 2000 clients, all subscribed, idle: app + Redis + Thruster Pss | 293 |
| 2000 clients, all subscribed, idle: whole container Pss | 293 |
| 2000 clients, saturated fan-out: app process Pss | 351 |
| 2000 clients, saturated fan-out: app process RssAnon | 262 |
| 2000 clients, saturated fan-out: app + Redis + Thruster Pss | 351 |
| 2000 clients, saturated fan-out: whole container Pss | 351 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.36 1.18 0.87 | 3.88 1.87 1.12 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.06 | 1.06 | 0/0 | nan |

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
