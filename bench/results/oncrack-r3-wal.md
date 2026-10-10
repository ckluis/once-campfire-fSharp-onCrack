# R3.4: the WAL-restart stall

Round 3, unit 4. The stall that has held back sustained posting since R2.2: this suite's 90 s warm-ups read 11.3k posts/s at
c=16, upstream's 2 s warm-up 15.2k, with one 0.9-1.0 s stall per window. Commits `1efc805` (the work) and `4ac9b2b` (the
default), on branch `crack`. Data and scripts: [`oncrack-r3-wal/`](oncrack-r3-wal/).

**Result, plainly:** the stall is the VM's disk, not the checkpoint policy. Sustained posting writes 250-300 MB/s of WAL. Under
that load the virtual disk stops completing writes for 0.3-1.7 s every few seconds, and any sync issued in that time waits it out.
No WAL policy with a bounded file hides a stop that long, so none of the designs measured here showed a gain that held up in
alternating reps. **The default stays R2.2's restart.** What came out of the unit:
- The deferred restart, with tests, as an opt-in (`CAMPFIRE_WAL_DEFER`, `CAMPFIRE_WAL_CEILING_PAGES`).
- A 250 ms checkpoint of a quiet WAL, on by default. Current Rails' checkpoint thread does the same.
- The tools that found the cause: a WAL trace, a WAL breakdown by b-tree, and disk sampling.
- The real lever, which is fewer WAL frames per post (below).

Durability is unchanged by default, and against a crash of the process in every variant (the kill -9 test ran with `CAMPFIRE_WAL_DEFER=on` too: 0 lost). *(Final review's correction: this line first said "unchanged in every variant".)* Against a power failure the opt-in is weaker. With `synchronous=normal` a commit is not synced until a checkpoint syncs the WAL, and while a checkpoint is stuck in a slow sync the deferred restart keeps acknowledging commits up to the ceiling (40,000 frames) where the default waits at 10,000. More acknowledged posts can therefore sit unsynced at that moment. That is one more reason it stays off.

## What the stall is

`CAMPFIRE_WAL_TRACE=/trace/wal.log` (new) logs every checkpoint, every forced restart and every writer group over 20 ms.
`bench/run`'s `TRACE_DIR` mounts a directory for the file. `oncrack-r3-wal/trace-run.sh` runs one tier 2 rep with the trace on
and samples the VM's dirty memory and `/proc/diskstats` every 250 ms; `trace.py` reads the result. R2.2's policy at c=16
(`tr-r22`):

- The WAL restarts 5.5 times a second. Every restart is the writer's forced RESTART at 10,000 frames.
- 48 PASSIVE checkpoints a second: median 3.0 ms, p99 18.7 ms, max 697 ms.
- The writer's RESTART waited for a running PASSIVE for more than 100 ms 15 times (max 700 ms). Its own run took more than
  100 ms 5 times (max 490 ms).
- No writer group took 20 ms or more. Commits themselves never stall.
- The slow checkpoints come in clusters about every 3.3 s. In those clusters the disk completes nothing for up to a second.
  Around one stall in `tr-gate` it ran at 240-306 MB/s, then 0 MB/s for about 0.8 s, then the write queue's busy time jumped
  12 s at once (`vm.log`).

Where 300 MB/s comes from (`bench/lib/walmix.py`, new). It reads the WAL that `bench/post-micro` leaves behind with
`POST_MICRO_KEEP` and names every frame's b-tree:
- 5,803 frames in 285 commits: 20.4 frames a commit, but only 177 distinct pages. Every group commit rewrites the right edge of
  about 13 b-trees.
- FTS5 is 36% of the frames (data 20.5%, content, docsize, idx). After it: `index_messages_on_room_id_and_created_at` 14.4%, the
  rich text and its uniqueness index 8.3% each, and `messages` 8.2%.
- At c=16 that is about 5.3 frames a post: 55,000-70,000 frames a second, 220-290 MB/s of WAL.

What the first attempt (cut off before committing) found, kept here as `t2-*`, one rep each on the mounted build:
- **No disk, no stall.** With the database on tmpfs (`t2-r22-tmpfs`), c=16 ran with a slowest answer of 9.8 ms. On ext4
  (`t2-r22`) it was 797 ms.
- **Truncating the WAL stalls too.** A 40,000-frame ceiling under the 64 MB `journal_size_limit` (`t2-defer`) truncated the WAL
  after every restart. The VM's root mounts with `discard`, and the truncation's trim stalled the next syncs: c=64 ran 1,054
  posts/s with a 5.8 s stall.

## Designs measured

Each design is a switch, so they ran on one build:

| Design | What the writer does past 10,000 frames |
|---|---|
| R2.2 (default) | waits for a running PASSIVE, then RESTARTs (copies the tail, syncs, waits for readers) |
| Deferred restart (`CAMPFIRE_WAL_DEFER=on`) | restarts only when that is cheap: no checkpoint running, at most 1,000 frames left to copy, and the last checkpoint under 25 ms. Otherwise it wakes the checkpointer again and keeps writing, up to the ceiling, where it waits as R2.2 does. The writer's `journal_size_limit` is above the ceiling, so the WAL is never truncated. |
| Ceiling | 16,000 (an earlier form, below 64 MB), 40,000 (~160 MB, the opt-in's default) or 150,000 frames (~600 MB) |
| Checkpoint every 4,000 pages | a fewer-but-larger PASSIVE checkpoint (`tr-gate-cp4k`); worse (9,386 posts/s at c=16, slowest 717 ms) and dropped |

**Traces** (tier 2, mounted build, one rep each, a fixed 60 s warm-up; `trace.py`):

| Run | c=16 posts/s | slowest | c=64 posts/s | slowest | writer waits over 100 ms |
|---|---|---|---|---|---|
| `tr-r22` R2.2 | 10,418 | 682 ms | | | 15 |
| `tr-defer16k` deferred, 16,000 | 11,537 | 611 ms | 16,965 | 19 ms | 8 |
| `tr-gate` deferred, 40,000 | 13,286 | 257 ms | 16,288 | 36 ms | 7 (each at the ceiling) |
| `tr-gate-150k` deferred, 150,000 | 13,466 | 173 ms | 16,868 | 20 ms | 3 (each at the ceiling) |

Even 150,000 frames was reached three times in about 70 s. After a slow checkpoint, the writer waits for a quick one before it
restarts the WAL, and slow periods run long enough for the WAL to grow by 600 MB.

**Tier 3** (the rebuilt image, this suite's full warm-up of 30-90 s until flat, `post_message` at c=16 and c=64; `t3-pair.sh`,
`pooled.py`):
- Reps 1-3 alternate R2.2 and the 40,000 ceiling (image `1efc805`).
- Ceiling reps 1-2 ran on their own, and rep 4 alternates with R2.2 (image `4ac9b2b`).

| Design | c | posts/s by rep | median | CPU us/post | slowest answer by rep (ms) |
|---|---|---|---|---|---|
| R2.2 restart (default) | 16 | 10,662, 11,883, 10,153, 11,002 | **10,832** | 199 | 950, 435, 888, 429 |
| deferred, 40,000 ceiling | 16 | 11,004, 11,771, 10,930 | **11,004** | 215 | 919, 1,329, 214 |
| deferred, 150,000 ceiling | 16 | 14,701, 12,857, 9,603 | **12,857** | 223 | 389, 63, 227 |
| R2.2 restart (default) | 64 | 16,194, 17,340, 16,890, 15,323 | **16,542** | 171 | 40, 51, 40, 45 |
| deferred, 40,000 ceiling | 64 | 12,624, 16,531, 14,778 | **14,778** | 193 | 195, 37, 25 |
| deferred, 150,000 ceiling | 64 | 15,050, 17,301, 12,374 | **15,050** | 191 | 40, 23, 104 |

How to read this:
- **The 40,000 ceiling is a wash at c=16 and lower at c=64** in all three alternating reps (12,624 / 16,531 / 14,778 against
  16,194 / 17,340 / 16,890). R2.2 did not stall at c=64 to begin with. The deferral adds back-to-back PASSIVE checkpoints (CPU per
  post 171 -> 193 us) and a larger WAL to sync.
- **The 150,000 ceiling has the best c=16 runs and the shortest worst answers** (63-389 ms against 429-950).
  - Its warm-up windows are flat at 13-14k, where R2.2's swing between 8k and 16k.
  - But in its one rep that alternated with R2.2 it lost (9,603 against 11,002). Its CPU per post is 12% higher, and it holds a
    600 MB WAL file.
  - Two reps on their own and one that lost do not make a win.
- The host was noisy as in R3.2. Samples of one variant swing 30-50% between reps, and some windows carry a host-probe note.

**In process** (`micro-ab-1.txt`, `bench/post-micro` with `--variants "base;wal_defer=off"` in the VM, the 40,000 ceiling, four
alternating 8 s windows; the in-process load generator shares the cores):
- c=16: 9,086 against 9,026 posts/s. Answers over 100 ms: 48 and 32 deferred, against 96, 64 and 64 for R2.2.
- c=64: 13,952 against 15,338.

**Upstream's harness** (`upstream/`, `--rounds 3 --duration 8`, its 2 s warm-up, image `4ac9b2b`). The `oncrack-cached` slot is
reused for the 150,000-frame opt-in with fresh authorization on (`env-r34.sh`); `oncrack` is the shipped default:

| Profile | Route | c | oncrack (default) median [runs] | opt-in, 150,000 ceiling |
|---|---|---|---|---|
| read-and-post | post a message | 16 | 12,588 [12,588, 13,108, 11,755] | 12,971 [12,688, 13,184, 12,971] |
| read-and-post | post a message | 64 | 17,480 [13,584, 17,480, 17,678] | 17,409 [17,254, 17,272, 17,409] |
| mixed, 10 writes/s | room page | 16 | 131,897 [140,802, 131,897, 124,059] | 129,784 [129,784, 143,817, 112,642] |
| mixed, 10 writes/s | messages page | 16 | 139,593 [153,661, 139,593, 121,352] | 137,351 [137,351, 139,792, 118,074] |
| mixed, 10 writes/s | sidebar | 16 | 150,471 [159,336, 150,471, 142,201] | 147,403 [160,424, 147,403, 98,713] |
| mixed, 10 writes/s | search | 16 | 147,694 [155,411, 147,694, 133,081] | 126,751 [147,748, 119,151, 126,751] |

- Every response passed its contract: 0 errors, 0 invalid responses.
- The two policies are within noise. Upstream's 8 s samples after a 2 s warm-up mostly end before the WAL reaches its limit, so
  the stall rarely shows there. At 10 writes a second, the mixed profile never comes near a WAL restart.
- Upstream Rust and C were not re-run. Against R3.3's ratios nothing on the post path changed by default.
- This session's c=16 post median (12,588) is below round 2's 15,214. The host was slower this afternoon, and the same image's
  reps here range 11,755-13,108.

## What changed in the code

- **`Checkpoints`** (`src/Campfire.Db/Database.fs`):
  - With no commit reaching 1,000 pages, the checkpointer runs a PASSIVE every 250 ms while the WAL holds frames it has not
    copied (`CAMPFIRE_WAL_CHECKPOINT_MS`, 0 turns it off). So a quiet database's WAL is synced within a quarter of a second, not
    after 1,000 pages: current Rails' checkpoint thread (`lib/rails_ext/sqlite_wal_checkpoint.rb`, every 0.25 s) gives the same
    bound.
  - Under load it never fires, because the 1,000-page wake comes first.
  - It records how long each PASSIVE ran (`Healthy`), and has `TryRestartWal` and `WakeAgain` for the opt-in.
- **`CAMPFIRE_WAL_DEFER`** (off), `CAMPFIRE_WAL_CEILING_PAGES` (40,000). With the defer on, the writer connection's
  `journal_size_limit` is 192 MB, or 1.2 times the ceiling if that is more. Readers and the default writer keep Rails' 64 MB.
- **Tests** (`DatabaseTests`):
  - The writer carries on past the limit while a checkpoint is stuck.
  - It waits for a stuck checkpoint at the ceiling, within one commit of it.
  - After a slow checkpoint it leaves the restart for later, and restarts once checkpoints are quick again.
  - A quiet WAL is checkpointed within the interval.
  - The writer's `journal_size_limit` follows the switch.
  - `bin/verify`: 1,144 tests, 0 failed.
- **Tools:**
  - `bench/lib/walmix.py`.
  - `bench/post-micro`'s `POST_MICRO_KEEP=DIR` keeps the database. `bench/micro-linux` passes it through, and its `CPUS` sets
    the cores.
  - `bench/run`'s `TRACE_DIR` and `LOGTAIL_LINES`.
  - `CAMPFIRE_WAL_TRACE`: stderr, or a file when the value is an absolute path.

Pixels: the default code path is R2.2's, and the change is in the database layer only, below anything rendered. No pixel gate
was run for this unit.

The climb log was not appended. It takes full five-workload runs at c=1 and c=16, and this unit's runs are posts only at c=16
and c=64; R3.2 and R3.3 did not append either.

## What would fix it

The stall is the disk's answer to the write volume, so the lever is fewer bytes per post:
- **Fewer WAL frames per post.** About 20 pages are rewritten per group commit, whatever the group's size. Bigger groups at c=16,
  or one transaction where the group and its `OnCommit` index work now take two, would cut frames per post.
- **FTS5's per-transaction segment and merge work,** 36% of the frames.

Measure either with `walmix.py` (frames per commit, by b-tree) and the trace before the throughput.

The 150,000-frame opt-in is the only policy that kept the writer off most slow syncs. Shipping it would need:
- alternating reps that hold up;
- a decision about its footprint: a WAL file of up to 600 MB that is never truncated, where current Rails has no bound at all
  but truncates to 64 MB after a restart.

## Disk

- The Mac fell to 11 GB free once, after the image build and the first tier 3 rep. That is below the 12 GB floor. The check ran
  in the same call as tier 3 rep 2, so that rep ran anyway.
- `bin/clean-docker` and `fstrim` brought it back to 15 GB. The gate cleanup (`bin/clean-docker`, `bin/clean-parity`, `fstrim`)
  ran after each block of runs, and the last left 13 GB.
- The post-micro database copy and the trace directories in the VM are deleted.
