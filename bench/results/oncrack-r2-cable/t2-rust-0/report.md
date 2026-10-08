```
date: 2026-10-08T08:04:20-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
rust image: campfire-rust:app sha256:d582a01d3a4ae9c5fd4bc9cd7b0262e1a5d4440cc0058d200b50ad9b27e1365c 2026-10-05T23:48:02.375329666-04:00 built from commit: 
repo HEAD: 642c7ae (dirty: 0 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 08:02:31), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps rust, reps 1; suites: cable; http secs 8, concs 1 16 64, routes room_show messages_page sidebar search avatar static_css up post_message, warm-up 30s at each route and concentration, idle 10s
log retention: 2 x 10m (json-file)
```

Reps: rust 1. Cells: median [min–max].

### Startup and memory

| Metric | Rust |
|---|---|
| cold start: docker run → /up 200 (ms) | 122 |
| idle memory.current (MB) | 41.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 268 |
| peak anon under load (MB) | 91.0 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

| Metric | Rust |
|---|---|

### Action Cable fan-out (one room; chatter.js subscriptions per client)

| Metric | Rust |
|---|---|
| 100 clients: subscribed | 100 |
| 100 clients: connect+subscribe all (s) | 0.08 |
| 100 clients: paced post→one client p50 ms | 3.21 |
| 100 clients: paced post→all clients p50 ms | 3.78 |
| 100 clients: paced post→all clients p99 ms | 5.58 |
| 100 clients: max sustained msgs/s (delivered to all) | 3,306 |
| 100 clients: deliveries/s (client×message) | 330,597 |
| 100 clients: saturated post→all p50 ms | 1.44 |
| 100 clients: saturated POST p50 ms | 1.15 |
| 500 clients: subscribed | 500 |
| 500 clients: connect+subscribe all (s) | 0.11 |
| 500 clients: paced post→one client p50 ms | 5.17 |
| 500 clients: paced post→all clients p50 ms | 8.02 |
| 500 clients: paced post→all clients p99 ms | 10.9 |
| 500 clients: max sustained msgs/s (delivered to all) | 1,051 |
| 500 clients: deliveries/s (client×message) | 525,338 |
| 500 clients: saturated post→all p50 ms | 8.83 |
| 500 clients: saturated POST p50 ms | 3.56 |
| 1000 clients: subscribed | 1,000 |
| 1000 clients: connect+subscribe all (s) | 0.14 |
| 1000 clients: paced post→one client p50 ms | 8.01 |
| 1000 clients: paced post→all clients p50 ms | 13.2 |
| 1000 clients: paced post→all clients p99 ms | 18.9 |
| 1000 clients: max sustained msgs/s (delivered to all) | 588 |
| 1000 clients: deliveries/s (client×message) | 588,248 |
| 1000 clients: saturated post→all p50 ms | 20.2 |
| 1000 clients: saturated POST p50 ms | 6.10 |

### Memory during cable fan-out, by process (MB, peak within the phase)

App process: Rails' Puma master and workers (Action Cable runs in them), or the Rust and F# ports' one campfire
process (its front server included). Pss counts pages shared between forked workers once;
RssAnon counts them in every process.

| Metric | Rust |
|---|---|
| 100 clients, all subscribed, idle: app process Pss | 37.9 |
| 100 clients, all subscribed, idle: app process RssAnon | 19.7 |
| 100 clients, all subscribed, idle: app + Redis + Thruster Pss | 37.9 |
| 100 clients, all subscribed, idle: whole container Pss | 37.9 |
| 100 clients, saturated fan-out: app process Pss | 96.6 |
| 100 clients, saturated fan-out: app process RssAnon | 78.2 |
| 100 clients, saturated fan-out: app + Redis + Thruster Pss | 96.6 |
| 100 clients, saturated fan-out: whole container Pss | 96.6 |
| 500 clients, all subscribed, idle: app process Pss | 102 |
| 500 clients, all subscribed, idle: app process RssAnon | 83.9 |
| 500 clients, all subscribed, idle: app + Redis + Thruster Pss | 102 |
| 500 clients, all subscribed, idle: whole container Pss | 102 |
| 500 clients, saturated fan-out: app process Pss | 103 |
| 500 clients, saturated fan-out: app process RssAnon | 84.4 |
| 500 clients, saturated fan-out: app + Redis + Thruster Pss | 103 |
| 500 clients, saturated fan-out: whole container Pss | 103 |
| 1000 clients, all subscribed, idle: app process Pss | 109 |
| 1000 clients, all subscribed, idle: app process RssAnon | 90.9 |
| 1000 clients, all subscribed, idle: app + Redis + Thruster Pss | 109 |
| 1000 clients, all subscribed, idle: whole container Pss | 109 |
| 1000 clients, saturated fan-out: app process Pss | 109 |
| 1000 clients, saturated fan-out: app process RssAnon | 90.3 |
| 1000 clients, saturated fan-out: app + Redis + Thruster Pss | 109 |
| 1000 clients, saturated fan-out: whole container Pss | 109 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| Rust | 1 | 1.31 0.97 0.39 | 4.47 2.00 0.80 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| Rust | 1 | 1.04 | 1.07 | 0/0 | nan |

### Responses by status class, every HTTP run of every rep

| App | Route | 2xx | 3xx | 4xx | 5xx | Errors (no response) |
|---|---|---|---|---|---|---|

### Rows written by `post_message` and the realistic workloads that post (messages counted in the app's SQLite file around each run: the write room's, or every room's for a realistic workload)

| App | Rep | Phase | Posts answered below 400 | Rows written | Match |
|---|---|---|---|---|---|

### Response bytes, one request per route (gzip: wire / decoded; identity: bytes) and the average over the c=16 run

The probe is a single request after sign-in, before any load. Bodies carry per-request tokens and the clock, so sizes of two apps agree to within a few bytes when they render the same page. "c=16 avg" is what the load generator received per request on the wire (gzip unless the column says otherwise).

| Route | Rust gzip wire / decoded | Rust identity | Rust c=16 avg | vs Rust |
|---|---|---|---|---|
| post_message | – | – | – | – |
