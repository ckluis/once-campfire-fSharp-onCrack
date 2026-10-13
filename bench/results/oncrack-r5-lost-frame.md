# Round 5, units R5.1 and R5.2: the message that did not reach every client

R5.1 (2026-10-10/11, the sections after "R5.2" below) found the fault. R5.2 (2026-10-12, the next section) proved the cause, fixed it and proved the
fix. **Conclusion: the defect was round 4's gathered write pinning only the last payload of each batch. It is fixed (54fb67f) and covered by a test
that fails without the fix, and no message was lost or corrupted in 105 target phases after the fix.**

## R5.2: cause, fix, proof, cost (2026-10-12)

### The cause, proven

`Sendmsg.pin` (R4.2) pinned each payload with `use p = fixed payload` and called itself for the next one, in tail position. The F# compiler turns a
self-recursive tail call into a loop. The IL of round 4's `pin` (read from the Release build with `System.Reflection.Metadata`) has one
`pinned byref uint8` local and ends its body with `br` back to offset 0000. So the one pinned slot was overwritten for each payload, and during
`sendmsg` only the batch's last payload was pinned. A compacting gen1 collection on another thread during the call could move the others: the kernel
read the old addresses, and once something else was allocated there, a client got the message's length of NULs and other objects' bytes. Round 5.1's
observation 3 (the highest index reported moved was even in 34 of 38 batches) is this: the last slot, the one never reported, was the pinned one.

Direct proof, with a test hook that runs a full compacting collection after the iovec table is filled and before the `sendmsg` (`SetBeforeSendmsg`,
tests only): round 4's `Sendmsg.pin` (b6d0a9a's `Socket.fs`, the hook and two factories added so the tests compile) fails the new test with **620 of 640
payloads moved: 20 batches of 32, every payload except the last of each batch**. The bounded contention reproducer fails it too (713 moved). In that small
test process the client still read the right bytes, because nothing had reused the vacated memory yet; the address check is the decisive one.

### The fix (54fb67f)

`Sendmsg.pinFrom` pins payloads with eight `fixed` locals per stack frame and recurses for the next eight. The recursive call is followed by a check that
reads that level's payloads (the verify switch's address check), so it is not in tail position: F# cannot make it a loop and the JIT cannot drop the
frame. IL: eight pinned locals, `call pinFrom`, no `tail.` prefix. Every level's pins stay on the stack until `sendmsg` returns; the kernel copies TCP
data during the call, and what a partial send leaves is copied by managed code (`FinishSend`), so nothing needs pinning after it. The scratch headers
are on the pinned object heap. `Frame`'s constructor is now private: frames come only from `OfString`, `OfBytes` and `Concat`, which fill every byte of
the array before the frame exists, so before anyone can publish it.

A first fix (426bcef) put every payload on the pinned object heap instead, which needs no pinning at all. It was proven the same way (below) and then
replaced because it costs memory (section "Cost"). Tests, in `tests/Campfire.Cable.Tests/TraceTests.fs`:

| test | kept fix | round 4's pin | mutation of the kept fix: recursive call back in tail position | first fix with `pinned = false` |
|---|---|---|---|---|
| "a compacting collection just before a gathered write's sendmsg changes nothing the client reads" (Linux, ungated, 25-37 ms) | pass | fail, 620 of 640 moved | fail, 480 of 640 moved (all but the last level's eight) | fail |
| "gathered writes keep their payloads where the kernel was told under contention with compacting collections" (`CAMPFIRE_PIN_STRESS=1`; 1,500 batches beside forced gen1 collections, bounded at 60 s) | pass (under 1 s) | fail, 713 moved | fail, 552 moved | fail, 480 moved |

R5.1's reproducer never reached a verdict (22 minutes, stopped by hand): its collector forced collections back to back, which starved the writing thread.
The new one pauses 1 ms between collections and has a 60 s ceiling; it decides in under a second.

`bin/linux-tests Cable` (54fb67f, with `CAMPFIRE_PIN_STRESS=1`): 106 passed, 1 skipped, 1 failed: `pings every three seconds with a unix timestamp`, 3.39 s
against its 3.1 s bound. It fails the same way on unchanged b6d0a9a (3.87 s) and in every full Linux run this session (3.25-3.89 s), and passes alone
(3.09 s): it is a timing test squeezed by the parallel suite in the VM, not this change. The golden replay failed once in five full runs and passed alone and
in the other four. macOS `dotnet test` of the Cable suite: 101 passed, 7 skipped (the Linux-only ones).

### The proof on the server

The R5.1 loop (`bench/cable/loop`, the raw client with its evidence on, window 128, 15 s saturated phases, the server trace OFF, the configuration in which
every miss happened) over the fix's build, published from the clean measured worktree (`bin/publish-mounted`, 0 dirty files) and mounted over
`campfire-oncrack:app`; the runner is `scripts/proof-r52.sh`. A target phase checks every acknowledged post against every client.

| build | block | containers | environment | target phases | messages posted | not delivered to every client | clients closed | window stalls | verify reports |
|---|---|---|---|---|---|---|---|---|---|
| kept fix 54fb67f | a-verify-gc4mb-fresh | fresh, 500 clients | `CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000` | 30 | 1,301,012 | 0 | 0 | 0 | 0 |
| kept fix 54fb67f | b-verify-default-fresh | fresh, 500 | `CAMPFIRE_CABLE_VERIFY=1` | 30 | 1,114,259 | 0 | 0 | 0 | 0 |
| kept fix 54fb67f | c-default-warm500 | warm, 500 | the defaults | 15 | 521,203 | 0 | 0 | 0 | (off) |
| kept fix 54fb67f | d-default-warm1000 | warm, 1,000 | the defaults | 10 | 258,877 | 0 | 0 | 0 | (off) |
| kept fix 54fb67f | alternation (below, "Cost"): stack1, stack2 | warm, 500 | `CAMPFIRE_MEM_LOG_MS=1000` | 20 | 734,848 | 0 | 0 | 0 | (off) |
| first fix 426bcef | a, b, c as above, and poh1, poh2 | | | 30 + 30 + 15 + 20 | 3,558,298 | 0 | 0 | 0 | 0 in 60 |

The kept fix: **105 target phases, 3,930,199 messages, about 2.1 billion deliveries, 0 not delivered to every client, 0 verify reports in 60 verify-on
phases.** The only lines in the app's error log were 12 `WAL restart took N ms` warnings (the VM's disk, R3.4). Data: `oncrack-r5-lost-frame/data-r52/proof/`
(the first fix's in `proof-poh/`); `python3 scripts/summarize.py data-r52/proof` prints the table.

Against R5.1, same loop and settings, round 4's code: with the trace off, 11 of 190 default phases had a miss. If the rate were unchanged, 0 in 105 would have
probability 0.2% (0.942^105). The verify switch is the sharper signal: on round 4's code it reported moved arrays in **every one of 52 fresh-container phases**
(`c0`-`c3`, `d1`, `y2`, `y3`), with or without GC pressure. On the kept fix it reported none in 60 fresh-container phases, 30 of them at the 4 MB gen0
budget, and the first fix none in 60 either.

### Cost at 1,000 clients

All at 1,000 clients, the cable suite of `bench/run` (raw client, window 128, one rep a run), arms rotated so that none always follows another, the builds
mounted over the same image. CPU is the server's per delivery (us), Pss its memory at saturation. Data: `data-r52/{cost-poh,arms,final}`;
`python3 scripts/arms-table.py DIR BASE` prints each round.

| rotation | arms (median CPU us / msgs/s / Pss MB) | CPU against the base, median of per-round ratios |
|---|---|---|
| `arms`, 6 rounds | pre-fix b6d0a9a 2.42 / 1,528 / 304; pinned heap 2.33 / 1,613 / 362; **stack (the kept code) 2.33 / 1,557 / 316**; gather off 2.26 / 1,676 / 308 | stack 1.004, pinned heap 0.963, off 0.988 (each against pre-fix; rounds range 0.77-1.31) |
| `final`, 6 rounds, the committed 54fb67f | **gather on 2.74 / 1,383 / 300**; gather off 2.29 / 1,679 / 311 | on/off 1.22 over all six; 1.01 without rounds 4 and 5 (below) |
| `cost-poh`, 4 rounds, the first fix | round 4's image 2.12 / 1,797 / 297; pinned heap on 2.41 / 1,571 / 363; off 2.26 / 1,675 / 401 | on 1.06, off 1.11 against round 4's image (a different build: no R5.1 switches) |

Rounds 4 and 5 of `final` were starved by the host: the load generator's cores fell to 1.10 and 1.55 (2.82-2.87 in the other rounds), the gather-on run of
round 4 posted 184 msgs/s at 17.6 us a delivery, and round 5 was slow for both arms. The Mac's load average was 4-12 all afternoon, from other sessions;
the VM reports no steal time, so a starved vCPU shows up as CPU per delivery.

**The fix costs nothing measurable:** the kept code against the pre-fix code in the same rotation is 1.004 by the median of rounds, with Pss 316 MB against
304. The first fix (payloads on the pinned object heap) was as fast but took +19% Pss (362 MB; its first rotation 357-435 MB against 293-312 for round 4's
image): pinned-heap arrays are reclaimed only by gen2 collections (in the alternation below, its first block reported 123-203 MB of fragmentation a phase; the
stack pin's phases 39-63 MB).
That is why it was replaced.

**Gather against copy is not separable on this host this afternoon:** off against pre-fix 0.988, on against off 1.01 without the two starved rounds, rounds
ranging ±30%. R4.2 measured -9% to -30% CPU per delivery for gathered writes in its own session; this session neither confirms nor contradicts it. It is
recorded as an open item: a same-process A/B with a runtime switch would settle whether gathered writes still pay for the care they need.

Whether the stack pin has a pathology the heap does not (many arrays pinned when a collection lands): the alternation (`data-r52/alt`, `scripts/alt-table.py`)
ran the two fixes by block in one session (pinned heap, stack, pinned heap, stack; 10 warm phases each at 500 clients, the GC's view logged every second).
Median 2,604 msgs/s for the pinned heap and 2,615 for the stack pin. Phases under half the median: 3 of 20 for the pinned heap, 1 of 20 for the stack pin,
at Mac load averages of 5.7-10.1 (`alt/hostload-mac.txt`; other phases ran normally at the same loads, so the load does not explain each one). Both fixes
have them, the pinned heap more often, and none of R5.1's 395 overnight phases did: they come with this afternoon's host, not with the stack pin. GC pause per 15 s phase: median 398 ms for the
stack pin, 184 ms for the pinned heap (whose first block ran a different mix, 38-46 gen2 collections a phase; its second block's first seven phases paused
289-410 ms like the stack's). No delivery suffered in either.

### R5.1's open questions, answered

- **How the pin failed:** proven above (the IL, and 620 of 640 moved under the hook).
- **v3 run03** (a verify-on phase whose client got a corrupted frame, with no verify report): not explained. Round 4's check ran in the innermost call
  after `sendmsg` and compared every payload's address, so a move during the call should have been reported. After the fix, 0 corrupted frames and 0 verify
  reports in 60 verify-on phases.
- **Why the server trace hid the miss** (0 of 118): not established. The trace adds work per batch, which changes how batches line up with collections; the
  mechanism needs a collection inside a `sendmsg` and a reuse of the vacated memory before the kernel's copy. Moot after the fix: every proof block ran with
  the trace off, the configuration in which the misses happened.
- **Other direct writers:** audited. In `Campfire.Cable` the only native call given managed addresses is the gathered `sendmsg`; the copy path, control
  frames and the remainder of a partial send go through `Socket.SendAsync`, which pins its memory itself. Elsewhere in `src/`: `Sql.fs` binds text from a
  scratch array allocated on the pinned object heap and binds blobs inside a straight-line `fixed`; `Deflater.fs` calls libdeflate inside two straight-line
  `fixed` locals. Neither involves a tail call or a loop. Nothing else hands native code a managed address.
- **The 4 misses without client evidence (ab3, ab4):** not re-run. They were on round 4's code, which has the defect.
- **The generator's `drain_secs: 0.0`:** unchanged, a reporting quirk.

### Can "no lost messages" be claimed?

Yes, for what was measured, with its limits stated. The one way R5.1 found messages going wrong is removed. Its mechanism is proven: the IL, and 620 of 640
moved under the hook. A test fails without the fix and passes with it, and runs in every `bin/linux-tests Cable`. After the fix the loop that found it
saw no message missing or corrupted at any client in 105 phases (3.9 million messages to 500 or 1,000 clients each) and no moved array in 60 verify-on
phases, under the conditions that produced the most moves before.

What this does not cover: it is a statistical result for the paths the load exercises (one room, 500 or 1,000 subscribers, plain TCP, gathered writes, no
compression on the generator's side). The fix is a pinning discipline that a future compiler change could undo; the ungated test is what guards it. One
R5.1 miss (v3 run03) is unexplained, and nothing like it was seen in 200 phases of the two fixes. Round 4's other reliability results (cable_heavy, the
lag cut, the hub budget) were not re-run here: cutting a slow reader stays the documented behavior (a reader that is cut is told to reconnect and refreshes
the room), so "no lost messages" means that no message a connected subscriber should get is skipped or corrupted.

### Open after R5.2

- Whether gathered writes still pay (above): a same-process A/B with a runtime switch. If they do not, turning them off removes this whole class of risk.
- `ProtocolTests` "pings every three seconds with a unix timestamp" fails in every full `bin/linux-tests Cable` run in the VM (3.25-3.89 s against a 3.1 s
  bound, also on unchanged b6d0a9a) and passes alone: a timing bound too tight for the parallel suite. Not changed here.
- v3 run03 (above), and why the server trace hid the miss: unexplained, moot for the fix.
- The R5.1 reproducer's gate and the deterministic test cover `Sendmsg` on Linux only; macOS always copies.

### Files (R5.2)

- `src/Campfire.Cable/Socket.fs` (`Sendmsg.pinFrom`, `Frame`'s factories, `SetBeforeSendmsg`), `src/Campfire.Cable/Pubsub.fs` (`GroupBase.Frame`),
  `tests/Campfire.Cable.Tests/TraceTests.fs` (the two tests).
- `bench/results/oncrack-r5-lost-frame/scripts/`: `proof-r52.sh` (the proof's blocks), `cost-r52.sh` and `arms-r52.sh` (rotations), `collect-r52.sh`,
  `arms-table.py`, `alt-table.py`; data in `bench/results/oncrack-r5-lost-frame/data-r52/` (`proof`, `proof-poh`, `cost-poh`, `arms`, `final`, `alt`).
- The VM keeps the full evidence under `/var/tmp/r52-proof`, `r52b-proof`, `r52-cost`, `r52-arms`, `r52-final`, `r52-alt` (not committed), and the
  mounted builds `/var/tmp/campfire-r52b` (54fb67f), `campfire-r52` (426bcef), `campfire-r52-pre` (b6d0a9a).

---

# R5.1 (2026-10-10/11): the hunt

Written 2026-10-12 from the hunt of 2026-10-10/11 (about four hours, 395 target phases). Evidence for R5.2, which diagnosed and fixed; nothing under `src/` was
changed in R5.1 beyond the switches below.

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
