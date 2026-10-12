# R5.2 memory bound: the hub's total reaches every chunk

Branch `crack`, commit `db83b63`. Round 4's open item 8: the hub-wide total (`CAMPFIRE_CABLE_HUB_BYTES`, 1 GiB) never trimmed a group's
newest chunk, so a client subscribing with 64 identifier variants and reading nothing pinned about 160 MB outside it. This closes it:
total retained Cable memory is bounded by the total, for any number of such clients, and a client that reads is never cut.

## What was wrong

Every identifier a client subscribes with is a group of its own with its own copy of each frame (the identifier is inside the frame, so
the copies differ). A group's log is a list of 256-frame chunks. Round 4's `Hub.Shed` cut "the subscribers in the oldest chunk of the log
that would free the most", and `ShedOldest` refused a log whose head chunk was its tail. Two consequences, both reproduced on round 4's code
(`b1ce8d9`) with this unit's tests, which were copied into a scratch worktree of it:

1. **The gap.** 40 connections x 64 variants reading nothing, against a 32 MiB total: the first check already reads 37,177,056 bytes retained
   and nothing is ever cut; over real sockets (3 x 64 variants, 40 KB frames, 16 MiB total) all 193 groups were still there 20 s later.
   Unbounded, that attack holds one copy per variant per connection of everything posted since each subscribed (2 GB in the Hub-level test).
2. **A worse one the same tests found.** Round 4 counted the read-but-not-yet-freed part of a chunk as retained and could cut only whole
   chunks, so over the total it cut *readers*: 40 connections x 64 variants that read every frame as it arrived were cut (`Lagged`) in the
   test with a 24 MiB total, a total that one broadcast's fan-out (2,560 copies of 4 KB) does not reach, though the bytes were all read. The
   bound bit the clients it was not meant for.

## What Rails does, and the options

Read in `actioncable-8.1.3` (`connection/subscriptions.rb`, `connection/stream.rb`): **no limit on subscriptions per connection**
(`Subscriptions#add` only refuses a repeated identifier), and each connection's write buffer is a `Queue.new` that never ends. Rails bounds
nothing and cuts nobody; onCrack's `MaxSubscriptions` (64, with `MaxIdentifierBytes` 4,096) is already tighter than Rails, and a page uses six.

| Option | Verdict |
|---|---|
| Cap distinct streams per connection (lower than 64) | Rejected. It bounds one connection, not the sum; a page needs six, an attacker needs K connections. Stays at 64. |
| Share frames between variants of one stream (a payload once, the identifier prefix per group, gathered by `sendmsg`) | Rejected for now. It divides the multiplier by 64 but still has a floor per group that is not sheddable, so the sum is not bounded; and it changes `Frame`, `FinishSend` and the gather path that R5.2's lost-frame fix just made correct. |
| **Count every frame some subscriber has yet to read, and cut the subscribers furthest behind, in any chunk** | **Taken.** Smallest change that makes the sum bounded. |

## The change (`src/Campfire.Cable/Pubsub.fs`)

- `LogGroup.Compact`: moves the head to the oldest chunk a subscriber is in, then empties the slots of that chunk that every subscriber is past
  (a group with no subscribers holds nothing). Retained bytes are now *what some subscriber has yet to read*, not the chunk it is in. The
  heartbeat's `Trim` calls it, so an idle room no longer holds its last chunk either.
- `Hub.Shed` (over the total; a pool item at most every 10 ms, and from the heartbeat): every log compacts first, so a client that reads pins
  nothing however many streams it has. If the logs still hold more, it collects the unread bytes of every subscriber (summed from the chunk's
  frames, only on this path), sorts furthest behind first, and cuts one at a time, compacting after each (`LogGroup.CutOne`), until under. A
  cut subscriber's group is emptied at once; its connection closes with `reconnect: true` (aborted after `Wake.CutGrace`, 1 s) and takes its
  other groups with it.
- **Readers stay lock-free**, so emptying a slot must never take one a reader will read. Compact reads each subscriber's chunk, then its
  index, and empties only below the lowest index of a subscriber in the head chunk. A reader moving to the next chunk now writes its index
  (0) *before* it writes the chunk (`Locate`), so a thread that sees the new chunk never pairs it with the old index; an index only grows,
  so a stale reading is lower and empties less. Mutation C below moves them back.
- No new storage: positions come from summing frame lengths (a first version kept a per-frame `Before` array: +2 KB per group, replaced).

## Tests (`tests/Campfire.Cable.Tests`)

| Test | What it proves |
|---|---|
| PubsubTests "total: connections that read nothing, each with 64 identifier variants ..." | 40 attackers x 64 variants + 8 readers x 64 variants, 200 frames of 4 KB, 32 MiB total: retained is at or under it after every step, the peak is at most the total plus one broadcast's fan-out (3,072 copies), every reader got all 12,800 frames, and every cut subscriber was an attacker's |
| "total: connections that read all they are sent, 64 variants each ..." | 40 x 64 readers, 300 frames, 24 MiB total: 0 cuts, retained never over the total, 0 at the end |
| "total: the client furthest behind is cut first ..." | exact order and amount: cutting the one 90 frames behind frees down to the next (80,000 bytes), nobody else is cut |
| "log: what is retained is what some subscriber has yet to read ..." | exact bytes after partial reads (200, not the 256 of the chunk), reads after emptying are whole, a subscriber added mid-chunk sees only what follows |
| "log: emptying read slots while one publisher and eight readers run ..." | the lock-free argument: two threads compacting flat out under one publisher and eight readers (chunks of 16), 2 s, nothing lost or reordered |
| ProtocolTests "clients with 64 identifier variants that read nothing are cut ..." | real sockets and the real `Server`: 3 clients x 64 variants of one room that read nothing, one client that reads, 60 frames of 40 KB, 16 MiB total: the reader gets all 60, the attackers' connections are closed and all their groups gone, retained is under the total, peak is under 160 MiB (about 460 MB if nothing were shed: 193 groups x 60 x 40 KB) |

Mutations, each failing what it should: no cuts (5 tests, including the real-socket one and round 4's two "hub budget" tests); one slot too many
emptied (the exact-bytes test); chunk moved before index (only the race test, which failed in every run). On round 4's code the three attack tests
(first, second and last) and the two exact-bytes tests fail as described above (the race test is about this unit's own mechanism). `bin/verify` (1,198 tests): all passed except two Db timing tests (`CheckHoldTests`, a WAL restart test)
that failed with the Mac's load average at 30 and pass alone; `bin/linux-tests Cable`: 112 passed, 2 gated. Under that load
`pings every three seconds` (3.1 s limit) and `many connections ... sees every frame` (counts connections that answered their probe in time)
failed once each in full-suite runs and pass alone; neither touches this code.

## Cost at 1,000 clients (R4.1 cable suite, raw client, window 128)

Mounted builds of the clean measured worktree, rotated six rounds, one `bench/run` cable rep each (`ab-table.txt`, `ab-table.py`, data in
`r52mem-ab/`): *before* is `54fb67f` (the lost-frame fix, the last code before this), *after* is `db83b63`.

| | before | after |
|---|---|---|
| median messages/s (each to 1,000 clients) | 1,431 | 1,626 |
| median server CPU per delivery | 2.58 us | 2.34 us |
| median Pss at saturation | 295.5 MB | 292.5 MB |
| per-round after/before CPU per delivery | 0.893 1.156 0.959 1.727 0.562 0.958 | median 0.958 |

All twelve phases are valid (every posted message complete, 0 clients closed). The host was busy: load average 12-34 from other sessions, and
two rounds were starved (round 4's *after* at 526 messages/s, round 5's *before* at 919). Read it as **no regression and no gain**: the
common path only adds the heartbeat's compaction and one store order in `Locate`; with a 1 GiB total the shed never runs in this suite.

## What is still not bounded, and what moves

- **Overshoot between looks.** The total is checked on each broadcast and acted on at most every 10 ms (and on the 3 s heartbeat), so it
  can be exceeded by what is published in between (the Hub-level test asserts a peak of at most the total plus one broadcast's fan-out, 3,072 x 4 KB = 12 MB, and
  calls the shed after every broadcast; the real-socket test runs the shed as the server does). At 1 GiB with Campfire's frame sizes this is small, not zero.
- **Cuts take effect when the connection closes** (at most `CutGrace`, 1 s, for a client that is not reading). The shed counts a cut group
  as freed at once, which is true of the log; the socket's own buffers and the connection's pending batch (up to 64 frames, and a copy of
  what a partial send left) are per connection, outside the total and not multiplied by variants.
- **A group's fixed cost** (its chunk arrays, 4 KB, and a subscription's objects) is not counted in the total; 64 groups x K connections of
  it is not bounded by it. It is per connection and does not grow with traffic.
- **If readers alone hold more than the total**, the furthest-behind readers are cut. That is the bound doing its job, not a defect: it takes
  more than a gigabyte of unread frames.
- Frames are still copied once per identifier variant (option 3 above was not taken).
- Not logged in the climb chart: A/B arms of an unchanged hot path are not an improvement, and a shed that never runs is not measured by it.

`AGENTS.md` ("The hub's total") now describes the mechanism.
