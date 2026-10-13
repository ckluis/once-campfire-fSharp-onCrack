```
date: 2026-10-12T15:59:27-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
rust image: campfire-rust-upstream:f9dca47 sha256:b0e047159ee217631110f99c318fcb5c40ace80aa5f9803325b6bd06589454ef 2026-10-10T17:27:34.587605813-04:00 built from commit: 
repo HEAD: b65d116 (dirty: 5 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-10 23:47:11), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POST_RATE 0, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps rust, reps 1; suites: cable; http secs 8, concs 1 16 64, routes up, warm-up 30s at each route and concentration, idle 10s
log retention: 2 x 10m (json-file)
```

Reps: rust 1. Cells: median [min–max].

### Startup and memory

| Metric | Rust |
|---|---|
| cold start: docker run → /up 200 (ms) | 232 |
| idle memory.current (MB) | 40.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 310 |
| peak anon under load (MB) | 114 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

| Metric | Rust |
|---|---|

### Action Cable fan-out (one room; chatter.js subscriptions per client)

| Metric | Rust |
|---|---|
| 1000 clients: subscribed | 1,000 |
| 1000 clients: connect+subscribe all (s) | 0.15 |
| 1000 clients: paced post→one client p50 ms | 3.14 |
| 1000 clients: paced post→all clients p50 ms | 4.82 |
| 1000 clients: paced post→all clients p99 ms | 17.9 |
| 1000 clients: max sustained msgs/s (delivered to all) | 1,288 |
| 1000 clients: deliveries/s (client×message) | 1,287,558 |
| 1000 clients: saturated post→all p50 ms | 26.1 |
| 1000 clients: saturated POST p50 ms | 1.96 |
| 2000 clients: subscribed | 2,000 |
| 2000 clients: connect+subscribe all (s) | 0.15 |
| 2000 clients: paced post→one client p50 ms | 4.89 |
| 2000 clients: paced post→all clients p50 ms | 8.66 |
| 2000 clients: paced post→all clients p99 ms | 22.9 |
| 2000 clients: max sustained msgs/s (delivered to all) | 723 |
| 2000 clients: deliveries/s (client×message) | 1,446,688 |
| 2000 clients: saturated post→all p50 ms | 125 |
| 2000 clients: saturated POST p50 ms | 2.67 |

### Memory during cable fan-out, by process (MB, peak within the phase)

App process: Rails' Puma master and workers (Action Cable runs in them), or the Rust and F# ports' one campfire
process (its front server included). Pss counts pages shared between forked workers once;
RssAnon counts them in every process.

| Metric | Rust |
|---|---|
| 1000 clients, all subscribed, idle: app process Pss | 55.2 |
| 1000 clients, all subscribed, idle: app process RssAnon | 37.0 |
| 1000 clients, all subscribed, idle: app + Redis + Thruster Pss | 55.2 |
| 1000 clients, all subscribed, idle: whole container Pss | 55.2 |
| 1000 clients, saturated fan-out: app process Pss | 112 |
| 1000 clients, saturated fan-out: app process RssAnon | 93.6 |
| 1000 clients, saturated fan-out: app + Redis + Thruster Pss | 112 |
| 1000 clients, saturated fan-out: whole container Pss | 112 |
| 2000 clients, all subscribed, idle: app process Pss | 124 |
| 2000 clients, all subscribed, idle: app process RssAnon | 105 |
| 2000 clients, all subscribed, idle: app + Redis + Thruster Pss | 124 |
| 2000 clients, all subscribed, idle: whole container Pss | 124 |
| 2000 clients, saturated fan-out: app process Pss | 133 |
| 2000 clients, saturated fan-out: app process RssAnon | 114 |
| 2000 clients, saturated fan-out: app + Redis + Thruster Pss | 133 |
| 2000 clients, saturated fan-out: whole container Pss | 133 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| Rust | 1 | 1.40 1.53 1.57 | 3.70 2.13 1.77 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| Rust | 1 | 1.10 | 1.06 | 0/0 | nan |

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
