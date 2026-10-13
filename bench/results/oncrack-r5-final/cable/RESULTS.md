# R5 final: cable suite

`bench/run --apps rust,fsharp,oncrack --suites cable` as `/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-final/cable/part.sh` runs it (one app, one rep, per call), in
`session.sh`'s order: 3 reps, alternating (rep 1 Rust, port, onCrack; rep 2 reversed; rep 3 as 1), then the sends pass (one rep each, perf-counted send
syscalls). Rust is upstream f9dca47's image, the port `campfire-fsharp:app`, onCrack `campfire-oncrack:app` (built from the clean measured worktree at
ee5a2e9; src identical to 6abc183). 100/500/1,000/2,000 clients, the raw client (3 threads), window 128, 15 s saturated (8 s in the sends pass), fresh
container per part, server on CPUs 0-3 and load generator on 4-7. Host load sampled every 10 s beside each session (`../host-load-cable-*.txt`).

## Three sessions were run; the headline is session 3

| session | what happened | host noise (share of samples with non-VM CPU >= 150%) | status |
|---|---|---|---|
| 1 (`session-1-incomplete/`, 01:16-01:58) | Complete except Rust rep 3: `bench/run` read its memory file at the instant the 200 ms sampler renamed it (virtiofs), aborted that part with no `rust-3.json`, and the session went on. Rust's per-phase counts are in `session.log` (all N/N). `bench/run` now retries that read. | 66% (rust/port/onCrack reps 2-3 at 77-90%) | NOISY and incomplete, not pooled, re-run |
| 2 (`session-2/`, 02:00-02:51) | All 9 reps complete and uninterrupted; the sends pass was stopped by the 12 GiB disk guard at 02:34 (Mac free 11.9 GiB: another project's `go test` regrew its build cache to 5.8 GB), after Rust. The orphaned port sends part was killed and its partial files removed; the port and onCrack sends were finished in a continuation (`sends-rest.sh`, 02:46-02:51, host 77% noisy). | 64% | NOISY and guard-stopped, not pooled, re-run once more (the plan allows three sessions) |
| **3 (`session-3/`, 02:53-03:27)** | **Complete, one uninterrupted session, no guard stop, no failure. All 12 parts (9 reps, 3 sends) finished.** | **7%** (201 samples; max non-VM CPU 390%, max load average 8.3) | **Quiet. The headline.** |

Why not pool: PLAN.md rule 3 (no pooling of a session the guard stops or that is incomplete) and rule 2 (a NOISY session is re-run). Sessions 1 and 2 are
reported in full beside this (`session-1-incomplete/tables.md`, `session-2/tables.md`) and nothing in them was dropped or adjusted. Their spread is the
reason session 3 is the only usable cable measurement: onCrack at 1,000 clients was 1,407 / 1,709 / 226 msgs/s in session 1 and 550 / 362 / 1,460 in session 2
against 1,925 / 1,995 / 2,002 in session 3; Rust at 1,000 clients 796 / 100 in session 1; the port 70-378. Every app swings 3-10x when the Mac is busy
(server CPU per delivery for onCrack at 1,000 clients: 6.49 us in session 2, 1.90 in session 3), so the ratios of the two noisy sessions say nothing
about the apps.

## Validation, every phase of all three sessions (`session-N/phases.md`, `phases.py`)

Every phase in the stored json of every session (Rust rep 3 of session 1 has no json, so `phases.py` did not see its four phases; their counts in that
session's `session.log` are all N / N) posted N and
delivered N to every client (saturated and paced), every client subscribed, 0 failed connects, 0 closed mid-run, 0 odd frames, 0 markers past the cap,
0 receipts without a post time, 0 window stalls. **No phase had a message that did not reach every client; no missing-id dump was produced** (no phase was short, so there is no dump to show). `phases.py` prints a FLAGGED line for any phase that would be; it printed none (`phases flagged: 0` in each
session's `phases.md`).

## Headline: session 3

| app | phases | all clients subscribed | every posted message reached every client (paced and saturated) | failed connects | closed mid-run | window stalls |
|---|---|---|---|---|---|---|
| Rust f9dca47 | 16 | 16/16 | 16/16 | 0 | 0 | 0 |
| F# port | 16 | 16/16 | 16/16 | 0 | 0 | 0 |
| onCrack | 16 | 16/16 | 16/16 | 0 | 0 | 0 |

### Delivered messages per second (each message to every client), median of 3 and the reps in run order

| clients | Rust | F# port | **onCrack** | **onCrack / Rust** | **onCrack / port** | port / Rust | reps in run order (Rust / port / onCrack) |
|---|---|---|---|---|---|---|---|
| 100 | 4,155 [2,990-4,224] | 3,407 [2,975-3,617] | **6,859** [5,992-6,923] | **1.65x** | **2.01x** | 0.82x | 2,990,4,155,4,224 / 3,407,2,975,3,617 / 5,992,6,923,6,859 |
| 500 | 2,625 [2,564-2,758] | 995 [924-1,005] | **3,251** [3,149-3,287] | **1.24x** | **3.27x** | 0.38x | 2,758,2,625,2,564 / 924,995,1,005 / 3,149,3,287,3,251 |
| 1,000 | 1,706 [1,249-1,724] | 464 [322-469] | **1,995** [1,925-2,002] | **1.17x** | **4.30x** | 0.27x | 1,249,1,706,1,724 / 322,469,464 / 1,925,1,995,2,002 |
| 2,000 | 1,054 [789-1,054] | 211 [205-212] | **1,067** [970-1,069] | **1.01x** | **5.05x** | 0.20x | 789,1,054,1,054 / 205,211,212 / 970,1,067,1,069 |

### Server CPU per delivery and cores (the container's cpu.stat over the saturated phase, divided by messages x clients), the load generator's cores
(of 4), sends per delivery (send, sendmsg, write syscalls of the app over 3 s of the saturated phase / deliveries), the app's Pss with every client
subscribed and idle and saturated (MB), and the paced latency of a post to the last client / to a client (ms, p50 / p99). Medians of 3.

| clients | | Rust | F# port | onCrack | onCrack / Rust |
|---|---|---|---|---|---|
| 100 | server CPU us / delivery | 7.17 | 8.58 | 4.44 | 0.62x |
| 100 | server cores busy | 2.96 | 2.99 | 2.99 | 1.01x |
| 100 | load generator cores busy | 1.43 | 1.30 | 1.58 | 1.10x |
| 100 | load generator CPU us / delivery | 3.45 | 3.82 | 2.30 | 0.67x |
| 100 | sends / delivery | 0.622 | 0.641 | 0.330 | 0.53x |
| 100 | Pss idle (MB) | 39 | 111 | 113 | 2.92x |
| 100 | Pss saturated (MB) | 100 | 280 | 272 | 2.72x |
| 100 | paced post -> last client p50 / p99 | 3.3 / 4.6 | 5.0 / 15.5 | 5.2 / 15.2 | 1.55x |
| 100 | paced post -> a client p50 / p99 | 2.9 / 4.4 | 4.3 / 15.3 | 4.8 / 15.0 | 1.62x |
| 100 | saturated post -> last client p50 / p99 | 1.1 / 4.7 | 1.2 / 3.5 | 1.0 / 3.7 | 0.84x |
| 500 | server CPU us / delivery | 2.74 | 7.59 | 2.21 | 0.81x |
| 500 | server cores busy | 3.59 | 3.74 | 3.55 | 0.99x |
| 500 | load generator cores busy | 2.64 | 1.77 | 2.73 | 1.04x |
| 500 | load generator CPU us / delivery | 2.01 | 3.56 | 1.68 | 0.84x |
| 500 | sends / delivery | 0.214 | 0.441 | 0.157 | 0.73x |
| 500 | Pss idle (MB) | 103 | 280 | 272 | 2.64x |
| 500 | Pss saturated (MB) | 106 | 561 | 285 | 2.70x |
| 500 | paced post -> last client p50 / p99 | 6.3 / 9.4 | 7.5 / 11.5 | 6.1 / 11.7 | 0.96x |
| 500 | paced post -> a client p50 / p99 | 4.3 / 7.6 | 4.7 / 9.7 | 4.6 / 11.5 | 1.07x |
| 500 | saturated post -> last client p50 / p99 | 5.7 / 20.2 | 6.1 / 23.0 | 6.5 / 23.1 | 1.15x |
| 1,000 | server CPU us / delivery | 2.25 | 8.30 | 1.90 | 0.84x |
| 1,000 | server cores busy | 3.80 | 3.88 | 3.76 | 0.99x |
| 1,000 | load generator cores busy | 2.83 | 1.58 | 2.91 | 1.03x |
| 1,000 | load generator CPU us / delivery | 1.66 | 3.41 | 1.46 | 0.88x |
| 1,000 | sends / delivery | 0.102 | 0.364 | 0.102 | 1.00x |
| 1,000 | Pss idle (MB) | 112 | 553 | 282 | 2.52x |
| 1,000 | Pss saturated (MB) | 114 | 689 | 317 | 2.77x |
| 1,000 | paced post -> last client p50 / p99 | 10.6 / 13.4 | 12.9 / 20.1 | 9.1 / 12.5 | 0.86x |
| 1,000 | paced post -> a client p50 / p99 | 6.5 / 11.7 | 7.9 / 17.4 | 6.4 / 11.5 | 0.99x |
| 1,000 | saturated post -> last client p50 / p99 | 19.9 / 68.4 | 18.1 / 68.0 | 27.9 / 66.6 | 1.40x |
| 2,000 | server CPU us / delivery | 1.86 | 9.22 | 1.79 | 0.96x |
| 2,000 | server cores busy | 3.94 | 3.88 | 3.78 | 0.96x |
| 2,000 | load generator cores busy | 2.90 | 1.42 | 2.91 | 1.01x |
| 2,000 | load generator CPU us / delivery | 1.37 | 3.35 | 1.36 | 0.99x |
| 2,000 | sends / delivery | 0.043 | 0.312 | 0.079 | 1.81x |
| 2,000 | Pss idle (MB) | 125 | 724 | 311 | 2.48x |
| 2,000 | Pss saturated (MB) | 133 | 934 | 369 | 2.77x |
| 2,000 | paced post -> last client p50 / p99 | 14.9 / 23.1 | 19.7 / 28.2 | 15.1 / 19.3 | 1.01x |
| 2,000 | paced post -> a client p50 / p99 | 8.4 / 18.9 | 13.5 / 26.7 | 8.8 / 17.5 | 1.04x |
| 2,000 | saturated post -> last client p50 / p99 | 101.5 / 156.3 | 48.4 / 160.6 | 72.3 / 133.8 | 0.71x |


## Host noise per part

Session 3:

| part | samples | share >=150% | median sum | max sum | max load avg |
|---|---|---|---|---|---|
| rust rep 1 | 14 | 29% | 42 | 265 | 7.4 |
| fsharp rep 1 | 19 | 11% | 47 | 363 | 8.3 |
| oncrack rep 1 | 17 | 24% | 60 | 390 | 7.3 |
| oncrack rep 2 | 20 | 5% | 28 | 156 | 6.0 |
| fsharp rep 2 | 18 | 0% | 36 | 114 | 4.6 |
| rust rep 2 | 17 | 6% | 22 | 212 | 4.8 |
| rust rep 3 | 20 | 5% | 26 | 159 | 5.0 |
| fsharp rep 3 | 18 | 0% | 22 | 59 | 4.2 |
| oncrack rep 3 | 17 | 0% | 21 | 86 | 5.2 |
| sends rust | 14 | 0% | 29 | 68 | 4.7 |
| sends fsharp | 14 | 7% | 29 | 358 | 3.6 |
| sends oncrack | 13 | 0% | 33 | 125 | 4.2 |
| **whole session** | 201 | **7%** | 30 | 390 | 8.3 |

Session 2:

| part | samples | share >=150% | median sum | max sum | max load avg |
|---|---|---|---|---|---|
| rust rep 1 | 15 | 60% | 181 | 720 | 36.5 |
| fsharp rep 1 | 20 | 80% | 280 | 435 | 55.7 |
| oncrack rep 1 | 20 | 80% | 289 | 455 | 54.6 |
| oncrack rep 2 | 23 | 83% | 305 | 504 | 56.1 |
| fsharp rep 2 | 23 | 83% | 324 | 799 | 66.2 |
| rust rep 2 | 27 | 59% | 247 | 828 | 47.1 |
| rust rep 3 | 17 | 35% | 81 | 413 | 10.1 |
| fsharp rep 3 | 18 | 28% | 95 | 325 | 16.0 |
| oncrack rep 3 | 21 | 52% | 150 | 633 | 15.9 |
| sends rust | 17 | 53% | 182 | 604 | 24.1 |
| sends fsharp | 10 | 100% | 292 | 392 | 35.0 |
| **whole session** | 211 | **64%** | 247 | 828 | 66.2 |

Session 1:

| part | samples | share >=150% | median sum | max sum | max load avg |
|---|---|---|---|---|---|
| rust rep 1 | 11 | 36% | 59 | 299 | 13.2 |
| fsharp rep 1 | 16 | 6% | 32 | 194 | 13.2 |
| oncrack rep 1 | 17 | 29% | 45 | 350 | 11.8 |
| oncrack rep 2 | 57 | 84% | 660 | 954 | 50.4 |
| fsharp rep 2 | 22 | 77% | 270 | 757 | 38.0 |
| rust rep 2 | 17 | 82% | 322 | 453 | 50.9 |
| rust rep 3 | 20 | 90% | 286 | 395 | 54.3 |
| fsharp rep 3 | 21 | 86% | 271 | 459 | 59.8 |
| oncrack rep 3 | 19 | 84% | 262 | 759 | 52.0 |
| sends rust | 16 | 75% | 270 | 576 | 49.8 |
| sends fsharp | 12 | 25% | 37 | 695 | 37.5 |
| sends oncrack | 16 | 38% | 48 | 420 | 17.2 |
| **whole session** | 244 | **66%** | 250 | 954 | 59.8 |

## Reading it

- Against Rust f9dca47, onCrack delivers **1.65x / 1.24x / 1.17x / 1.01x** the messages a second at 100 / 500 / 1,000 / 2,000 clients with 0.62x / 0.81x /
  0.84x / 0.96x of its server CPU per delivery. Round 4's quiet session read 1.59x / 1.24x / 1.16x / 0.94x. At 2,000 clients it is level with Rust, not ahead:
  the 1.01x is inside the spread (Rust's reps 789 / 1,054 / 1,054; onCrack's 970 / 1,067 / 1,069), and both are bound by the `sendmsg` syscall (4 of 4
  server cores busy). Do not read it as a win.
- Rust's rep 1 is its lowest at every count in session 3 (2,990 / 2,758 / 1,249 / 789 against 4,155 / 2,625 / 1,706 / 1,054 median); it ran first after the
  wait, with the session's noisiest samples (29% at >= 150%). It is in the median as the plan says.
- The port (0.20-0.82x of Rust) and onCrack against the port (2.0-5.1x) hold R4's picture. Pss: onCrack 113 MB idle / 272 saturated at 100 clients and 311 / 369
  at 2,000, Rust 39 / 100 and 125 / 133, the port 111 / 280 and 724 / 934: onCrack's Pss is 2.4-2.9x Rust's and about 40% of the port's at 2,000 clients.
- Paced latency (a post to the last client): onCrack is 1.55x Rust at 100 clients (5.2 vs 3.3 ms p50) and level at 500-2,000 (0.96x, 0.86x, 1.01x). This
  is the one cell where Rust is clearly faster; every app's number is higher here than R4's (3.3 vs 1.6 Rust at 100), the host was busier at the start.
- Sends per delivery (syscalls the app makes over 3 s of the saturated phase): onCrack 0.330 / 0.157 / 0.102 / 0.079 against Rust 0.622 / 0.214 / 0.102 / 0.043.
  At 2,000 clients Rust batches into fewer syscalls (0.043 vs 0.079); onCrack's server CPU per delivery is still equal (1.79 vs 1.86 us).
- Raw files: `session-N/t3/*.json` (3 reps) and `session-N/sends/*.json`, `*-logtail.txt` (container log tail), `uptime.log`, `env.txt`. Tables regenerate with
  `CABLE_RES=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-final/cable/session-3 python3 /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-final/cable/session-table.py` (session 3 is the default layout; point CABLE_RES at a session directory).
