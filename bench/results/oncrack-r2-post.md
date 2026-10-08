# onCrack R2.2: posting, 2026-10-08

Area 2 of round 2: cut the work a post does, keeping Rails' durability (WAL, `synchronous=normal`, every post committed before
it is answered). Nine commits on `crack` (`564a162` to `eae5beb`), image `campfire-oncrack:app` `sha256:12969a1861f3`, label
`eae5beb`. `campfire-fsharp:app` (the port) untouched.

- Raw data: [`oncrack-r2-post/`](oncrack-r2-post/). `tier3/` (posts, 3 reps), `tier3-real/` (mixed and spread_mixed, 3 reps),
  `tier3-paced500/` (mixed at 500 posts/s: onCrack 3 reps, the port and Rust 1 rep, one session), `tier3-reads/` (the read
  regression check), `t2-*` (every tier 2 run, logged), `perf-c16*/` (perf breakdowns).
- Rust and the port are scored by round 1's same-session medians (`oncrack-round1-final/`) for the classic post, and by R2.0's
  same-session baseline (`oncrack-r2-bench/`) for the realistic workloads.

**Verdict**

- **Posting at one connection:** 4,626 posts/s, 391 us of CPU a post. Round 1: 3,395 and 585. **1.68x Rust, 1.52x the port**, and
  for the first time onCrack's CPU per post at c=1 is below Rust's (0.96x; it was 1.43x).
- **At 64 connections:** 18,461 posts/s, 154 us. Round 1: 17,684 and 187. **4.14x Rust, 3.47x the port**, CPU 0.40x Rust.
- **At 16 connections the rate went down, not up:** 12,010 [10,030-12,163] against round 1's 13,215, though CPU per post fell
  from 230 to 185 us. Every rep has one 0.9-1.0 s stall in its 8 s window, and the warm-up never settled: the writer's WAL RESTART
  checkpoint, which onCrack's faster posting now reaches every 20-30 s (below). Between stalls the rate is 15-16k. Still **1.70x Rust
  and 1.37x the port**, with CPU 0.48x Rust. This is the open item of this unit.
- **Posting into rooms of 526 members (`spread_mixed`):** 753 posts/s against 337. **2.36x Rust and 1.91x the port**; it was 0.86x
  the port. R2.0's open question had a simple answer: every post rewrote 524 membership rows, each firing two managed trigger calls.
- **Reads while writing:**
  - At the same rate of posts (500/s, the new `POST_RATE`), onCrack reads 91,322 req/s: **4.40x Rust, 3.14x the port** (one
    session). The R2.1 image read 84,907 in the same configuration (tier 2): the cheaper post leaves more for the reads.
  - In the closed-loop `mixed` (one connection posting as fast as it is answered), onCrack's posts went from 1,079 to 1,424 a
    second (+32%) and its reads from 43,283 to 34,805 (-20%). Each post invalidates the read room, so a faster poster costs the
    readers more misses. Still 1.87x Rust and 1.44x the port on reads, 2.07x and 1.89x on posts. This is a trade, not a gain, and
    is reported as one.
- **Nothing else moved:** room page 124,996 and sidebar 137,768 req/s at c=16 (round 1: 123,942 and 138,182).
- **The run is sound:** every response 2xx with 0 connection errors; post rows written equal the 2xx answers in every phase; decoded
  bytes equal Rust's on every probed route. `bin/verify` passes (1,102 tests, 1,095 passed, 7 skipped). `bin/kit-differential http`:
  3,000 requests, 0 differ. Pixel parity on the states a post can change (`realtime/**`, `interactions/sidebar/**`, default seed):
  116/116 screenshots pixel-equal to Rails'.

## Where a post's time went

A tier 1 harness came first, because nothing measured a post end to end in seconds. **`bench/post-micro`** boots the whole app in
process (its own front server on loopback) over a copy of a parity seed, signs posters in, and runs N keep-alive connections posting
into a room. It alternates windows between variants of `Campfire.Db.PostPath`'s runtime switches in one warm process and prints
posts/s, process CPU and bytes allocated per post, answers over 100 ms, and the writer's WAL restarts. A two-variant comparison at
two concurrencies takes about 40 s; the tier 2 loop it replaces (`bin/publish-mounted` and `bench/quick`) takes 2-3 minutes a
variant. It runs on macOS, so it gives direction; every kept change was then measured at tier 2 in the VM.

What it found (macOS, CPU per post including the in-process clients):

| Room | c=1 | c=16 | allocation | note |
|---|---|---|---|---|
| All Talk (3 members) | 575 us, 3,627/s | 545 us, 14,301/s | 141 KB | the classic workload's shape |
| HQ, crowd seed (524 members) | 1,450 us, 1,065/s | 1,634 us, 1,788/s | 669 KB | the writer saturated at c=16 |

A thread-time trace (`dotnet-trace`) of the HQ case put 87% of the writer thread in `Room.receive`: the unread-marks `UPDATE` of
524 rows, each row firing the read cache's `memberships_u` trigger, which calls `campfire_bump` twice through
Microsoft.Data.Sqlite's managed callback. A database micro-benchmark of that statement alone: 790 us with the triggers, 546 us
without them, 73 us when only rows not yet unread are written.

In the VM (`bench/breakdown perf`, c=16, classic seed), after the first changes: SQLite reads 40 us, gzip 30 us, the writer's SQLite
29 us, runtime 18, Campfire.Db 18, Kestrel 16, allocation 19, rich text 10 of 217 us.

## What changed, one at a time

Every change has a switch, on by default; none touches durability.

| Change | Switch | Tier 2 (VM) | Why it is correct |
|---|---|---|---|
| **Unread marks only where the state changes.** Outside direct rooms a post writes `unread_at` only on memberships not yet unread. | `CAMPFIRE_POST_UNREAD_SKIP` | `spread_mixed` posts 343 -> 733/s; HQ in process 1,765 -> 6,205 posts/s at c=16 | `unread_at` is only ever read for being set (`Membership#unread?`, the `unread` scope, the push badge). `updated_at` keys only the direct rooms' sidebar fragment (`cache membership`), so direct rooms still rewrite every row, as Rails does. |
| **The unread pings pluck member ids**, and stream names are made once per user. | none | HQ in process: 1,057 -> 771 us, 438 -> 172 KB a post | The same ids, the same streams. |
| **A post's search-index row and unread marks commit with the post** (`Tx.OnCommit`), after every write of a group, with no savepoint. | `CAMPFIRE_POST_ON_COMMIT` | in process, c=16 +4.7% | One commit per post (per group) instead of two or three. A failing statement of it rolls back alone and its error reaches the caller after the write committed, as Rails raises it from the save. A savepoint per hook made FTS5 flush a segment per post and halved c=16 in the first try, so there is none. |
| **A write runs on its caller's thread** when the writer is idle, nothing is queued, and it is the only request in flight that may write (`WriteLoad`). | `CAMPFIRE_WRITE_INLINE` | c=1 3,503 -> 4,310/s, CPU 576 -> 441 us | Same group-of-one path as the writer thread, the connection owned by one thread at a time (`TryTakeInline`). Ungated, c=16 fell from 15,571 to 9,837 (writes queued behind an inline one waited for the writer thread to wake), hence the gate. A request's thread never runs the WAL RESTART: it sends the writer thread round with an empty write. |
| **The search index's text is worked out before the write**, in the read that canonicalizes the body. | `CAMPFIRE_POST_PLAIN_TEXT_EARLY` | in process, c=16 +4.6% | The same stored body, the same resolver; a test compares it with `plainTextBody` for formatted, listed and blank bodies. Off the single writer. |
| **The push job reads on its own thread** when a reader connection is free (`Database.Read`, not always `ReadOffloaded`). | `CAMPFIRE_PUSH_INLINE` | CPU c=1 477 -> 412 us, c=16 215 -> 198 | The notifications are encrypted when the pool delivers them (as in Rails' pool), so the read is a handful of queries. |
| **libdeflate for whole bodies**, a compressor per thread. | `CAMPFIRE_GZIP_LIBDEFLATE` | c=1 446 -> 432 us | Same header and trailer; other deflate bytes, the same body when inflated. |
| **A POST's answer is gzipped once at level 1** and kept out of the digest-keyed gzip cache. | `CAMPFIRE_GZIP_ONCE_LEVEL` (1) | CPU c=1 403 -> 379, c=16 193 -> 181, c=64 164 -> 152 us | Rack::ETag digests every 200 body, a POST's too, so every answer was compressed at level 6 and kept, though none is sent twice. **Disclosed:** the answer is 2,096 bytes on the wire instead of 1,987 (+5%). Kept bodies (frozen pages, GET answers) stay at level 6. |

Rejected after measuring: a quiet trigger with a `WHEN` subquery (731 us against 798: the per-row subquery costs most of what the
callbacks did); bounding the RESTART's wait for readers to 50 ms, and skipping it while the checkpointer runs (the restarts still
took 0.3-2.4 s; neither kept).

"Render the answer and broadcast once" was already the case (C2): the answer reuses the broadcast's fragment. The broadcast's
member read is the part that grew with the room, and it is now an id pluck.

## The c=16 stall (open)

With `LOG_REQUESTS=false` the container logs `WARN campfire_db: WAL restart took N ms` (new, past 100 ms): 0.8-2.5 s, every 20-30 s at
c=16. The writer runs a RESTART checkpoint whenever the WAL reaches 10,000 pages, and every write waits for it.

- In process on macOS the same posting makes 5-6 restarts a second, each under 10 ms; in the VM they take seconds.
- It is the copy and sync, not waiting for readers: bounding that wait to 50 ms changed nothing.
- The R2.1 source, mounted and run on the same schedule, had one 348 ms stall. onCrack's faster posting reaches the limit more often.
- c=64 does not stall in any rep (larger groups, fewer commits, less WAL per post).
- Turning off inline writes or on-commit work does not remove it (bisected at tier 2).

The fix belongs to the WAL policy, not the post path: fewer WAL pages per commit (FTS5's merge work is the likely bulk), or a restart
that does not hold the writer. Deferred, below.

## The numbers

Tier 3, the rebuilt image, 3 reps, `bench/quick`'s warm-up (30-90 s until flat), `SERVER_CPUS=0-3 LOADGEN_CPUS=4-7`.

| Workload | c | onCrack R2.2 | round 1 onCrack | **/ Rust** | **/ port** | CPU us | round 1 CPU | Rust CPU | port CPU |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 1 | 4,626 [4,565-4,684] | 3,395 | **1.68x** | **1.52x** | 390.8 | 585.2 | 408.7 | 636.0 |
| post a message | 16 | 12,010 [10,030-12,163] | 13,215 | **1.70x** | **1.37x** | 185.2 | 230.0 | 388.1 | 354.8 |
| post a message | 64 | 18,461 [18,272-18,730] | 17,684 | **4.14x** | **3.47x** | 154.2 | 186.6 | 387.0 | 339.8 |

Rust and the port: round 1's same-session medians (Rust 2,759 / 7,082 / 4,459; the port 3,034 / 8,780 / 5,324).
`bench/quick compare` against phase7-final's stored medians gives 1.66x Rust and 1.52x the port at c=1, 1.67x and 1.35x at c=16.

Latency at c=16: p50 0.89 ms, p99 4.8 ms, max 0.86-1.0 s (round 1: 1.03 / 5.34 ms). At c=1: p50 0.19 ms, p99 0.37-0.39 ms.

| Workload | lane | onCrack R2.2 | R2.0 onCrack | Rust | F# port | **/ Rust** | **/ port** | CPU us/req |
|---|---|---|---|---|---|---|---|---|
| mixed | posts | 1,424 [1,410-1,430] | 1,079 | 688 | 753 | **2.07x** | **1.89x** | 103.9 (was 84.3) |
| mixed | reads | 34,805 [34,752-34,876] | 43,283 | 18,597 | 24,232 | **1.87x** | **1.44x** | |
| spread_mixed | posts | 753 [743-758] | 337 | 319 | 393 | **2.36x** | **1.91x** | 279.5 (was 284.3) |
| spread_mixed | reads | 13,129 [12,940-13,141] | 13,229 | 13,155 | 13,584 | **1.00x** | **0.97x** | |

Mixed at a fixed 500 posts/s (`POST_RATE=500`, one session; onCrack 3 reps, Rust and the port 1 rep each):

| | Rust | F# port | onCrack | **/ Rust** | **/ port** |
|---|---|---|---|---|---|
| reads/s | 20,742 | 29,127 | 91,322 [89,669-92,552] | **4.40x** | **3.14x** |
| read p50 / p99 ms | 0.73 / 1.68 | 0.44 / 1.32 | 0.11 / 0.81 | | |
| post p50 / p99 ms | 1.39 / 2.53 | 1.25 / 3.22 | 0.72 / 1.76 | | |
| CPU us/req | 161.6 | 124.7 | 39.8 | 0.25x | 0.32x |

At tier 2 the R2.1 image read 84,907 and the first kept build 88,444 in this configuration (one rep each).

## Correctness

- **Attack tests** (`tests/Campfire.App.Tests/PostPathTests.fs`, `tests/Campfire.Db.Tests/GroupCommitTests.fs`):
  - a post marks unread who wasn't and leaves who was (row and `updated_at` untouched), and Jason's cached sidebar shows HQ unread
    on his next request after each post, read after his membership is read, unread again after the next post, with that post's
    time; the poster is never marked;
  - in a direct room every other member's row is still rewritten on each post (the sidebar fragment's key moves);
  - the search index's text worked out before the write equals `Message.plainTextBody`, and search finds a post at once;
  - on-commit work commits with its write; a failing statement of it reaches its caller alone, the write committed, alone and in
    a group (after every write of the group, in order);
  - 16 callers x 50 writes on their own threads never share the writer connection and keep each caller's order, and with two
    writing requests in flight nothing runs inline. A sabotaged `TryTakeInline` (no ownership check) fails it and four group tests.
  - gzip: whole members inflate to their bodies from 1 B to 300 KB, random and repetitive, at both levels, with the same header
    and trailer.
- The C2 oracle (24 posts as one group leave exactly the database 24 posts one by one leave) passes with on-commit work.
- `bin/verify`: 1,102 tests, 1,095 passed, 7 skipped (the 7 that skipped before). `bin/kit-differential http`: 0 of 3,000 differ.
- `bin/pixel-parity --seeds default --only 'realtime/**,interactions/sidebar/**'` on the candidate image built with `eae5beb`:
  116/116 pixel-equal (every engine and viewport of the lean matrix for those 17 states, the unread and new-ping sidebar states
  among them); summary in [`oncrack-r2-post/pixel-parity.json`](oncrack-r2-post/pixel-parity.json). The full gate on every seed is
  the round verifier's.
- One defensive change came after the image (`c48baef`: an inline write never answered returns `WriterGone`); not measured.
- Not run: `bin/db-differential`. Two posts into an open room leave `unread_at` at the first post's time where Rails writes the
  second's (a deliberate difference, `PostPath.UnreadSkip`; Rails reads the column only for being set, so a rollback to Rails reads
  the same state). The full pixel gate is the round verifier's.

## Logging

Every tier 2 and tier 3 run is in `oncrack-log.jsonl` under unit `r2-post`, kept or not, except the three paced runs: logged under
their builds' commits they would replace those dots' closed-loop `mixed` values on the climb chart (as R2.0 kept its controls out).

## Deferred

1. **The c=16 WAL restart stall** (above): cut WAL pages per commit (FTS5 automerge settings, or the hot pages each post rewrites),
   or restart the WAL without holding the writer. Until then the c=16 post median carries a 1 s stall per window.
2. **Misses after an invalidation stampede.** In `mixed` every post makes up to 16 readers render the same page at once. A
   single-flight render per key would turn those into one render and 15 waits; that is what would give the closed-loop reads back.
3. **The push job repeats the post's work**: the body's plain text (parsed again), the room and the creator. Handing it what the post
   already has saves a parse and three reads.
4. **A fresh message's presenter reads boosts and the attachment** that a just-created message cannot have.
5. **Thread pool spinning** is still most of the remaining c=1 CPU (in process, spin limit 0 takes a post from 557 to 337 us), but it
   is a process-wide setting that cost the read pages before (Dockerfile notes); not changed here.
6. Gzip of digested GET misses (the `spread` workload's) at level 6 could take the faster level too; not measured here.
