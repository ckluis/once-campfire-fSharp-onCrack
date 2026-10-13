# R4.4: WAL volume per post

Round 4, unit 4. R3.4 traced the c=16 post stall to the VM's disk under 250-300 MB/s of WAL and named fewer frames per post as the lever.
This unit measured what a post writes, what cuts it, and whether cutting it buys throughput. Scripts: [`oncrack-r4-wal/`](oncrack-r4-wal/). The `wal-ab` tables below are copied from its output; the raw traces are not kept.

**Result, plainly:** nothing shipped as a new default, because nothing that cut the bytes also kept the throughput.
- A group window halves the WAL bytes per post (c=16: 17.8 to 9.5 KB) and costs 25% of the posts per second at c=16 and 7.5% at c=64 (alternating windows, quiet host).
- Halving the bytes did not lift sustained c=16 throughput either: in 30 s windows after a 90 s warm-up the windowed variant was no faster (median 9,637 against 11,103), so the stall is not simply a function of WAL volume.
- FTS5 `automerge=16` cut frames per post 12-16% in the in-process micro and 9% offline, but 0% to 5% in the container (below the spread between windows). It stays an opt-in.
- The tools came out: the writer now counts the WAL frames its commits append, `bench/wal-ab` alternates a setting by window in one container and prints frames and bytes per post for each window, and `replay.py` attributes a commit's frames to b-trees without concurrency.

No default code path changed: four atomic adds per group (the stats) and the frame count the writer already read after each group. The upstream harness, the mixed profile and the search parity states were not re-run for that reason (nothing they exercise changed); `bin/verify`: 1,162 tests, 0 failed on the last of three tries (see Verification).

## What a post writes

`oncrack-r4-wal/replay.py` replays the post path's SQL (a group of K posts in savepoints, the index rows after them, one COMMIT) against a copy of the crowd seed
and names each frame's b-tree. At K=5, 18.4 frames a commit (3.7 a post):

| b-tree | frames a commit | |
|---|---|---|
| FTS5 data (new segment, structure and averages records, interior pages) | 4.2 | |
| FTS5 content, docsize, idx | 1.1, 1.0, 1.0 | FTS5 in all: 7.3, 40% |
| `index_messages_on_room_id_and_created_at` (onCrack's addition) | 1.8 | 10% |
| rich text uniqueness index | 1.6 | |
| rich texts, `messages` | 1.3, 1.25 | |
| `index_messages_on_creator_id`, `index_messages_on_room_id` | 1.3, 1.3 | |
| `sqlite_sequence`, `rooms` (the touch) | 1.0, 1.0 | counters and a timestamp |
| page 1 (database size changes) | 0.4 | |

Each tree takes its right-edge page whatever the group's size, plus about a quarter more for splits. So a commit costs a nearly fixed ~18 pages and
frames per post is about 18 / writes per group. The container's groups: 4.4-4.5 writes at c=16, 14-15 at c=64, which is 4.4 and 1.75 frames a post.
Nothing in the fixed part can be dropped without changing the schema (`sqlite_sequence` is AUTOINCREMENT's, `rooms.updated_at` is the touch, the
indexes are Rails' or the room-page index R2 added), or the data Rails reads.

## Group window

`CAMPFIRE_GROUP_COMMIT_WINDOW_US` already existed (the writer waits that long for more writes to join a group; C2 measured it slower at 200 us and left it off).
`bench/wal-ab` alternates it by window in one warm container (`PostPath` switch `group_window_us`, flipped through a control file within 20 ms), 8 s windows,
order flipping each round, 40 s warm-up, host load 2-4:

| c | variant | posts/s by window (median) | frames/post | KB/post | WAL MB/s | us CPU/post |
|---|---|---|---|---|---|---|
| 16 | no window | 14,910 14,666 15,092 15,321 (**15,001**) | 4.25-4.48 | 17.1-18.0 | 264-282 | 189 |
| 16 | 300 us | 11,209 11,040 11,239 11,340 (**11,224**) | 2.33-2.40 | 9.4-9.6 | 108-111 | 211 |
| 64 | no window | 16,264 17,313 17,156 16,611 (**16,884**) | 1.74-1.79 | 7.0-7.2 | 118-127 | 171 |
| 64 | 300 us | 16,127 16,206 15,100 15,097 (**15,614**) | 1.29-1.40 | 5.2-5.6 | 83-87 | 187 |

The window raises writes per group (4.5 to 11 at c=16, 15 to 24.5 at c=64) and the post waits for it: at c=16 the system is latency bound (2.2 of 4 cores
busy), so a longer wait is a slower post. At c=64 the writer is not the bottleneck either, and the extra wait is a smaller loss.

Long windows (c=16, 90 s warm-up, 30 s windows, 3 rounds, host load 3-4): no window 10,479 / 12,024 / 11,103 posts/s at 194-223 MB/s;
300 us 10,883 / 9,272 / 9,637 at 99-108 MB/s. Half the bytes, no faster, so on this evidence the stall is not what limits the windowed variant or the plain one.

Single, non-alternating tier 2 reps taken earlier on a busy host (load 5-6) read the other way at c=64 (12,994 plain; 15,015 at 100 us; 16,687 at 300 us) and
lost at c=16 (10,966; 10,351; 9,403): host drift. The alternating windows above are the ones to believe; the single reps were traced runs of `trace-run.sh` (raw files not kept).

No adaptive rule was found: CPU saturation does not tell where a window pays (c=64 is the saturated case and still loses 7.5%), and a rule keyed to writes
in flight is the same as a rule keyed to c. A window keyed to a slow disk (while the checkpointer's `Healthy` is false) is the untested candidate.

## FTS5 automerge

FTS5 stores `automerge` (default 4) in the index's `%_config` table; every connection that opens the table reads it, Rails' included, and it changes how
segments merge, never what a search finds. A merge of a few tiny segments rewrites a handful of pages whatever their size, and with a segment per commit
that is one merge event for every four commits.

| Where | automerge 4 | automerge 16 (0 is the same: levels still merge at `crisismerge`, 16) |
|---|---|---|
| offline replay, K=4, 6,000 commits (`replay.py`) | 4.735 frames/post | 4.292 (-9%) |
| in-process micro, crowd seed, c=16 (`bench/post-micro --fts`) | 3.56-3.67 | 3.05-3.13 (-12..-16%) |
| container, default seed, 8 windows each (`wal-ab`, `CAMPFIRE_FTS_AUTOMERGE`) | 4.28-4.52, mean 4.41 | 4.44-4.68, mean 4.52 |
| container, crowd seed, 8 windows each | 3.44-3.84, mean 3.61 | 3.23-3.63, mean 3.43 (-5%) |

The container does not show the micro's gain. I did not find why (the mid-run b-tree breakdown in the container is the next measurement; `wal-ab`'s `KEEP`
copy came after a restart, 32 frames). Fewer merges also leave up to 15 segments a level to search, against 3. So no default: `CAMPFIRE_FTS_AUTOMERGE=N`
(0-16; unset leaves what the database holds) stores it at start (`Schema.setFtsAutomerge`), and a test holds search results equal before and after
changing it. Not run: `bin/db-differential` with it set, since the default does not touch the database.

## Rejected

- **Deferring the index row to a batch past the group's commit.** It is where FTS5's 40% goes, but a post would be acknowledged before its index row is
  durable (a crash loses it until a start-up repair, and Rails, rolled back to, never repairs it) and a search would need to flush first. That is a
  durability and freshness change, not the same durability as Rails; the in-group deferral (`Tx.OnCommit`, R2.2) is already done.
- **Skipping the `rooms` touch or `sqlite_sequence`.** One frame each, both data Rails reads.
- **Dropping Rails' `index_messages_on_room_id`** (the room-page index covers it): a schema change.

## What changed in the code

- `WriterStats.Frames` (and `All`): the WAL frames the writer's commits append, from the frame count it already read after every committed group
  (`Database.fs`); `WriterStats.All.Groups` and `.Writes` are now kept too. `CAMPFIRE_WAL_TRACE` logs the totals at every WAL restart.
- `PostPath.GroupWindowUs` (a bench switch over `Config.GroupWindowUs`) and `Database.StartPostPathControl` (`CAMPFIRE_POSTPATH_FILE`: a control file
  applied within 20 ms; benches only, inert otherwise).
- `Schema.ftsAutomerge`, `Schema.setFtsAutomerge`, `CAMPFIRE_FTS_AUTOMERGE` (opt-in).
- Tools: `bench/wal-ab`, `bench/results/oncrack-r4-wal/{replay.py,frames.py,commits.py,trace-run.sh}`, `bench/post-micro` (`--fts`, frames and writes per
  group per window).
- Tests (`GroupCommitTests`): the frame counter; search results equal across automerge 4, 16 and 0.

## Verification

`bin/verify` ran 1,162 tests and passed (0 failed) on the third of three tries. The Mac was at load 20-37 from other sessions; the first two tries failed
`CheckHoldTests` (a "the readers ran" count of 1,000 checks in 300 ms), `DatabaseTests` (slow checkpoint, WAL bounded), and Cable timing tests, and the
same tests failed on a stash of HEAD under the same load (3 tries: 2 failed, 1 passed), and each passes alone. They are load-sensitive tests, not
changes of this unit. Pixels: nothing rendered changed, so `bin/pixel-parity` was not run.

## Deferred

- Why `automerge` helps in process and offline and not in the container: snapshot the WAL mid-run (not after a restart) and attribute by b-tree.
- A window used only while the disk is slow (`Checkpoints.Healthy` false), the one design the numbers leave open.
- `bin/db-differential` with `CAMPFIRE_FTS_AUTOMERGE` set, and search latency over an index with the extra segments.
- The upstream harness's post and mixed profiles on this build (the default path is unchanged).
