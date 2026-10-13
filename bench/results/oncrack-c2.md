# onCrack unit C2: posting at scale

Date 2026-10-07, branch `crack`, commits `d3a7a23` (group commit), `af9d66c` (one read after a post), `25ea87e` (broadcast encoded only
for subscribers), `0f3e120` (an HTTP test of concurrent posts). Image `campfire-oncrack:app` `sha256:56c3c35f8fd5`, label
`revision=0f3e120`; `campfire-fsharp:app` (the port) untouched. Every number below is onCrack's, scored against the stored medians of
`phase7-final` (Rust and the F# port in one session; not re-measured here), never a like-for-like port result.

## What changed

**Group commit** (`src/Campfire.Db/Database.fs`, module `Writer`). The writer takes every write already queued (up to 64,
`CAMPFIRE_GROUP_COMMIT_MAX`) and runs them in one `BEGIN IMMEDIATE` transaction, each in a savepoint of its own, with one `COMMIT`; then
the group's after-commit work (a post's search-index row and its members' unread marks) in the writes' order, in one more transaction;
then those hooks' events (the push job); then the read cache's versions are released; then every caller is answered, in queue order.
There is no waiting: a group is what queued while the writer was busy with the last one, so at c=1 every group is one write and runs
exactly as the port's writer does.

- **Durability is unchanged and Rails-equivalent.** Every post is committed (WAL, `synchronous=normal`, the reference's setting, which the
  port already used) before its response is written. Nothing is answered from an uncommitted group. Rails' durability already doesn't
  fsync per commit (the WAL is synced at checkpoints), so there was no per-post WAL sync to share. What group commit shares is the
  commit itself: the WAL frames for the pages a post touches (messages, rich texts, the FTS segments, the room, memberships) are written
  once per group instead of three times per post (the port's post commits its transaction, then the index row and the unread update each
  autocommit), and the readers' page caches, which SQLite drops whenever the database changed, are dropped once per group.
- **Failure isolation.** A write that fails rolls back to its savepoint alone; its caller gets its error or exception, the rest commit.
  Anything that breaks the group's transaction itself (a failing `COMMIT` or savepoint, an error after which SQLite has rolled the whole
  transaction back) leaves nothing committed, and the group runs again write by write, exactly as the port runs writes. Write closures do
  database work only (a non-database effect belongs in an after-commit hook), which is what makes running one again safe; that was already
  true of every closure in the code. The same holds for the after-commit transaction (it reruns as autocommitted hooks).
- **What differs from writes run alone, by design:** the group's after-commit work commits together rather than statement by statement
  (a failed statement still rolls back alone: SQLite rolls back a statement, not its transaction, on a constraint error), and its events go
  out after that commit rather than between hooks. `tx.Now()` inside a hook is read after the whole group ran, so an `updated_at` a hook
  writes can be a few microseconds later than it would have been; nothing compares it.
- **Settings:** `CAMPFIRE_GROUP_COMMIT=off` (one write per transaction, the port's writer), `CAMPFIRE_GROUP_COMMIT_MAX` (64),
  `CAMPFIRE_GROUP_COMMIT_WINDOW_US` (0: the writer may wait that long for a group to fill; measured below, slower, off by default; it
  never weakens durability, only adds latency).

**One read after a post** (`src/Campfire.App/Controllers/Messages.fs`). The port's `messages#create` read three times after its write
(the broadcast's render and the members for the unread pings; the bots for webhooks; the answer's render), each a read transaction on a
reader whose page cache the write had just invalidated, and the account twice. Now one read does all three, keeping the order of side
effects (broadcast, then the webhook jobs' write, then the answer) and taking the answer's message partial from the fragment cache the
broadcast's render filled, as before.

**Broadcast encoded only when heard** (`src/Campfire.App/Channels/Broadcasts.fs`, `Hub.HasSubscribers`). `broadcast_create` escaped the
~20 KB message partial into a JSON string for the room's stream whether or not anyone was subscribed; now it asks the hub first. A
subscriber that joins after that answer misses the broadcast exactly as it would one sent a moment earlier, and with debug logging on
every broadcast is still made and logged. **Disclosed:** the benchmark's post workload has no Cable subscribers, so this saving shows
there in full; a room with people in it pays the encoding as before (about 14 µs of CPU per post at c=16, tier 2 below).

**Precomputation asked for and already there:** the message partial is rendered once per post (the answer reuses the broadcast's fragment),
and the unread ping's `{"roomId":n}` is encoded once for every member's stream (the port did both). The broadcast payload is encoded once
per stream, not per subscriber (the hub frames it once per group of subscribers).

## Tests that try to break it

`tests/Campfire.Db.Tests/GroupCommitTests.fs` (9). The tests hold the writer on a blocking write so that the writes queued behind it are one
group (the writer's statistics confirm the group's size), then check:

- 20 writes in one group return their own values in order, each seeing the rows of those before it;
- a write that fails (a UNIQUE violation after an insert, a `RecordNotFound` after an insert) rolls back alone, its caller alone gets the
  error, the writes after it commit; a write that raises a bug gets its exception and the rest commit;
- a write that ends the transaction under the writer (`ROLLBACK` in the closure) makes the group run again write by write: every other
  write is committed exactly once (the first ran twice, committed once), the culprit fails alone;
- after-commit hooks run after the group committed (a fresh connection inside each hook sees all 8 rows), in the writes' order, and the
  events come out in each write's order, its own then its hook's;
- a failing hook reaches its own caller, after its write committed (as Rails raises it from the save that committed);
- 16 concurrent writers, 40 writes each: every write is visible to a fresh connection the moment its caller hears back (640 of 640);
- read-cache versions are odd inside the group and even, and moved, when the callers hear back;
- **the oracle:** 24 posts in three rooms by three users, run as one group, leave exactly the same messages, rich texts, memberships
  (unread marks), rooms (touches), search index and events as the same posts run one by one with `GroupMax = 1` (frozen clock, same
  fixtures). A sabotage check (the savepoint rollback removed) fails two of these tests.

`tests/Campfire.App.Tests/ReadCacheTests.fs`, new: 16 browsers post 6 messages each at once over HTTP (in a run: 113 writes in 23 groups,
the largest 15): every answer is 200 and carries its own message and no one else's, each message is stored once, each poster's messages
were committed in the order it sent them, the room page shows the last. The C1 read-cache tests (posts, edits, deletes, bans, racing
readers) all run with group commit on, and the whole App suite also passes with `CAMPFIRE_GROUP_COMMIT=off`.

`bin/verify`: 1,063 tests, 1,056 passed, 7 skipped, 0 failed. Not run: `bin/pixel-parity` (the answers' bytes are unchanged: `bench/run`'s
probe finds decoded bytes equal to Rust's on every probed route in every run), `bin/db-differential` (the rows are the same as one-by-one
posts, which the oracle test shows, but the reference comparison was not re-run), the other differentials.

**One unexplained failure.** In one full App run (of about 40 full runs and 40 runs of the read-cache class), `a ban signs the user out
and takes their messages off every cached page` got an empty room page right after a direct-to-database post. It never recurred; the
test now reports the status, size and redirect of what it got, so a recurrence says what happened. Recorded as open, not explained.

## Measurements

Tier 2 (mounted builds, one rep each, post a message only; `oncrack-c2/t2-*`, all logged):

| Build | c=1 req/s (CPU µs) | c=16 req/s (CPU µs) | c=64 req/s (CPU µs) |
|---|---|---|---|
| `d3a7a23`, `CAMPFIRE_GROUP_COMMIT=off` (= C1) | 2,917 (655) | 8,631 (362) | 6,103 (348) |
| `d3a7a23`, group commit | 2,984 (639) | 11,947 (257) | 14,692 (215) |
| `af9d66c`, + one read after a post | | 12,439 (248) | 16,460 (202) |
| `25ea87e`, + broadcast only when heard | | 12,963 (234) | 17,934 (186) |
| `25ea87e` + `CAMPFIRE_GROUP_COMMIT_WINDOW_US=200` (not kept) | 1,870 (839) | 10,946 (251) | 16,172 (194) |
| `25ea87e` + readers `mmap_size=256MB` (not kept, reverted) | | 12,671 (246) | 16,595 (194) |

Where the CPU went (perf, `oncrack-c2/perf-*`, per post): the writer thread 74 µs at C1 → 40 µs grouped at c=16 → 32 µs at c=64; the
reader threads 104 → 85 → 65 µs; kernel time 96 → 45 → 27 µs (WAL writes and the readers re-reading pages). At C1 c=64 was *slower* than c=16
(6.1k against 8.6k) at the same CPU per post with only 2.1 of 4 cores busy: posts queued on the one writer. Grouped, c=64 uses 3.2 cores and
is the fastest. A commit window only adds latency here (c=1 pays the whole window per post; at c=16 and c=64 the queue already fills
groups), so it stays off. A larger `synchronous` relaxation has nothing to give: commits at Rails' `normal` already don't sync.

Tier 3 (the rebuilt image, all five workloads at c=1 and c=16, 3 reps, warm-up until flat, plus post at c=64, 3 reps; every response 2xx with
0 connection errors in all 33 runs, decoded bytes equal Rust's on every probed route, post rows equal the 2xx answers in every phase). Raw:
`oncrack-c2/tier3/` and `oncrack-c2/tier3-c64/` (`report.md`, `vs-stored.md`):

| Workload | c | onCrack req/s | / F# port | / Rust | CPU µs/req | port | Rust |
|---|---|---|---|---|---|---|---|
| post a message | 64 | 17,865 [17,666-17,995] | **3.03x** | **3.71x** | 187 | 341 | 389 |
| post a message | 16 | 12,953 [12,572-12,983] | **1.46x** | **1.81x** | 236.7 | 353.0 | 385.6 |
| post a message | 1 | 3,123 [3,023-3,176] | **1.02x** | **1.12x** | 622.4 | 629.1 | 403.7 |
| room page | 16 | 98,146 | 2.43x | 3.43x | 31.8 | 93.6 | 122.4 |
| room page | 1 | 11,821 | 1.55x | 1.82x | 151.7 | 208.7 | 142.1 |
| messages page | 16 | 101,732 | 2.69x | 3.38x | 30.3 | 102.2 | 114.2 |
| messages page | 1 | 12,527 | 1.51x | 1.84x | 148.4 | 199.3 | 139.2 |
| sidebar | 16 | 108,132 | 2.88x | 3.83x | 27.2 | 101.8 | 123.2 |
| sidebar | 1 | 13,491 | 1.69x | 2.18x | 138.0 | 181.0 | 149.0 |
| search | 16 | 74,061 | 2.17x | 2.78x | 31.2 | 107.3 | 123.9 |
| search | 1 | 12,595 | 2.08x | 2.23x | 145.2 | 315.1 | 158.3 |

Posts against C1's tier 3: c=16 8,631 → 12,953 req/s (+50%), 357 → 237 µs CPU per post; c=1 3,026 → 3,123 (within noise: a post at c=1
is a group of one); c=64 (not measured at C1; the stored port is 5,888) 17,865. Geometric means of the five: c=16 **2.95x Rust, 2.26x the
port** (C1: 2.75x, 2.11x); c=1 **1.79x Rust, 1.53x the port** (C1: 1.78x, 1.52x). The read pages are unchanged by this unit; room page c=16
is 4.5% under C1's (98.1k against 102.7k) and one sidebar c=16 rep read 75k (the other two 108-109k): noise on paths this unit doesn't touch,
not investigated further. Warm-up hit its 90 s maximum on room, messages and sidebar at c=16 (flat afterwards, as in C1).

Is the post number too good? It is the commit count: three commits per post became two per group (the group sizes in the benchmark were
not recorded; the in-process HTTP test saw 113 writes in 23 groups at 16 posters), and the perf split above moves where it should (writer, readers' SQLite, kernel), while everything above the database (HTTP, auth, rich
text, rendering, gzip at ~31 µs) is where it was. Each response is still a post's own committed message (rows counted against 2xx answers in
every run).

## Deferred

- `bin/pixel-parity`, `bin/db-differential` on this build.
- A durability option *stronger* than Rails (`synchronous=full`, an fsync per commit), where group commit would share each fsync: not
  built or measured.
- What remains in a post at c=16 (234 µs): readers' SQLite (setRoom, the post-write read, the push job: three read transactions, each on a
  freshly invalidated page cache), gzip of the answer (~31 µs), HTTP and the runtime. The push job's read could share the post's read.
- The one unexplained read-cache test failure (above).
- `bench/quick compare` does not print c=64 (the c=64 ratios above are computed by hand from `phase7-final/report.md`), and `bench/quick log`
  stamps a tier 3 run as `mounted` unless given `--build` (the two tier 3 lines were corrected by hand to the image digest).
