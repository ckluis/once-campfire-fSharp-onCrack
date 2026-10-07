# onCrack unit C4: runtime and HTTP

Date 2026-10-07, branch `crack`, commit `2f75677` (Native AOT as an opt-in build, `bench/boot`, a memory line in `bench/paths`). Every number is onCrack's, scored against the
stored medians of `phase7-final` (Rust and the F# port, one session, not re-measured), never a like-for-like port result. `campfire-fsharp:app` (the port) is untouched.

## Result in one paragraph

**Native AOT works, and it is not the default.** It builds with no source change (the app already used `CreateSlimBuilder`), serves every route, and passes the pixel gate. It cuts cold
start and idle memory about in half and the image by a third, wins 9-20% at one connection, and **loses about 10% at sixteen connections on the four read pages** (it has no tiered
PGO). The default image's headline is the c=16 geometric mean, so the default stays JIT + ReadyToRun; AOT ships as `--build-arg NATIVE_AOT=true`, a disclosed opt-in for small hosts and
low concurrency. Nothing else in the unit helped: the syscall count per response is already at its floor under Kestrel, the GC settings are already at their best point, `Tailcalls=false`
and composite ReadyToRun did nothing or hurt. The default image's code is unchanged since C3, so its numbers are C3's (`oncrack-c3.md`).

## Native AOT

Build: `bin/publish-mounted` with `AOT=1` (tier 2, in `campfire-aot-toolchain:latest` = the toolchain image plus clang), or `docker build --build-arg NATIVE_AOT=true .` (tier 3; clang is
installed in the build stage; image `campfire-oncrack:aot`, 269 MB on disk against 422 MB, 71.7 MB of content against 113 MB). `TreatWarningsAsErrors` stays on: the ILC analysis warnings
(FSharp.Core's, and one in `Front/Conn.fs`) are `NoWarn`ed for `PublishAot` builds only in `Campfire.App.fsproj`, with the reason in a comment, and ILC runs with
`OptimizationPreference=Speed` (+3% over the default blend in two paired runs; `IlcInstructionSet=native` added nothing and would tie the binary to the build host's CPU, so it is not set).

What AOT changes at run time, found by looking, not assumed:

- **No JIT, so startup and memory fall.** Cold start (docker run to the first 200 from `/up`, `bench/boot`, 7 fresh containers, median [min-max]): JIT image 218 [197-317] and 204 [190-256] ms
  (two sessions), **AOT 94 [89-113] ms** (publish directory, mounted) and **98 [89-165] ms** (the image). Rust's 118-191 ms in `phase7-final`. Idle memory after 3 s: 38 MB (anon 22) against
  **22 MB (anon 20)**. In `bench/quick`'s tier 3 (idle after 10 s, peak over all five workloads): idle 19 MB (anon 17) against 28 MB (anon 15); cold start 90-130 ms against 200-241 ms.
- **Peak memory over the whole run is not better.** `peak_current_mb` 494-537 against 491-495 for the C3 JIT image, `peak_anon_mb` 244-275 against 219-224 (+15%; the AOT runtime does not
  honor `DOTNET_GCgen0size`: with 16 MiB or 256 MiB the read-page peak stayed 46-50 MB, and throughput did not move). On the read pages alone (`bench/paths`, room + sidebar at c=16)
  the container peaked at 46 MB, against 126 MB for the JIT image. The writes and the Cable run decide the whole-run peak.
- **Throughput at one connection needs a longer thread pool spin.** The JIT runtime calibrates `Thread.SpinWait` at start; the AOT runtime does not, so the pool's default of 70 spins
  is far shorter and each hand-off between workers pays a futex wake: the room page at c=1 ran 11.5k req/s on 1.33 cores against the JIT's 13.3k on 1.95. With
  `DOTNET_ThreadPool_UnfairSemaphoreSpinLimit` at 0x100/0x400/0x1000 it ran 15.5k/16.0k/16.4k at c=1 (CPU per request 164/184/183 us, up from 116) and 110k/109k/110k at c=16 (from 103k).
  0x100 (256) is what the AOT image sets, in `bin/boot`, only when the build left `/opt/campfire/.native-aot`; a value given to the container wins. It spends CPU for latency, as
  the JIT runtime's own spinning does (`ThreadNative_SpinWait` is 6% of the JIT's profile).
- **The c=16 gap is code quality, not scheduling.** At 0x100 the AOT build uses 3.72 of 4 cores against the JIT's 3.77, so it is not idle; it spends 33.8 us per request against 29.9. What is
  missing is dynamic PGO and the tier-1 re-JIT. Static PGO for ILC (a `.mibc` from `dotnet-pgo`) was not tried: the tool is not on nuget.org, and the gain ILC gets from it
  is mostly inlining, which `Speed` already moved by 3%.
- **A lost feature, disclosed:** `H2C_ENABLED` (HTTP/2 without TLS) reaches into a Kestrel internal by reflection (`Front/Conn.fs`); under AOT the type is not there, the front server logs
  `H2C_ENABLED, but Kestrel's connection internals aren't as expected; serving HTTP/1.1 only` (the port's own fallback, tested here: JIT image HTTP/2 200, AOT image HTTP/2 refused, HTTP/1.1 200).
  TLS with ALPN HTTP/2 is Kestrel's own and was not affected by anything seen here, but it was not run.
- Regexes (`RegexOptions.Compiled`, 177 route patterns) fall back to the interpreter under AOT; route recognition is ~0.2-0.4 us per request, so it does not show.

Correctness: `bin/pixel-parity --fast --seeds default` on the AOT image (`PARITY_CANDIDATE_IMAGE=campfire-candidate-oncrack-aot`, built with the new `PARITY_CANDIDATE_BUILD_ARGS`): **361/361
screenshots pixel-equal, 1415 s** (`oncrack-c4/pixel-parity-aot-default-fast.log`; `auth/sign_in/rate_limited` needed its usual re-capture). Tier 3: every response 2xx with 0 connection errors in 30
runs, decoded bytes equal to Rust's on every probed route, post rows equal the 2xx answers. Not run on the AOT image: the other four seeds, the full matrix, the unit tests (they run on the
JIT build; the same source), media variants beyond what the parity seed shows, TLS.

Tier 3, `campfire-oncrack:aot` rebuilt from `2f75677`, all five at c=1 and c=16, 3 reps, warm-up until flat (`oncrack-c4/tier3-aot/`, `vs-stored.md`; logged, `kept: false`). Ranges are the min-max of 3 reps.

| Workload | c | AOT req/s | / F# port | / Rust | CPU us/req | vs C3 JIT image (req/s) |
|---|---|---|---|---|---|---|
| room page | 16 | 108,635 [107,254-108,662] | 2.69x | 3.80x | 35.1 | 124,328 (**-12.6%**) |
| room page | 1 | 15,957 | 2.10x | 2.46x | 160.9 | 13,548 (**+17.8%**) |
| messages page | 16 | 107,256 | 2.84x | 3.57x | 34.1 | 124,328 (-13.7%) |
| messages page | 1 | 16,655 | 2.00x | 2.44x | 155.1 | 13,837 (+20.4%) |
| sidebar | 16 | 121,674 | 3.24x | 4.31x | 30.6 | 138,274 (-12.0%) |
| sidebar | 1 | 18,008 | 2.25x | 2.91x | 147.2 | 16,349 (+10.1%) |
| search | 16 | 120,224 | 3.53x | 4.52x | 31.0 | 136,313 (-11.8%) |
| search | 1 | 17,184 | 2.84x | 3.04x | 154.1 | 14,677 (+17.1%) |
| post a message | 16 | 13,614 | 1.53x | 1.90x | 239.4 | 13,249 (+2.8%) |
| post a message | 1 | 3,513 | 1.15x | 1.26x | 657.2 | 3,399 (+3.4%) |

Geometric means of the five: c=16 **3.47x Rust, 2.66x the port** (default JIT image, C3: 3.84x and 2.95x; AOT is 0.90x of it); c=1 **2.32x Rust, 1.99x the port** (C3: 2.04x and 1.75x; AOT is 1.14x of it).
CPU per request at c=1 is higher than the JIT image's (the spin); at c=16 it is 14% higher (35.1 against 30.2 on the room page).

## What was tried and not kept

All are tier 2 (mounted builds, `bench/paths`, JIT unless stated), two paired runs where a difference under 5% would matter (noise on a cell is about +-5%).

| Change | Result | Decision |
|---|---|---|
| `Tailcalls=false` for every project (`perf` showed 9% of samples under `DispatchTailCalls`, F#'s helper-based tail calls, inclusive) | room c=16 128.4k/125.3k against 124.4k/120.5k-126.2k for the image, sidebar 137.5k/140.5k against 139.8k/137.4k; c=1 the same | **no**: inside noise; the 9% was the work after the call, not the dispatch |
| ReadyToRun composite with the framework (`PublishReadyToRunComposite`) | first `/up` 189 ms against 204-218; **idle 744 MB (anon 724)** against 38 MB | **no**: a seventh of a second saved for 700 MB |
| `DOTNET_GCgen0size` 4 / 16 / 64 MiB (JIT, c=16) | room 121.5k / 122.7k / 125.2k, sidebar 136.0k / 138.3k / 139.1k, container peak 84 / 100 / 126 MB | **stays 64 MiB** (16 MiB gives up 2% for 21% of the read-page peak; the score is throughput) |
| `DOTNET_gcConcurrent=0` | idle 38 MB, room c=16 124.2k, peak 125 MB, all as the default | no change |
| AOT `IlcInstructionSet=native` | room c=16 106.2k against 103-108k | no (and not portable) |
| AOT `DOTNET_GCgen0size` 16 / 256 MiB | not honored: peak 48 / 50 MB, 110.6k / 107.9k | n/a |
| Trimming the JIT build | not tried: ASP.NET Core and Falco use reflection, and trimming changes the footprint of the files, not the process (anon memory is the JIT's code and heaps) | deferred |

## HTTP: syscalls and copies per response

`perf trace -s` on the JIT image at c=16 (room page, cached hit; `target/c4` scripts, not committed): per worker thread one `read` and one `sendmsg` per request, about 1.2 `sched_yield` (the pool's
spin), the `.NET Sockets` thread's epoll at under half an event per request, no `getrandom` beyond the request id's, and `futex` only 161 calls in 4 s. That is the floor for Kestrel's socket
transport; C3's 10 syscalls per request included the second send of a chunked answer, now gone. The profile of the same run (`perf record`, JIT symbols through `DOTNET_PerfMapEnabled=1
DOTNET_EnableWriteXorExecute=0`): kernel 24-27% (the send is 16%), pool spin 6%, `Memmove` 4.5% (2% is the frozen body into Kestrel's pipe, which has no copy-free path from a byte array), the
write barrier stubs 4.4%, Kestrel's response header writing ~1.5%, then a long tail under 1% each: `Regex.RunSingleMatch` 1% (route recognition, one regex per request),
`RailsEncoding` 1.1% and libcrypto 3.4% (the session cookie's HMAC; already a pooled keyed HMAC and a regex-free envelope reader), `Embedded.search` 0.6% (the preload link list).
No preassembled header block or single write was added: the response is already one `sendmsg`, and the header serialization is small enough that replacing Kestrel's header dictionary
would be a rewrite of the adapter for a 1-2% effect, not measurable above 5% noise.

## Tools and files

- `bench/boot`: cold start (`/up`, and the first room page after sign-in), idle memory and RSS in fresh containers; `oncrack-c4/boot.jsonl` has every run.
- `bench/paths` prints the container's peak and current memory after the runs.
- `bin/publish-mounted`: `AOT=1`, `PUBLISH_ARGS`, `aot-toolchain`. `parity/bin/candidate`: `PARITY_CANDIDATE_BUILD_ARGS`.
- Raw runs: `oncrack-c4/t2-aot-spin/` (tier 2 of the AOT publish with the spin), `oncrack-c4/tier3-aot/`.

## Deferred

- A cookie-verification cache (the session cookie's HMAC and decode are ~4% of a cached hit): it needs the envelope's expiry kept with the cached value so a cookie expires on time; a
  correctness risk for a few percent.
- Static PGO for the AOT build; trimming the JIT build; `bin/pixel-parity` (full lean matrix, all seeds) and the unit tests on the AOT build, which should precede making it anything more than an opt-in.
- TLS/ALPN HTTP/2 on the AOT image.
- The default image was not rebuilt this unit (no change to the app's code); its `bin/boot` gains one line, harmless without the marker file.
