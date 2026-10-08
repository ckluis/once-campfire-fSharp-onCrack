```
date: 2026-10-08T08:21:41-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:3fd0dd609e3ccca63edac303f0f2c0098052ecf10e090e48da4b99694d452775 2026-10-07T18:06:59.581414571-04:00 built from commit: da1e92f56d59f65de6d3225a503e49d6bc06fed6
oncrack build: MOUNTED /var/tmp/campfire-mounted-r21 over /opt/campfire (642c7ae (dirty files under src/: 6) at 2026-10-08T12:21:41Z)
repo HEAD: 642c7ae (dirty: 6 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 08:02:31), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: cable; http secs 8, concs 1 16 64, routes room_show messages_page sidebar search avatar static_css up post_message, warm-up 30s at each route and concentration, idle 10s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 207 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 379 |
| peak anon under load (MB) | 206 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

| Metric | onCrack |
|---|---|

### Action Cable fan-out (one room; chatter.js subscriptions per client)

| Metric | onCrack |
|---|---|
| 100 clients: subscribed | 100 |
| 100 clients: connect+subscribe all (s) | 0.07 |
| 100 clients: paced post→one client p50 ms | 4.67 |
| 100 clients: paced post→all clients p50 ms | 5.05 |
| 100 clients: paced post→all clients p99 ms | 9.89 |
| 100 clients: max sustained msgs/s (delivered to all) | 3,465 |
| 100 clients: deliveries/s (client×message) | 346,526 |
| 100 clients: saturated post→all p50 ms | 1.33 |
| 100 clients: saturated POST p50 ms | 1.10 |
| 500 clients: subscribed | 500 |
| 500 clients: connect+subscribe all (s) | 0.11 |
| 500 clients: paced post→one client p50 ms | 6.14 |
| 500 clients: paced post→all clients p50 ms | 8.28 |
| 500 clients: paced post→all clients p99 ms | 10.9 |
| 500 clients: max sustained msgs/s (delivered to all) | 1,014 |
| 500 clients: deliveries/s (client×message) | 506,746 |
| 500 clients: saturated post→all p50 ms | 7.16 |
| 500 clients: saturated POST p50 ms | 3.76 |
| 1000 clients: subscribed | 1,000 |
| 1000 clients: connect+subscribe all (s) | 0.20 |
| 1000 clients: paced post→one client p50 ms | 8.10 |
| 1000 clients: paced post→all clients p50 ms | 13.3 |
| 1000 clients: paced post→all clients p99 ms | 16.7 |
| 1000 clients: max sustained msgs/s (delivered to all) | 550 |
| 1000 clients: deliveries/s (client×message) | 549,567 |
| 1000 clients: saturated post→all p50 ms | 16.1 |
| 1000 clients: saturated POST p50 ms | 6.72 |

### Memory during cable fan-out, by process (MB, peak within the phase)

App process: Rails' Puma master and workers (Action Cable runs in them), or the Rust and F# ports' one campfire
process (its front server included). Pss counts pages shared between forked workers once;
RssAnon counts them in every process.

| Metric | onCrack |
|---|---|
| 100 clients, all subscribed, idle: app process Pss | 114 |
| 100 clients, all subscribed, idle: app process RssAnon | 32.8 |
| 100 clients, all subscribed, idle: app + Redis + Thruster Pss | 114 |
| 100 clients, all subscribed, idle: whole container Pss | 114 |
| 100 clients, saturated fan-out: app process Pss | 267 |
| 100 clients, saturated fan-out: app process RssAnon | 180 |
| 100 clients, saturated fan-out: app + Redis + Thruster Pss | 267 |
| 100 clients, saturated fan-out: whole container Pss | 267 |
| 500 clients, all subscribed, idle: app process Pss | 269 |
| 500 clients, all subscribed, idle: app process RssAnon | 181 |
| 500 clients, all subscribed, idle: app + Redis + Thruster Pss | 269 |
| 500 clients, all subscribed, idle: whole container Pss | 269 |
| 500 clients, saturated fan-out: app process Pss | 284 |
| 500 clients, saturated fan-out: app process RssAnon | 196 |
| 500 clients, saturated fan-out: app + Redis + Thruster Pss | 284 |
| 500 clients, saturated fan-out: whole container Pss | 284 |
| 1000 clients, all subscribed, idle: app process Pss | 277 |
| 1000 clients, all subscribed, idle: app process RssAnon | 189 |
| 1000 clients, all subscribed, idle: app + Redis + Thruster Pss | 277 |
| 1000 clients, all subscribed, idle: whole container Pss | 277 |
| 1000 clients, saturated fan-out: app process Pss | 295 |
| 1000 clients, saturated fan-out: app process RssAnon | 207 |
| 1000 clients, saturated fan-out: app + Redis + Thruster Pss | 295 |
| 1000 clients, saturated fan-out: whole container Pss | 295 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.28 1.00 0.98 | 4.16 1.93 1.31 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.06 | 1.08 | 0/0 | nan |

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
