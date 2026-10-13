# onCrack R4.3: the cost of fresh authorization, 2026-10-10

Round 3 made fresh authorization the default: a front-server replay re-reads the session, its user and (for a room page) the membership and the
room on every hit, and ran 15-18% below the cached decision. This unit makes that check cheaper without weakening it.

**Result.** A fresh check now costs about 2-2.7 µs of CPU less (the instruments below give 1.95 to 2.7), which is 7-10% of a room or messages page hit. Same build, setting alternating, in
one warm container (`bench/fresh-ab`, six rounds each, order flipped every round): room page **-7.7%** CPU per request (all six rounds
negative), messages page **-9.6%** (five of six). Tier 3 (full-length `bench/quick` reps of the rebuilt image, three per setting, interleaved
hold, nohold, nohold, hold, hold, nohold): the room page at c=16 goes from 117,232 to 127,344 requests/s (+8.6%) and 27.7 to 25.1 µs; the
messages page from 122,786 to 139,118 (+13%) and 26.0 to 23.3 µs. In the in-process harness the fresh path now sits within about 1.3 µs (5%)
of the cached decision (24.9-25.2 against 23.1-24.3 µs per answer, two processes each, cached first and last); the hold removed 2.6-3.1 µs per answer there, so the gap was about 4 µs. That sum is across runs, not one measurement.

Every hit still runs its query. Nothing is remembered between checks but the snapshot SQLite itself keeps, and the first check that starts after a commit
returned sees it, whichever connection made it.

## Where the fresh check's time went

`bench/breakdown perf` on the room page at c=16 (`perf-fresh/`, `perf-cached/`; fresh 30.2 µs unprofiled, cached 32.0 in a drifting host, so only the layers
are read): the check is 5.1 µs of a hit: SQLite 4.52, `Campfire.Db` 0.60. The statement itself is not the cost. `bench/db-micro`'s `fresh` scenarios (Linux,
hot loop) put a primary-key seek in a read transaction at 1.14-1.19 µs, `FreshAuth.replay` for session plus membership at 1.45-1.46 µs, and the same query in a
read transaction held open at 0.39 µs. `perf trace -s` on the micro: **two `fcntl` and one `fstat` per check**. Starting a read transaction in WAL mode takes a
shared lock on a read mark of the WAL index, an `fcntl` when no other connection of the process holds that mark at that moment (SQLite's unix VFS asks the
kernel only on the first holder), and gives it back at the end; `fstat` comes from an empty WAL, where the database size is the file's. The profile's
kernel share inside `Conn::step` (4.1%) and `Conn::finish` (2.2%) is those calls, and the libc share beside them is the VFS's mutexes.

## What changed

`Database.CheckNow` runs on `CheckerPool` (`src/Campfire.Db/Database.fs`): the connections of R3.2 in 16 slots with a compare-and-swap state in place of the bag
(a thread still gets back the slot it used last, more open on demand, never waits). After a check the connection keeps its read transaction open (a deferred
`BEGIN` before the query, no `COMMIT`), and the next check's query runs in it when `Versions.ChangeStamp` still reads what it read before that transaction
began. `ChangeStamp` is the WAL index header's change counter through the mapping the version watch already uses: every commit by any connection moves it by
one, and checkpoints, restarts, rollbacks and empty commits move it by nothing (`VersionsWatchTests` hold that). Unchanged means the snapshot is the whole database as it
is now; changed (or no WAL index) means `COMMIT`, `BEGIN` and a new snapshot before the query. The stamp is read before the snapshot is taken (a full fence between
them), so the worst a race costs is one needless new transaction.

A kept transaction pins the WAL, and the writer's RESTART waits for every reader of it. Three guards:
- Every check that leaves one open arms a 5 ms timer (only then, so an idle process has none) that ends the transactions that are stale or idle for 5 ms,
  and re-arms while any is kept and fresh.
- The writer calls `ReleaseHolds` before a RESTART (`Checkpoints.BeforeRestart`, both `RestartWal` and `TryRestartWal`): it ends every idle one at once and keeps checks
  from beginning one for 50 ms; a check running just then ends its own when it finishes.
- A failed check, a `BEGIN` that fails, a connection that cannot return to autocommit (closed and its slot freed), and disposing the database (waits for
  checks running, ends the transactions, closes the connections).

`CAMPFIRE_FRESH_HOLD=0` (or `off`, `false`) restores one transaction per check. `CAMPFIRE_FRESH_HOLD_FILE` is for benches: a file's `0` or `1` sets it within 20 ms,
inert when unset.

Not done, on purpose: remembering a check's answer under the change counter (or the version counters) and skipping the query while it holds. Upstream's contract
is a query on every hit ("Laravel checks membership afresh on every cache hit using a narrow existence query"); an answer kept under a stamp is the cached decision
of R3.2 with a database stamp, and R3.2 decided the headline must be the mode that re-reads. In doubt, I did not.

## Correctness

- `tests/Campfire.Db.Tests/CheckHoldTests.fs`, ten tests: the transaction is kept and reused; a commit by another connection and by the writer is seen by the very next
  check (50 rounds each); **a stress run (4 readers, 400 commits by another connection) fails if any check answers from before a commit that returned ahead of it**
  (readers read the published count first, then check); an idle and a stale transaction are let go without another check; `ReleaseHolds` leaves
  `wal_checkpoint(RESTART)` from another connection not busy and holds new ones off; the setting off keeps nothing; a failed check keeps nothing and the connection works after;
  disposing with a held transaction returns.
- **Mutation:** comparing the stamp for "held at all" instead of "unchanged" (a transaction never renewed) fails three tests (own commits, foreign commits, the stress run).
- `bin/verify Db App` passes (Db 223: 218 + 5 skipped; App 251: 250 + 1 skipped). `FreshAuthTests`, `ForeignWriteTests`, `FastPathTests` and `ReadCacheTests` (38) pass
  with the default, `CAMPFIRE_FRESH_AUTH=0`, `CAMPFIRE_FRESH_HOLD=0` and `CAMPFIRE_TEST_FRONT=1` (in process and fronted, both modes).
  Under the Mac's load (15-20 while other sessions built) whole-suite runs failed 1-6 timing and media tests (bcrypt rate limit, uploads, the bot api) in
  different configurations, each passing alone and in the next run; the targeted classes above are the ones that matter to this change.
- Reads beside writes (`bench/fresh-micro --post-rate`): at 10, 200 and as many as the connection can post a second, posts answered per window are the same in both
  settings, WAL restarts happen in both with the same longest (13 ms), and reads cost less with the hold (48.4 against 53.1 µs, 89 against 114, 280 against 326).
- Pixels were not re-run: nothing renders differently; the change decides how a check reads the database.

## Measurements

Host: the Mac was busy with other sessions throughout (load 2-6, sometimes 11-20; `bench/lib/hostprobe.py` ratio 1.05-1.25 at the quiet moments). Every figure is a same-session pair.

| Instrument | Room page | Messages page |
|---|---:|---:|
| `bench/fresh-ab`, one container, CPU per request, hold vs nohold, c=16 (`fresh-ab-*.txt`) | 25.65 vs 27.60 µs, -7.7% (6/6 rounds) | 29.95 vs 32.25 µs, -9.6% (5/6) |
| tier 3, image, 3 reps each, interleaved, req/s at c=16 | 127,344 vs 117,232, +8.6% | 139,118 vs 122,786, +13% |
| tier 3, CPU µs/request at c=16 | 25.1 vs 27.7 | 23.3 vs 26.0 |
| tier 3, req/s at c=1 | 19,723 vs 17,815, +11% | 20,178 vs 19,599, +3% |
| tier 3, CPU µs/request at c=1 | 26.5 vs 28.1 | 25.7 vs 26.8 |
| `fresh-micro`, in process, µs CPU per answer (includes clients) | 25.6 vs 28.2; 33.5 vs 36.6; 35.7 vs 43.1 | 20.7 vs 22.5 |

Tier 3 ranges are wide (room page nohold c=16: 93,794-130,583 requests/s) because each rep is its own container in a drifting host; the medians agree with the
paired instruments, which is why the pairs lead. Sequential single-rep `bench/quick cpu` runs (`q1-*.log`) swung 27.5-40.1 µs for the same setting and were not used.
The tier 3 table is `t3-table.py` over `t3-*.log`.

The cached decision, same harness: 23.1-24.3 µs per answer in `fresh-micro` against 24.9-25.2 with the hold (`micro-cached-vs-hold.txt`; the variant column
says `hold` in all four rows, because the cached rows ran with `CAMPFIRE_FRESH_AUTH=0`, where the setting does nothing).

Not re-run: the upstream harness session (R3.2's 5-way, `docs/performance-review.md`'s method). Fresh mode's multiple over current Rust (2.6x) and C (1.85x), stated in
`oncrack-r3-final.md`, is therefore not updated here; the same-session instruments say fresh hits cost 7-10% less CPU than when it was measured. A new multiple needs a
session on a quiet Mac with all five apps.

## Files

- `bench/results/oncrack-r4-fresh/`: `perf-fresh/`, `perf-cached/` (breakdown perf), `fresh-ab-room.txt`, `fresh-ab-messages.txt`, `fresh-micro-runs.txt`,
  `micro-cached-vs-hold.txt`, `t3/` and `t3-*.log` with `tier3.sh` and `t3-table.py`, `q1*` (discarded), `ab.sh` and `ab-quick.sh` (helpers).
- Tools added: `bench/fresh-micro`, `bench/fresh-ab`, `fresh` scenarios in `bench/db-micro` (`DB_MICRO_ONLY`, `DB_MICRO_WAL`).

## Deferred

- A pinned statement per check shape on each checker connection (no statement-cache lookups, no `SqlArg` array, no closure): with the hold the check is about
  0.4 µs of a 25 µs hit, so the ceiling is a percent or two; not tried.
- The app path's `FreshAuth.membership` (a room or messages page hit that does not go through the front server's replay) still runs on a pooled reader in a
  transaction of its own. The same hold would apply on a reader dedicated to it; the replay is the hit path in upstream's harness, so it was left.
- A session in upstream's harness (all five apps) to restate the multiples against Rust and C.
- Logging this unit in `oncrack-log.jsonl`: rounds 3 and 4.2 did not either, and the file holds the cached-decision numbers.
