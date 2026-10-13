# onCrack round 5: adversarial verification

Branch `crack`, round 5's changes `c16820f..3e3e184` (R5.1 evidence switches, R5.2 lost-frame fix and memory bound, R5.3 bench flip). Verifier
commits: `6abc183` (product fixes and attack tests), `59f6762` and `f4b7604` (test races and isolation), this report. 2026-10-12, the Mac at load
average 2-18 from other sessions.

## Verdict

R5.2's lost-frame fix holds under every attack thrown at it. Payloads stayed pinned at every batch size round the eight-a-level edges, through
partial sends and under forced compacting collections. A further 31 server phases delivered 740,613 messages to every client: about 420 million deliveries.
**R5.2's memory bound had three real defects in the reader protocol it introduced**, all fixed with tests that fail on `3e3e184`:

1. **An emptied slot read as a null frame.** `Compact` empties slots every subscriber of a group has passed. A subscriber cut by `CutOne` or
   `cutHead` is out of the group at once, but its reader takes no lock. If it had looked at its cut flag a moment before, it read an emptied slot
   and got `Got` with a null frame. The connection put the null into its batch and the write failed on it (`frame.Bytes`). The connection ended
   without the `reconnect: true` goodbye and dropped the rest of that batch. The browser reconnects and refreshes either way, so a user sees the
   same thing; but the log handed a reader something its contract says it never does. **Now** `TryRead` returns `Lagged` for an emptied slot
   (only a subscriber that has left the group can reach one).
2. **A reader crossing into a new chunk read as a whole chunk further behind.** The reader's place was a pair, written in two steps (index 0,
   then the chunk; R5.2's order). A look between the two writes by `Collect` (the hub total's ranking) or `Tally` (the post-pressure verdict) saw the
   old chunk at index 0. In the attack test (chunks of one frame, so every read crosses) that happened in **1.2% of looks on macOS (122,413 of
   10.2 million) and 5,313 of 10.4 million on Linux**. When the hub is over its total, that could cut a client that reads ahead of one further behind.
   **Now** the place is one number: `Subscriber.Slot`, the next slot over the whole log (chunk id x chunk size + index). It is written once, with release, after
   the frame is read; moving to the next chunk is the single `MoveTo`, since a chunk's last slot + 1 is the next one's first.
3. **The reader's index store was not ordered after its frame load.** On ARM64 a plain store can become visible before an earlier load completes.
   `Compact` could then see the slot as passed and empty it under the read: case 1's null frame, for a client that was reading. No test caught this
   on this hardware, and I do not claim it happened. The release store (`Advance`, `stlr`) closes it as part of fix 2.

A fourth, smaller one is in R4.2's gather (not round 5, but in the write path round 5 rebuilt). A gathered write whose `sendmsg` threw, on a
socket closed under it (a cut's abort a second after the goodbye), left the batch's payloads in the thread's scratch: 40 of 40 in the test.
They were held, outside every bound, until the thread's next gather of as many frames. Now cleared on any exit.

The test suite had defects that hid or faked failures. These are fixed in `59f6762` and `f4b7604`, described below.

Nothing here changes a frame's bytes or the UI. The Cable golden replay passes byte for byte, so the pixel gate was not run.
`CAMPFIRE_REQUIRE_SEED=1 bin/verify` passes: **1,204 tests, 1,187 passed, 17 skipped, 0 failed**.

## What was attacked, and what held

| Surface | Attack | Result on `3e3e184` | After |
|---|---|---|---|
| Gather pinning (R5.2 `pinFrom`) | a full compacting collection before `sendmsg`, batches of 1, 2, 7, 8, 9, 15, 16, 17, 63, 64, 65, 127, 255, 256 frames, a frame given twice in a batch, an empty frame (Linux) | held: 0 moved, 0 wrong | same |
| Partial sends | 16 KB send and receive buffers, a client pausing 1 ms every 5 frames, 40 batches of 1-23 frames of 0.5-9.5 KB, a compacting collection before each `sendmsg` (Linux) | held: 0 moved, 0 wrong, at least 10 writes taken in part | same |
| Pin stress (gated, `CAMPFIRE_PIN_STRESS=1`) | 1,500 batches of 32 beside forced gen1 collections every ms | (R5.2: held) | 0 moved, 0 wrong in 3 runs (253, 564, 775 collections) |
| A gather that throws | the socket closed before the call | **40 of 40 payloads left in the thread's scratch** | 0 |
| Cut during a read | the subscriber taken out of its group without its flag (the moment its reader is past the check), the slots emptied, the reader reads on | **`Got` with a null frame** | `Lagged` |
| Chunk crossing | chunks of 1 frame, a reader keeping up, the publisher measuring it with `Collect` between publishes, 1 s | **thousands of looks a chunk further behind** (rate above) | 0 |
| Compact against readers | R5.2's race test (one publisher, eight readers, two threads compacting flat out) | passes | passes; the mutation "advance the slot before reading the frame" fails it 3 of 3 |
| Readers never cut, 64 variants, furthest-behind first, exact bytes | R5.2's tests | pass (one raced, below) | pass |
| Hub total under real load | the R5.1 loop at 500 clients with `CAMPFIRE_CABLE_HUB_BYTES=4194304` | not run | 10 phases, 347,228 messages, 0 not delivered, **0 clients closed** |
| Fan-out (R5.3) | the bench flip off when unset; `BroadcastOrder`'s timer from ticks | unchanged behaviour: the default 1,000 us hold still arms a 1 ms timer, and a hold of 0 still arms 1 ms | same |

The 4 MB total sits below what the room log spans between trims at saturation: about two chunks of 256 frames of about 10 KB, roughly 5.3 MB. So
`Shed` and `Compact` should have run against reading clients every chunk cycle, about 136 times a phase. That is arithmetic, not a measurement: the app
exposes no hub gauge, and a cut would have shown as a closed client.

One edge of the bench flip, bench-only: a connection reads `order` and `log` when it starts, and `Hub.Subscribe` reads `log` when it makes a group. A
flip file changed between the two gives an ordered connection a ring group, which has no publish numbers. `bench/cable/flip` changes the file only between
load generator runs, so its results are not affected. Production never reads the file (`PubsubTests` holds that).

## The fix (`6abc183`)

In `src/Campfire.Cable/Pubsub.fs`:
- `Subscriber` keeps `slot` (int64) instead of `index`. `Slot` is the reader's own read, `SlotSeen` a volatile read by other threads, and
  `Advance` a volatile write after the frame is read. `Locate` derives the index from the slot and the chunk's id; crossing writes only the chunk.
- `Compact` empties the head chunk below the lowest `SlotSeen` of all subscribers. A subscriber past the head has a slot past its end, so the chunk
  check is gone.
- `unread` (for `Collect`) reads the chunk, then the slot, and walks from that chunk to the one holding the slot. `Tally` is `newest - SlotSeen`.
- `TryRead` returns `Lagged` for an emptied slot.

In `src/Campfire.Cable/Socket.fs`, `SendGather` clears the scratch payloads on every exit that did not hand the rest to the copy path, including
an exception.

**Cost.** Measured in process (`oncrack-r5-verifier/scripts/tryrecv-bench.fsx`: 1,000 subscribers drain 256 frames a round, 200 rounds, the two
builds alternated six times): **1.25 ns per `TryRecv` before, 1.91 ns after**, consistent in every pair (`tryrecv-bench.txt`). The release store
costs about 0.66 ns a read. R5.2 and R5.3 measured about 2,300-2,500 ns of server CPU per delivery at 1,000 clients, so this is about 0.03%, far
below what the cable suite can resolve on this host. No suite A/B was run, and no throughput claim is made either way.

## On the server

The R5.1 loop (`bench/cable/loop`: raw client, window 128, 15 s saturated phases, server trace off) ran over `6abc183`. It was published from the clean
measured worktree (`bin/publish-mounted`, 0 dirty files; the build has `SlotSeen` and no `IndexSeen`), mounted over `campfire-oncrack:app`, and run by
R5.2's `proof-r52.sh`. No product file changed after `6abc183`.

| Block | Clients | Environment | Phases | Messages | Not delivered to every client | Clients closed | Window stalls | msgs/s |
|---|---|---|---|---|---|---|---|---|
| a-default-warm500 | 500 | defaults | 12 | 294,706 | 0 | 0 | 0 | 561-2,877 |
| b-default-warm1000 | 1,000 | defaults | 9 | 98,679 | 0 | 0 | 0 | 326-1,273 |
| c-hub4mb-warm500 | 500 | `CAMPFIRE_CABLE_HUB_BYTES=4194304` | 10 | 347,228 | 0 | 0 | 0 | 1,738-2,586 |

The only lines in the app's logs were `WAL restart took N ms` warnings (the VM's disk, R3.4). Rates swing with the host (load 12-18 then). A
fourth block, fresh containers with `CAMPFIRE_CABLE_VERIFY=1`, was dropped: the Mac was at its 12 GB floor, and R5.2 already ran 60 such phases on
the same pinning code. Data: `oncrack-r5-verifier/proof/`.

## The test suite

The full Cable suite under load failed on timing so often that it checked little. On Linux, none of the 10 full runs this session before the changes
was green.
macOS failed about one run in three. Every failure below was traced to a cause or reproduced on unchanged `3e3e184` (a scratch worktree).

- **R5.2's "total: the client furthest behind is cut first" raced the hub.** It set the total before broadcasting, so a broadcast or the trim over it
  queued the hub's own shed on the thread pool. That shed could take the far subscriber out before the test's `Shed` looked, and note the cut after the
  count was read. Alone it failed 2 of 20 runs (`CutCount` 0, expected 1), and it failed on `3e3e184` as well. The total is now set just before the
  test's `Shed`: 0 of 30 failed. The 64-variant test lets a queued shed note its last cut before comparing counts.
- **TraceTests switch process-wide state while everything else runs.** The trace test turns the trace on for the whole process; my chunk-crossing attack
  (about a million publishes a second) then buried its 300 records, and it waited 30 s for them. The gather tests install a hook that forces a full
  compacting collection before every gathered write in the process. On Linux that stalled every socket test beside them ("no frame within 5s" after
  17-27 s).
- **Timing tests in the parallel suite:**
  - "pings every three seconds" allows 100 ms over a 3 s timer. With the same tests, it failed 4 of 8 macOS runs on the fix's product and
    0 of 8 on `3e3e184`'s. Its own path (the timer, a new frame, `Trim` of an empty hub, the wakes, a copy write) runs no code round 5
    changed. Per-class and whole-suite CPU were equal, and the fix's suite finished sooner (17.0-17.6 s against 18.5-21.1 s), so more ran
    beside it: the schedule decided, not the product.
  - The golden replay and DirectTests' "many connections" wait seconds a frame. They failed in nearly every full Linux run, on `3e3e184` as well,
    and passed alone.
  - These, TraceTests and FanOutTests now share the `fan-out` collection (`DisableParallelization`), with unchanged assertions.
- **"unsubscribe stops delivery silently" was a race.** An unsubscribe has no reply, and the test waited 200 ms of silence before broadcasting.
  Under load the broadcast came first and was delivered, as Rails would deliver it. It failed 2 of 2 Linux runs on `3e3e184`. It now waits for the server
  to drop the stream.

After these, macOS Cable was green in all 10 runs: 6 after the first change, then 4 after the second, `bin/verify` among them. Linux Cable was
green in 2 of 3: 1 of 2 with pin stress on, 1 of 1 with it off. The one red Linux run was DirectTests'
"a client ping during the probe is answered": the second probe's answer came after the probe timeout under load, so the connection stayed on the stream
(`DirectConnections` 0). It passed the two runs before.

## Not explained

**ProtocolTests' "unknown channels and malformed commands get no reply" timed out at 30 s once**, in some 40 macOS suite runs on the fix's build. The test client skips
pings, so the `confirm_subscription` that should follow never came in 30 s. It passed 20 of 20 alone and 15 of 15 with its class alone. The
confirm goes from the connection's `Pending` list through the writer's copy path (macOS never gathers). It touches no hub log and no code round 5
changed beyond null trace checks. Not reproduced, not explained, left open.

## Gates

- `CAMPFIRE_REQUIRE_SEED=1 bin/verify` (Release build, warnings as errors, every test): **1,204 tests, 1,187 passed, 17 skipped, 0 failed**. The
  skips are Linux-only or explicit tests.
- `bin/linux-tests Cable` (with `CAMPFIRE_PIN_STRESS=1`): 119 passed, 1 skipped in the green runs.
- Not run: Rust and C rescoring, and PR #6's reliability profiles: no performance claim and no fan-out change in this unit. The pixel gate was not run,
  for the reason above.
- Disk: the Mac went under the 12 GB floor once, from another session's 13 GB Go build cache, with no go process running: `go clean -cache`, as the
  brief allows. `bin/clean-docker` and `bin/clean-parity` were run at the end.

## Open, for the final

- The unexplained 30 s timeout above.
- DirectTests' probe-timing tests can still fail under Linux load. They could join the `fan-out` collection if they keep doing so.
- From R5.2, still true:
  - the total is checked at most every 10 ms;
  - a group's fixed cost and each connection's pending batch sit outside it;
  - frames are copied once per identifier variant.
- New: while the hub is over its total, `Shed` collects and sorts every subscriber with unread bytes at most every 10 ms (O(n log n) allocation
  under attack). Cutting brings it back under, so the cost lasts as long as an attack keeps the hub over.
- `CAMPFIRE_CABLE_LAG_BYTES`'s per-group check (`written - head.Start`) still counts a head chunk's emptied slots. It can cut a group's furthest-behind
  subscribers up to one chunk early (about 2.5 MB against 256 MB). It is conservative, and left as is.

## Data and scripts

`bench/results/oncrack-r5-verifier/`:
- `proof/`: each block's `phases.jsonl`, loop log and environment, plus `proof.log`.
- `tryrecv-bench.txt` and `scripts/tryrecv-bench.fsx`: the in-process cost.
- `suite-controls.txt`: every alternated suite run, HEAD against fix, with what failed and the host load.

The measured worktree (`/Users/clank/Desktop/projects/oncrack-measured`) is at `6abc183`, whose product equals the branch head's.
