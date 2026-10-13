# onCrack R4.1: a cable load generator that measures the server, and the fan-out baseline for R4.2, 2026-10-10

Round 2 left the 1,000-client point at 747 msgs/s for onCrack against Rust's 752, with the load generator at 3.85 of its 4 cores.
That number was the client's ceiling. This unit replaced the client, found that a client that keeps up exposes a flaw in the
saturated phase's load shape (and fixed it), and then measured Rust, the F# port and onCrack in one session at 100, 500, 1,000 and
2,000 clients. R4.2 is judged against the tables below.

**Done:** at 1,000 clients saturated, the server's cores are the limit for all three apps and the load generator is clearly under 4
cores:

| 1,000 clients | server cores busy (of 4) | load generator cores busy (of 4) | load generator CPU per delivery |
|---|---|---|---|
| Rust f9dca47 | 3.86 | 2.44 | 1.99 us |
| F# port | 3.87 | 1.44 | 3.65 us |
| **onCrack** | 3.81 | 2.65 | 1.76 us |
| *the tungstenite client, same load shape (`r41-ab4`)* | *3.43-3.49* | *3.84-3.89* | *4.7-4.9 us* |

Tools: `bench/loadgen/src/rawcable.rs` (the client), `bench/cable/ab` (load generator variants against one running app),
`CABLE_ARGS` and `CABLE_SENDS` in `bench/run`. Tables: [`review/table.py`](oncrack-r4-fanout-baseline/review/table.py) (the baseline)
and [`review/client.py`](oncrack-r4-fanout-baseline/review/client.py) (the load generator runs in `client/`), from the raw JSON beside them.

## The load generator

`loadgen cable --client raw` (the default; `--client tungstenite` is what rounds 1-3 measured with, `--deflate 1` is unchanged).

- **What it is:** each connection is a non-blocking socket in one of `--threads` (3) epoll loops (mio). A loop reads into one 256 KB
  buffer, walks frames by their headers, answers every ping with a pong echoing it (onCrack's direct writes wait for that pong, R2.1),
  counts each subscription's `confirm_subscription`, and looks for the `bmk<seq>z` marker of each posted message. No WebSocket
  library, no UTF-8 check, no `String` per frame, no task wake-up per frame, no lock per receipt. A read that comes back short has
  drained the socket (edge-triggered), so a wake-up costs one `recv`, not two.
- **What it still validates:** every client subscribes (all confirmations) and a message counts for a client once (a sliding bitmap
  of the last 16,384 sequence numbers per client); a message is complete only when every ready client has it; per-client latency is
  recorded per receipt and post-to-last-client latency per message. Bookkeeping is per loop and written by one thread (a `store`, not
  a read-modify-write on a shared line). The result carries a `client` object: reads, bytes, frames, pings answered, odd frames,
  connections closed mid-run.
- **Marker search:** a profile of the first version (`perf` on the load generator, 1,000 clients) put 37% in the kernel's receive copy
  and 28% in `memmem` over 10 KB frames. The message text sits about 1 KB from the end of its frame, so a frame's last 4 KB is
  searched first and the whole frame only when that holds no complete marker (`--tail-window 0` searches whole frames). Alternating
  A/B at 1,000 clients on onCrack (`r41-ab7`, 4 reps): 2.21-2.43 against 2.58-2.80 us of load generator CPU per delivery, 959-1,071
  against 912-991 msgs/s. A frame carrying two messages would be counted for the later one only; this suite posts one message per
  frame, and a miscount can only make a message look undelivered.
- **Threads:** 2 loops were both pegged (2.0 cores) and would be the limit once the server got faster. The host was too noisy that hour to
  separate 3 from 4 (`r41-ab1`, `r41-ab3`); 3 is a headroom choice, not a measured optimum.
- **Tests** (`cargo test`, in `rawcable.rs`): the seen window counts each number once and slides; three clients over two loops each
  receive 400 messages written in uneven pieces (reads cut headers, payloads and markers), an early marker (found by the whole-frame
  fallback), a duplicate on one connection (counted once), and answer a ping with its payload.
- **Cost:** 1.4-2.0 us of CPU per delivery against 4.7-10 us for tungstenite, in the same runs.

## What a client that keeps up exposed

With the raw client and the old load shape (four closed-loop posters, no limit) every run lost messages: in `r41-ab4` with `--window 0`,
`posted` 19,293 but `complete` 541 and 276 connections closed mid-run (the other two: 16,288 / 2,488 with 94 closed, 17,945 / 1,104 with 205). The posters outran the fan-out, the stream's 256-frame ring
(`StreamCapacity`, as tokio's broadcast in Rust) lapped the slowest subscribers, and the server closed them with `reconnect: true`, as
Action Cable does. The tungstenite client was slow enough to throttle the posters without anyone seeing it, which is why round 2's
runs always completed.

So the saturated phase now keeps at most `--window` (128) messages posted and not yet delivered to every client; a poster waits for
message `s - window` to reach every ready client (2 s at most; stalls are counted and were 0). Window 32 already gave the same
throughput (1,719-1,738 against 1,768 at 128 in quiet runs) but left the server at 3.3 cores, a latency bound (window / delivery time);
128 is half the ring and gives 3.8 cores. 192 cost more CPU per delivery (`r41-ab5`). Every cable phase of the session below completed
every message with no connection closed.

Two smaller things the 2,000-client point needed: the load generator's soft descriptor limit (1,024 in the VM) failed 988 of 2,000
connects, so `bench/run` raises it.

## The baseline

One session, 2026-10-10 01:51-02:24, `SERVER_CPUS=0-3 LOADGEN_CPUS=4-7`, the cable suite alone in a fresh container per app and rep
(`review/part.sh`), 3 reps in `bench/run`'s order (rep 1: Rust, port, onCrack; rep 2: onCrack, port, Rust; rep 3 as 1), 15 s
saturated, `--window 128`, the raw client with 3 loops. Images: Rust is **upstream f9dca47** (`campfire-rust-upstream:f9dca47`,
`sha256:63d7de5e36bb`), not round 2's pinned `ccece30`; the port is `campfire-fsharp:app` (`sha256:421f335c3ff8`); onCrack is
`campfire-oncrack:app` (`sha256:69deaa8cdf60`, built from `191c468`; since then `src/` changed only by a Debug log line on a cold path in
`Concerns.fs`). The VM's spin probe before each part read 1.04-1.08 of the quietest ever. Validation, all 48 phases: every client
subscribed, every posted message complete (paced and saturated), 0 failed connects, 0 closed mid-run, 0 window stalls.

**Delivered messages per second** (each message to every client; median of 3, range, and the reps in run order):

| clients | Rust | F# port | **onCrack** | **onCrack / Rust** | **onCrack / port** | port / Rust | reps in run order (Rust / port / onCrack) |
|---|---|---|---|---|---|---|---|
| 100 | 2,628 [2,515-4,229] | 3,374 [2,045-3,540] | **6,160** [3,701-6,903] | **2.34x** | **1.83x** | 1.28x | 4,229,2,628,2,515 / 3,540,3,374,2,045 / 6,903,6,160,3,701 |
| 500 | 1,689 [1,634-2,549] | 899 [667-1,005] | **2,729** [1,978-3,033] | **1.62x** | **3.04x** | 0.53x | 2,549,1,634,1,689 / 1,005,899,667 / 3,033,2,729,1,978 |
| 1,000 | 1,230 [1,189-1,647] | 395 [340-468] | **1,507** [1,272-1,704] | **1.23x** | **3.81x** | 0.32x | 1,647,1,230,1,189 / 468,395,340 / 1,704,1,507,1,272 |
| 2,000 | 689 [588-957] | 169 [163-211] | **731** [657-777] | **1.06x** | **4.34x** | 0.24x | 957,588,689 / 211,163,169 / 777,731,657 |

**Read these ratios with the drift in mind.** Every app fell across the session (Rust 1,647 to 1,189 at 1,000 clients over 20 minutes,
the port 468 to 340, onCrack 1,704 to 1,272) with the spin probe flat; the Mac was running other sessions' builds and tests (load
average up to 7). The order alternates so the drift partly cancels, but paired per rep onCrack / Rust at 1,000 clients is 1.03x, 1.23x and
1.07x, and at 2,000 clients 0.81x, 1.24x and 0.95x. The honest statement: onCrack is clearly ahead at 100 and 500 clients, ahead by
about 5-25% at 1,000, and level with Rust at 2,000. R4.2 must compare against a control measured in its own session.

**Per delivery, cores, memory and latency** (medians of 3; ratios are onCrack / Rust):

| clients | | Rust | F# port | onCrack | ratio |
|---|---|---|---|---|---|
| 100 | server CPU us / delivery | 12.07 | 9.33 | 5.05 | 0.42x |
| 100 | server / load generator cores busy | 3.15 / 1.34 | 3.11 / 1.36 | 3.12 / 1.57 | |
| 100 | sends / delivery | 0.464 | 0.519 | 0.288 | 0.62x |
| 100 | Pss saturated (MB) | 98 | 276 | 267 | 2.73x |
| 100 | paced post to last client, p50 / p99 (ms) | 3.1 / 4.4 | 5.3 / 22.2 | 5.5 / 22.7 | 1.76x |
| 500 | server CPU us / delivery | 4.45 | 8.47 | 2.71 | 0.61x |
| 500 | server / load generator cores busy | 3.67 / 2.30 | 3.78 / 1.66 | 3.70 / 2.52 | |
| 500 | sends / delivery | 0.118 | 0.397 | 0.108 | 0.92x |
| 500 | Pss saturated (MB) | 106 | 532 | 281 | 2.65x |
| 500 | paced post to last client, p50 / p99 (ms) | 6.6 / 7.8 | 8.3 / 12.8 | 6.3 / 9.9 | 0.97x |
| 1,000 | server CPU us / delivery | 3.17 | 9.74 | 2.55 | 0.80x |
| 1,000 | server / load generator cores busy | 3.86 / 2.44 | 3.87 / 1.44 | 3.81 / 2.65 | |
| 1,000 | sends / delivery | 0.031 | 0.351 | 0.065 | 2.11x |
| 1,000 | Pss saturated (MB) | 114 | 649 | 302 | 2.64x |
| 1,000 | paced post to last client, p50 / p99 (ms) | 10.5 / 13.9 | 13.2 / 21.8 | 9.3 / 14.6 | 0.88x |
| 2,000 | server CPU us / delivery | 2.86 | 11.50 | 2.64 | 0.92x |
| 2,000 | server / load generator cores busy | 3.95 / 2.54 | 3.90 / 1.26 | 3.81 / 2.54 | |
| 2,000 | sends / delivery | 0.023 | 0.237 | 0.057 | 2.43x |
| 2,000 | Pss saturated (MB) | 134 | 1,027 | 353 | 2.64x |
| 2,000 | paced post to last client, p50 / p99 (ms) | 17.0 / 23.0 | 21.3 / 29.0 | 13.7 / 19.2 | 0.80x |

The full tables (Pss idle, paced post to a client, saturated latency, load generator CPU per delivery) are the output of `review/table.py`,
and `summary.json` has every number.

- **Server CPU per delivery** is the container's `cpu.stat` over the saturated phase (posting and draining) divided by messages x
  clients. At 100 clients the servers are not CPU-bound (3.1 of 4 cores): the post path (6,160 posts/s for onCrack) is the limit there.
- **Sends per delivery** are from a separate pass (`sends/`, one rep, 8 s saturated, `perf stat` counting send, sendmsg, sendmmsg, write and
  writev of the app over 3 s of the saturated phase); the tracepoints cost the app a few percent, so those runs are not in the msgs/s
  medians. The pass read 1,318 / 394 / 1,342 msgs/s at 1,000 clients (Rust / port / onCrack), in line with the session's. Round 2's
  figures (0.283 for onCrack, 0.19 for Rust, at 1,000 clients) came from the slow client, whose full receive buffers force small writes;
  with a client that keeps up, both batch much more, and onCrack still sends about twice as often as Rust per delivery.
- **Pss** is the app process's peak with every client subscribed and saturated (`procmem.py`).
- **Paced latency** is 30 posts 200 ms apart, post to the last client having it; the p99 of 30 samples is nearly the maximum.

## For R4.2

- At 1,000 and 2,000 clients both onCrack and Rust sit at 3.8-3.95 server cores: the lever is CPU per delivery (2.55 and 2.64 us for
  onCrack, 3.17 and 2.86 for Rust) and sends per delivery (2x Rust). The port's 9.7-11.5 us is what round 1 started from.
- At 100 clients both .NET apps show a p99 of 22 ms for the paced post (median 5.5 against Rust's 3.1) in every rep; it is one or two
  of 30 messages and is not explained here.
- Pss saturated is 2.6-2.7x Rust at every count (the GC heap's high-water mark, as in round 2).

## Deferred

- **More reps in the opposite order.** A fourth rep reversed (or a second block with the apps in the other order) would cancel the
  session's drift better than 3 reps do; the drift itself (all three apps losing 25-30% over 20 minutes, spin probe flat) is not explained.
- **Rust's pinned `ccece30`** (round 2's control) is not rebuilt; this baseline's Rust is upstream f9dca47, as in round 3's headline.
- **Sends per delivery in the median reps** (needs a cheaper counter than `perf stat` tracepoints, or a pass per rep).
- **The load generator's floor**: 37% of its CPU is the kernel's receive copy and ~0.3 `recv` per delivery; it needs no further work
  unless R4.2 pushes the server past about 2.5M deliveries/s.
- **The 100-client post path and p99** above.
- **The tungstenite client** is kept (`--client tungstenite`) for comparison with rounds 1-3; their stored cable numbers are not
  comparable with anything measured here.

## Reproducing

All inside colima (`colima ssh -- bash -c "cd REPO && ..."`); `bin/clean-docker` and `bin/clean-parity` after.

```sh
for rep in 1 2 3; do for app in rust fsharp oncrack; do bench/results/oncrack-r4-fanout-baseline/review/part.sh $app $rep; done; done   # bench/run orders each rep
for app in rust fsharp oncrack; do bench/results/oncrack-r4-fanout-baseline/review/part.sh $app 1 sends; done                              # sends per delivery
python3 bench/results/oncrack-r4-fanout-baseline/review/table.py --json
python3 bench/results/oncrack-r4-fanout-baseline/review/client.py
bench/cable/ab --app oncrack --clients 1000 --reps 4 --variants 'raw:3 raw:3/--tail-window,0'                                              # load generator variants, alternating
(cd bench/loadgen && cargo test --release)                                                                                                 # the raw client's tests
```
