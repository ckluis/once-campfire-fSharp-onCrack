```
date: 2026-10-08T08:35:08-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: 
user agent: (none)
oncrack image: campfire-oncrack:app sha256:3fd0dd609e3ccca63edac303f0f2c0098052ecf10e090e48da4b99694d452775 2026-10-07T18:06:59.581414571-04:00 built from commit: da1e92f56d59f65de6d3225a503e49d6bc06fed6
oncrack build: MOUNTED /var/tmp/campfire-mounted-r21b over /opt/campfire (642c7ae (dirty files under src/: 8) at 2026-10-08T12:35:08Z)
repo HEAD: 642c7ae (dirty: 8 files under src/ and rust/)
work dir (seed copies): /var/tmp/campfire-bench-work (ext4)
loadgen: /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/target/rust/aarch64-unknown-linux-gnu/release/loadgen (2026-10-08 08:26:55), built with rust:1.98.1-trixie
seed: default (realistic workloads: crowd; classic: default); realistic concs 16, MIX_POSTERS 1, SPREAD_POSTERS 1, POSTING_USERS 32, SEARCH_QUERIES 200, REAL_USERS 0 (0: all)
schedule: apps oncrack, reps 1; suites: cable; http secs 8, concs 1 16 64, routes room_show messages_page sidebar search avatar static_css up post_message, warm-up 30s at each route and concentration, idle 10s
log retention: 2 x 10m (json-file)
```

Reps: oncrack 1. Cells: median [min–max].

### Startup and memory

| Metric | onCrack |
|---|---|
| cold start: docker run → /up 200 (ms) | 234 |
| idle memory.current (MB) | 28.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 407 |
| peak anon under load (MB) | 218 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

| Metric | onCrack |
|---|---|

### Action Cable fan-out (one room; chatter.js subscriptions per client)

| Metric | onCrack |
|---|---|
| 100 clients: subscribed | 100 |
| 100 clients: connect+subscribe all (s) | 0.07 |
| 100 clients: paced post→one client p50 ms | 4.98 |
| 100 clients: paced post→all clients p50 ms | 5.45 |
| 100 clients: paced post→all clients p99 ms | 16.9 |
| 100 clients: max sustained msgs/s (delivered to all) | 3,823 |
| 100 clients: deliveries/s (client×message) | 382,299 |
| 100 clients: saturated post→all p50 ms | 1.18 |
| 100 clients: saturated POST p50 ms | 0.99 |
| 500 clients: subscribed | 500 |
| 500 clients: connect+subscribe all (s) | 0.12 |
| 500 clients: paced post→one client p50 ms | 5.39 |
| 500 clients: paced post→all clients p50 ms | 7.42 |
| 500 clients: paced post→all clients p99 ms | 11.5 |
| 500 clients: max sustained msgs/s (delivered to all) | 1,236 |
| 500 clients: deliveries/s (client×message) | 618,219 |
| 500 clients: saturated post→all p50 ms | 5.69 |
| 500 clients: saturated POST p50 ms | 3.12 |
| 1000 clients: subscribed | 1,000 |
| 1000 clients: connect+subscribe all (s) | 0.14 |
| 1000 clients: paced post→one client p50 ms | 8.11 |
| 1000 clients: paced post→all clients p50 ms | 12.5 |
| 1000 clients: paced post→all clients p99 ms | 15.2 |
| 1000 clients: max sustained msgs/s (delivered to all) | 685 |
| 1000 clients: deliveries/s (client×message) | 685,190 |
| 1000 clients: saturated post→all p50 ms | 12.8 |
| 1000 clients: saturated POST p50 ms | 5.51 |

### Memory during cable fan-out, by process (MB, peak within the phase)

App process: Rails' Puma master and workers (Action Cable runs in them), or the Rust and F# ports' one campfire
process (its front server included). Pss counts pages shared between forked workers once;
RssAnon counts them in every process.

| Metric | onCrack |
|---|---|
| 100 clients, all subscribed, idle: app process Pss | 113 |
| 100 clients, all subscribed, idle: app process RssAnon | 32.9 |
| 100 clients, all subscribed, idle: app + Redis + Thruster Pss | 113 |
| 100 clients, all subscribed, idle: whole container Pss | 113 |
| 100 clients, saturated fan-out: app process Pss | 269 |
| 100 clients, saturated fan-out: app process RssAnon | 182 |
| 100 clients, saturated fan-out: app + Redis + Thruster Pss | 269 |
| 100 clients, saturated fan-out: whole container Pss | 269 |
| 500 clients, all subscribed, idle: app process Pss | 265 |
| 500 clients, all subscribed, idle: app process RssAnon | 177 |
| 500 clients, all subscribed, idle: app + Redis + Thruster Pss | 265 |
| 500 clients, all subscribed, idle: whole container Pss | 265 |
| 500 clients, saturated fan-out: app process Pss | 290 |
| 500 clients, saturated fan-out: app process RssAnon | 202 |
| 500 clients, saturated fan-out: app + Redis + Thruster Pss | 290 |
| 500 clients, saturated fan-out: whole container Pss | 290 |
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
| onCrack | 1 | 1.28 1.81 1.69 | 3.95 2.47 1.92 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.07 | 1.04 | 0/0 | nan |

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
