# Round 5, unit R5.1: the message that did not reach every client

Written 2026-10-12 from the hunt of 2026-10-10/11 (about four hours, 395 target phases). This file is evidence for the next unit, which
diagnoses and fixes; nothing under `src/` was changed beyond the switches below.

## Question

Round 4's open item 1 (`bench/results/oncrack-r4-final/cable/t3`, onCrack, 500 clients, rep 1): 34,740 of 34,741 acknowledged posts reached
every client, nobody disconnected, one window stall, the phase waited its full 60 s drain. Is that the server or the load generator?

## Answer in one paragraph

It is the server, and it is not a lost frame. In all 7 misses where the raw client's evidence was on, exactly one client (499 of 500
received the message) was handed a text frame of the right length (10,298 bytes) with intact WebSocket framing, whose payload was NULs
and pieces of other heap objects instead of the message. The only path that hands the kernel a message array in place is the gathered
`sendmsg` (`Sendmsg.pin`, R4.2). With the verify switch on, that path reports, in every phase of a fresh container, arrays that are not
where the kernel was told when `sendmsg` returns, although each is held by a `fixed` local. That reporting never happens with
`CAMPFIRE_CABLE_GATHER=off` or `CAMPFIRE_CABLE_DIRECT=off`, and no miss has happened with either off, with the F# port or with Rust. What
is not closed: one verify-on miss (v3 run03) had no verify report in its phase, and nothing has yet shown the exact way the pin fails
(section "Mechanism"). The F# fix belongs to the next unit; the reproducer for it is `TraceTests.fs` (section "Reproducer": it has not yet produced a verdict).

## What was added (all off by default, committed d8fdaf4..0eaed8f)

| switch | where | does |
|---|---|---|
| raw client evidence (`--client-trace 1` in the bench driver) | `bench/loadgen/src/rawcable.rs` | on a drain timeout writes per client the message ids missing, any text frame over 1 KB with no marker (head, tail, NUL count), and the last frames; `drain-*.jsonl`, `drain-summary.json`, `stall-*.jsonl` per phase |
| `CAMPFIRE_CABLE_TRACE=path` | `src/Campfire.Cable/Trace.fs` | per connection frame numbers sent, chunk crossings, cuts, revocations, gathers and partial gathers |
| `CAMPFIRE_CABLE_VERIFY=1` | `src/Campfire.Cable/Socket.fs` | a probe of each published array, checked before and after the `sendmsg` that reads it, and, while the payloads are still pinned, that the address in the iovec table is where each array is. Reports the first 20 failures, then one a second |
| `LINUX_TESTS_ENV=CAMPFIRE_PIN_STRESS=1` | `tests/Campfire.Cable.Tests/TraceTests.fs` | the gated pin-stress reproducer (below) |

Scripts: `bench/results/oncrack-r5-lost-frame/scripts/` (`hunt.sh`..`hunt10.sh`, `block.sh`, `collect.sh`, `summarize.py`).

## The table

395 target phases in 41 blocks (`scripts/summarize.py data-summary` prints the full per-block table; copy in
`data-summary/table.md`). A target phase is the saturated phase at 500 clients (or 1,000 in `a-warm1000`) in which every acknowledged post
is checked against every client. 11 had a message not delivered to every client.

| group | target phases | with a miss |
|---|---|---|
| onCrack, defaults for the cable (gathered writes on, direct on) | 308 | 11 (3.6%) |
| of which server trace on (`a-*`, `b-ring500`, `c-stream500`, `f-tail0-500`, `g-*`, `j-*`) | 118 | 0 |
| of which server trace off | 190 | 11 (5.8%) |
| `CAMPFIRE_CABLE_GATHER=off` (`k2`, `c4`, `w1`) | 33 | 0 |
| `CAMPFIRE_CABLE_DIRECT=off` (`k3`, `c5`) | 21 | 0 |
| F# port (`d-port500`, `p1-port-stress`) | 16 | 0 |
| Rust (`e-rust500`, `r1-rust`) | 16 | 0 |

The 11 misses:

| block | phase | posted | missing | client evidence |
|---|---|---|---|---|
| ab3-r4-image (the round-4 image, as shipped) | run03 | 40,773 | 1 | client trace off |
| ab3-r4-image | run07 | 42,086 | 1 | client trace off |
| ab3-r4-image | run08 | 33,348 | 2 | client trace off |
| ab4-new-build (4d6f89c mounted, verify off) | run01 | 35,970 | 1 | client trace off |
| d2-procmem-default (fresh, defaults) | run08 | 42,144 | seq 31755 | one client, NUL/pointer payload, 6,887 NULs of 10,298 |
| i-notrace500 | run01 | 38,947 | seq 16579 and 16581 | one client, two frames of 10,298 bytes, all NUL, same instant |
| i-notrace500 | run03 | 30,977 | seq 12530 | one client, 10,298 bytes, all NUL |
| i-notrace500 | run05 | 41,305 | seq 16917 | one client, 10,298 bytes, NULs then a fragment of another string (`"channel":"RoomMessagesChannel","signed_stream_name":"IloybGtPaTh2WTJGdGN...`) |
| m2-gc4mb (gen0 budget 4 MB) | run06 | 41,619 | seq 41137 | one client, 8,864 NULs of 10,298, pointer-like bytes |
| v3-verify-default (verify on) | run03 | 39,784 | seq 21934 | one client, 6,848 NULs of 10,298, pointer-like bytes. **No verify report in the phase** |
| y3-verify-gc4mb-fresh (verify on, 4 MB gen0, fresh) | run02 | 35,906 | seq 32224 | one client, 7,661 NULs of 10,298; the phase has 50 verify reports |

Per-phase detail for the 7 with client evidence: `data-summary/lost-phases.json`; in each of them `received_by` is 499 of 500. Every one of the 11: no
client was closed (`closed_midrun` 0), `failed` 0, and one window stall per missing message (the generator's window of 128
outstanding posts stalls on a post that never completes).

## What the client evidence says

- Not a lost or late frame. The client with the miss has the same `frames` and `bytes` totals as its peers (within a ping), no
  `bad_markers`, no `multi_marker_frames`, `tail_miss` 0: the WebSocket framing of the connection never went out of step. Where the message
  should be, it has one frame of the message's exact length whose payload is wrong (`unmarked_big` 1, or 2 when two messages were in one
  batch). The load generator counted correctly: it did not mistake a good frame for a missing one.
- The wrong payloads are not copies of messages. They are NULs with 8-byte values shaped like heap addresses, or a UTF-8 fragment of a cable identifier string: memory belonging to other managed objects, which is what a kernel copy
  from an address whose object has since been moved away (and its place used for something else, or cleared) would read.
- Round 4's other symptom, "each client got about 20 extra non-message frames", is the 60 s drain itself: the clients' `recent` frames
  show a 36-byte frame every 3 s (the cable ping), 20 of them in 60 s. It is a result of the wait, not a second fault.
- The generator's `result.json` says `drain_secs: 0.0` for these phases although `stderr` shows the harness waited 60 s between
  `saturated_posted` and `saturated_drained`. That is a reporting quirk of the generator's result (not looked into; nothing was changed).

## Mechanism the evidence supports

1. A gathered write passes the kernel the addresses of the frames' own `byte[]` payloads. `Sendmsg.pin` pins them with `use p = fixed
   payload` in a recursion one frame deep per payload, then calls `sendmsg`. Its comment says each payload stays pinned until the call
   returns.
2. With `CAMPFIRE_CABLE_VERIFY=1` and the gathered path, the check made inside the innermost call (every payload "still pinned"), after
   `sendmsg` returned, finds the array elsewhere than the iovec table says (`MOVED before sendmsg returned: the kernel was given
   f4050dfd3018, the array is at f405008dd558 now, generation 1`). `data-summary/verify-moved-per-block.txt`:
   - fresh containers, gather on: all 52 phases of `c0`, `c1`, `c2`, `c3`, `d1`, `y2`, `y3` report it (no GC pressure needed: `c0` has
     the image's own GC settings); warm containers (`v1`, `v2`, `v3`, `y1`): the first phase of the container only (the other 11 or 5
     phases of each, none).
   - gather off (`c4`, `w1`: 18 phases) and direct off (`c5`: 6 phases), same verify switch: not once.
   - All 1,194 parsable reports of those blocks are generation 1, moved both toward lower and higher addresses (753 and 441): array relocation by a
     compacting gen1 collection, not a content write.
3. In the complete reports (first 20 failures of a process, 38 batches counted from payload 0), the highest payload index reported is even
   in 34 of 38. Frames come in pairs (message, 84-byte unread frame), so the last slot of a batch is odd and is the one that never
   appears. This is what you would see if only the last `fixed` local still pinned its array when the call happened; it is consistent
   with that, not proof (batch sizes were not logged).
4. A miss needs the move to land during the kernel's copy and the vacated memory to hold something else by then, which is rare (about
   one message in 40,000) while the move itself is routine. This is why a block can report moves in every phase and have no miss.
5. Misses were only ever seen with gathered writes on; the 54 gather-off and direct-off phases had none. By count alone this is weak (a
   5.8% rate leaves 0 of 54 at about 4% probability); with the MOVED reports, which are absent under the same switches and universal
   in fresh containers, it is the pin's failure that separates the groups.

Candidate for how the pin fails, for the next unit to prove or kill, not established here: F# turns a self-recursive call in tail position
into a loop, so `p` would be one pinned slot overwritten by each payload and only the last array stays pinned when `sendmsg` runs.
Observation 3 fits it. The reproducer decides it.

## Controls and what they did and did not show

| control | result |
|---|---|
| `CAMPFIRE_CABLE_GATHER=off` | 0 misses in 33 phases, 0 MOVED in 18 verify phases |
| `CAMPFIRE_CABLE_DIRECT=off` | 0 misses in 21 phases, 0 MOVED in 6 verify phases |
| `CAMPFIRE_CABLE_LOG=ring` (`b`, `c2`) and `CAMPFIRE_CABLE_ORDER=stream` (`c`, `c3`) | 0 misses in 21 and 21 phases (6 each with trace off) and MOVED still in every `c2`/`c3` phase: neither the log nor the order is involved |
| F# port, Rust | 0 misses in 16 and 16 phases (the port has no gathered writes; the verify switch exists only in onCrack) |
| old image against new build (`ab1`..`ab4`) | misses on the round-4 image as shipped (3 of 8, `ab3`) and on the mounted verify build (1 of 8, `ab4`): the evidence switches did not cause them |
| server trace on | **0 of 118 phases against 11 of 190 with it off** (one-sided hypergeometric p = 0.004). The trace changes the timing or the allocations enough to hide the miss. The "controls" run with trace on (`b-ring500`, `c-stream500`) therefore say little; `c2` and `c3` (trace off, verify on) are the ones that count |
| fresh against warm containers | 2 of 90 against 9 of 218: no rise for fresh containers in misses (moves are another matter: above) |
| GC pressure (`DOTNET_GCgen0MaxBudget`) | 2 of 94 against 9 of 214: no rise in misses either. It is not the budget but the first phase of a process that has the moves |
| `DOTNET_TieredCompilation=0` (`y1`) and `DOTNET_ReadyToRun=0` (`y2`) | moves still reported (y1 first phase only, y2 every phase): not a tiering or R2R artifact |

Earlier summaries of this hunt (that misses rise under GC pressure and on fresh containers) are not supported by the table; what rises
with a fresh container is the verify reports of moves.

## Reproducer

`LINUX_TESTS_ENV=CAMPFIRE_PIN_STRESS=1 bin/linux-tests Cable --filter-method "*gathered writes keep*"` (from
`tests/Campfire.Cable.Tests/TraceTests.fs`, commit 0a792aa): 4,000 gathered writes of 32 frames of 10 KB each while another thread forces
compacting collections; it fails with the count of arrays not where the kernel was told. **It has not been run to a verdict.** The committed test was started once for this report
(2026-10-12 08:02, the build took about 2 minutes) and was stopped by hand after 22 minutes of test time at 100% of one core, with no result:
the tight forced-GC loop beside 4,000 writes of 320 KB may simply be too slow, or it hangs. It needs a smaller loop (fewer iterations, a pause
between collections) and a timeout before it can decide anything; that is the first job of the next unit, ahead of any change to `Sendmsg.pin`.

## What is still unknown

- The exact way the pin fails (the loop hypothesis above is untested; read the IL of `Sendmsg.pin` or change the recursion to see).
- v3 run03: a verify-on phase with a corrupted frame at the client and no verify report at all in its phase (`app.log` and
  `app-errors.log` empty; verify reports at most one a second after the first 20, and the previous report was minutes earlier). Either the
  move was not seen by the check (for instance it happened between `sendmsg` returning and the check, or in a different call path) or
  there is a second way to send bytes that are not the message. The partial-send remainder (copy of the unsent tail after a short
  `sendmsg`) is the other place that reads the arrays outside the pin; the trace's `Partial` events would say, but the trace hides the
  miss. A verify of the remainder path is the cheapest next probe.
- Why the server trace hides it (0 of 118).
- Whether the page's other cable writers (direct writes through `Writer` in `Connection.fs`) have the same hole; the 21 direct-off
  phases are too few to say.
- The 4 misses without client evidence (`ab3`, `ab4`) are counted by the generator only; presumably the same, unconfirmed.
- Round 4's single miss was at 500 clients on the default; no miss was seen at 1,000 (15 phases of `a-warm1000`, all trace on).

## Files

- `/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-lost-frame/data-summary/`: per block `env.txt`,
  `phases.jsonl`, `misses.txt`, `loop.exit`, the hunt logs, `table.md`, `lost-phases.json`, `verify-moved-per-block.txt`.
- The full data (1.2 GB: per phase client dumps, server traces, app logs) stays in the VM at `/var/tmp/r5-lost-frame/<block>/` and is not
  committed.
- `/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-lost-frame/host-load-hunt.txt`: Mac process load
  during the hunt (no relation to the misses found).
