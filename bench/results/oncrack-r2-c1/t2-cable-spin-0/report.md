```
date: 2026-10-08T17:25:49-04:00
host: 6.8.0-117-generic, , 8 threads, 5GB
server cpus: 0-3 (nproc 4); loadgen cpus: 4-7; network: host
env: WEB_CONCURRENCY=3 JOB_CONCURRENCY=3 RAILS_MAX_THREADS=5 
rust extra env: 
fsharp extra env: 
oncrack extra env: DOTNET_ThreadPool_UnfairSemaphoreSpinLimit=0
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
| idle memory.current (MB) | 29.0 |
| idle anon (MB) | 15.0 |
| peak memory.current under load (MB) | 399 |
| peak anon under load (MB) | 212 |

### HTTP (signed in as david; keep-alive; c = concurrent connections)

| Metric | onCrack |
|---|---|

### Action Cable fan-out (one room; chatter.js subscriptions per client)

| Metric | onCrack |
|---|---|
| 100 clients: subscribed | 100 |
| 100 clients: connect+subscribe all (s) | 0.07 |
| 100 clients: paced post→one client p50 ms | 4.47 |
| 100 clients: paced post→all clients p50 ms | 5.01 |
| 100 clients: paced post→all clients p99 ms | 22.0 |
| 100 clients: max sustained msgs/s (delivered to all) | 5,191 |
| 100 clients: deliveries/s (client×message) | 519,136 |
| 100 clients: saturated post→all p50 ms | 1.35 |
| 100 clients: saturated POST p50 ms | 0.70 |
| 500 clients: subscribed | 500 |
| 500 clients: connect+subscribe all (s) | 0.11 |
| 500 clients: paced post→one client p50 ms | 4.73 |
| 500 clients: paced post→all clients p50 ms | 6.86 |
| 500 clients: paced post→all clients p99 ms | 9.11 |
| 500 clients: max sustained msgs/s (delivered to all) | 1,524 |
| 500 clients: deliveries/s (client×message) | 761,985 |
| 500 clients: saturated post→all p50 ms | 7.50 |
| 500 clients: saturated POST p50 ms | 2.38 |
| 1000 clients: subscribed | 1,000 |
| 1000 clients: connect+subscribe all (s) | 0.14 |
| 1000 clients: paced post→one client p50 ms | 7.24 |
| 1000 clients: paced post→all clients p50 ms | 11.3 |
| 1000 clients: paced post→all clients p99 ms | 62.0 |
| 1000 clients: max sustained msgs/s (delivered to all) | 819 |
| 1000 clients: deliveries/s (client×message) | 819,316 |
| 1000 clients: saturated post→all p50 ms | 17.2 |
| 1000 clients: saturated POST p50 ms | 4.33 |

### Memory during cable fan-out, by process (MB, peak within the phase)

App process: Rails' Puma master and workers (Action Cable runs in them), or the Rust and F# ports' one campfire
process (its front server included). Pss counts pages shared between forked workers once;
RssAnon counts them in every process.

| Metric | onCrack |
|---|---|
| 100 clients, all subscribed, idle: app process Pss | 113 |
| 100 clients, all subscribed, idle: app process RssAnon | 33.0 |
| 100 clients, all subscribed, idle: app + Redis + Thruster Pss | 113 |
| 100 clients, all subscribed, idle: whole container Pss | 113 |
| 100 clients, saturated fan-out: app process Pss | 268 |
| 100 clients, saturated fan-out: app process RssAnon | 182 |
| 100 clients, saturated fan-out: app + Redis + Thruster Pss | 268 |
| 100 clients, saturated fan-out: whole container Pss | 268 |
| 500 clients, all subscribed, idle: app process Pss | 268 |
| 500 clients, all subscribed, idle: app process RssAnon | 181 |
| 500 clients, all subscribed, idle: app + Redis + Thruster Pss | 268 |
| 500 clients, all subscribed, idle: whole container Pss | 268 |
| 500 clients, saturated fan-out: app process Pss | 282 |
| 500 clients, saturated fan-out: app process RssAnon | 194 |
| 500 clients, saturated fan-out: app + Redis + Thruster Pss | 282 |
| 500 clients, saturated fan-out: whole container Pss | 282 |
| 1000 clients, all subscribed, idle: app process Pss | 280 |
| 1000 clients, all subscribed, idle: app process RssAnon | 192 |
| 1000 clients, all subscribed, idle: app + Redis + Thruster Pss | 280 |
| 1000 clients, all subscribed, idle: whole container Pss | 280 |
| 1000 clients, saturated fan-out: app process Pss | 301 |
| 1000 clients, saturated fan-out: app process RssAnon | 213 |
| 1000 clients, saturated fan-out: app + Redis + Thruster Pss | 301 |
| 1000 clients, saturated fan-out: whole container Pss | 301 |

## Validity

### Load average before each run (1, 5, 15 minutes; the run waited for the 1-minute figure to fall below LOAD_MAX)

| App | Rep | Before | After |
|---|---|---|---|
| onCrack | 1 | 1.29 2.12 2.33 | 3.88 2.65 2.49 |

### Host CPU probe (a fixed spin timed on every pinned CPU, against the quietest this VM has shown; bench/lib/hostprobe.py)

The VM's load average cannot see another program on the Mac taking the cores its vCPUs run on; this can. A ratio of 1.00 is a quiet host, above 1.10 the pinned server and load generator were slowed by something outside the run. `After each window` probes the machine right after every measured run of the rep.

| App | Rep | Before the run | After the run | Windows probed above 1.10 | Highest after a window |
|---|---|---|---|---|---|
| onCrack | 1 | 1.04 | 1.08 | 0/0 | nan |

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
