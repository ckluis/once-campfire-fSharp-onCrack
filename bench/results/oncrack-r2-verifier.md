# onCrack round 2: the verifier's findings, fixed

Date 2026-10-09, branch `crack`. Code commits `1537475` (the WAL index watch, per-epoch fragments, content ETag on the messages page), `1c87802`
(fast path targets as hashes, a cache budget of 0 is off, `Q=` is a quality), `96bb4f6` (db differential), `f958658` (README, AGENTS), `2ea9ae9`
(libc named per platform; never fails start-up). Image `campfire-oncrack:app` `sha256:7e56d81cc90f` (label `2ea9ae9`); `campfire-fsharp:app` (the
port) untouched. Raw data in [`oncrack-r2-verifier/`](oncrack-r2-verifier/): `t2-before`, `t2-after`, `t2-real-before`, `t2-real-after`, `post-ab/`,
`t3` (each `bench/quick` output, `vs-stored.md` inside), and `evidence/` (the verifier's black-box scripts as run on Linux, and their output).

onCrack is scored on its own terms (plan rule 4). Nothing here weakens durability or adds an opt-in.

## Verdict

- **All seven findings fixed, each with a test that fails on the code before** (mutation-checked where the fix is a guard): the critical one and
  the two majors by one mechanism, the WAL index watch.
- **On Linux, against the verifier's own `foreign.py`** (fresh container per case, warm 5 times, edit from another connection, check at once and
  1.5 s later): every case that Rails 90b3300 and Rust ccece30 pass now passes, plus the timestamp-free edits they fail (body, creator, creator's
  name, boost insert and update, the stale `If-None-Match`). Session deleted or token rotated: 302 to `/session/new`; membership deleted: 302 and
  404 (`evidence/foreign-fixed.jsonl`). Two checks still read `False`, and neither is a defect: `user_deactivated` (status edited alone) is 200 in
  Rails and Rust too, since Rails deactivation deletes the sessions; `search_body_edit` searches "Pizza", which no message of the default seed
  contains, so its UPDATE changes no row in any app. A search case that edits a message Kevin can find passes here, and fails on Rust and on
  onCrack R2.5 with both caches off (`evidence/search-and-memflood.jsonl`).
- **The long-URL flood**: 20,000 distinct 7 KB URLs, each twice, one signed-in user: anon **22 -> 103 MB** (R2.5: 21 -> 362; the verifier measured
  99 with the fast path off).
- **Throughput did not move.** Tier 3 read pages are within 1% of tier 2 and of R2.5's tier 3. Posts at c=16, alternated with the R2.5 build
  in one session: 16,142 and 14,142 posts/s before against 16,201 and 16,219 after, at 170-173 us of CPU each. Tier 3's post rows are low
  (11,050 at c=16, 3,999 at c=1), but CPU per post is level or lower (174.5 and 246.0 us; R2.4's tier 3 was 245.6 at c=1). Every post rep
  reached its warm-up maximum: these are the writer's WAL-restart stalls (open since R2.2), which hit the R2.5 build the same way (R2.5's own run
  had a 10.3k rep). I report the row as measured, and I don't count it as this change's cost.
- **Correct:** every response 2xx with 0 connection errors in every run, post rows equal the answers, and decoded bytes equal Rust's on every
  probed route. `bin/verify`: 1,123 passed, 8 skipped. `bin/db-differential`: 4/4, schema identity, rollback ok. No run logged
  `a commit by another connection`, so the app's own writes never trip the watch.

## The findings and their fixes

| # | Severity | Finding | Fix | Test that catches it |
|---|---|---|---|---|
| 1 | critical | A session revoked, a token rotated or a membership removed by another connection stayed authorized (read cache, auth maps, fast path) and could still post | `Versions` maps the WAL index's `iChange` (one per commit that writes, by anyone) read-only, keeps the value accounted for, and tells the writer's commits from others' by its own connection's `PRAGMA data_version` (`Versions.Committing`, around every `COMMIT` and every autocommitted after-commit hook). `Versions.Sync`, before any cache serves (pages, sessions, users, every fast path replay), moves every counter by 2 and the epoch by 1 for a commit nobody accounted for | `ForeignWriteTests` (in process and fronted): revoked and rotated sessions, removed membership, a revoked session's POST; `VersionsWatchTests`. Mutations: `Sync` a no-op fails 5 of 6; dropping the writer's `data_version` check fails the interleaving test |
| 2 | major | Content committed by another connection (rename, a timestamped message) hidden by the page caches | Same mechanism | `ForeignWriteTests` "foreign and local writers change cached room content" |
| 3 | major | Timestamp-free edits (body, creator, name, boosts) stale in fragments, search and the messages page's 304 (inherited from Rails and Rust) | One fragment store per epoch (`AppState.FragmentStoreNow`), taken by a request before authentication and by a job before its first read; the messages page drops `fresh_when` for `Rack::ETag`'s content digest and no `Last-Modified` (as upstream now does; README, known differences) | `ForeignWriteTests` "timestamp free foreign edits invalidate nested fragments and validators"; one store for every epoch fails it |
| 4 | major | The fast path's target set kept every offered URL as a string outside its budget (~1.4 GB) | It keeps 32-bit process-seeded hashes (a collision costs a key build) | `VerifierRound2Tests`: 20,000 7 KB targets, none kept alive (the string set keeps all 20,000) |
| 5 | minor | `*_MB=0` fell back to the defaults; `CAMPFIRE_RESPONSE_CACHE_MB` ignored | 0 is off; upstream's setting sets both (0 off, N split 1:4 as the defaults); `ResponseCacheBudgets.resolve` | `VerifierRound2Tests` budgets table |
| 6 | minor | The db differential never exercised R2.2's `unread_at` divergence | Two more posts into hq while its members are unread; memberships compared by the message their `unread_at` names: byte-equal with `UnreadSkip` off, and with it on only earlier posts (at least one row). Cites upstream Rails #336 | `bin/db-differential` (4/4) |
| 7 | minor | `gzip;Q=0` treated as q=1 (inherited from Thruster, Rack and Rust) | `Q=` read as `q=` in the front server and in `Rack::Deflater`'s place (README, known differences) | `VerifierRound2Tests`, `DeflaterTests` |

How the watch stays exact (`src/Campfire.Db/Versions.fs`, top comment):
- `iChange` moves only for commits that write. Checked empirically on SQLite 3.54 and in `VersionsWatchTests`: not for empty commits, rollbacks,
  checkpoints, WAL restarts or TEMP writes.
- The writer holds the watch's lock across its commit and reads `data_version` before and after, so a foreign commit before, during or right after
  its own is never absorbed into the accepted value.
- A reader that sees the header move while the writer is committing waits on the lock, then finds the value accepted.
- The mapping goes through libc. .NET's `FileStream` takes a `flock` that fights SQLite's locks on macOS, and closing a descriptor would drop the
  process's POSIX locks, SQLite's included, so the descriptor stays open until every connection is closed.
- A write on the writer's connection outside `Committing` costs every cache, never correctness, and logs `WARN campfire_db: a commit by another
  connection`.

## Measurements

Tier 1 was skipped: on a hit the change is one load from the mapping and one volatile read, and per commit it is a lock and two
`PRAGMA data_version` queries on the writer. Tier 2 and tier 3 measured it directly.

**Tier 2, five workloads, 1 rep each, same session** (`t2-before`: the R2.5 image `64a714d`; `t2-after`: mounted `2ea9ae9`). req/s (CPU us/req):

| Workload | c | before | after | after / before |
|---|---|---|---|---|
| room page | 16 | 174,478 (17.8) | 174,013 (17.8) | 1.00x |
| room page | 1 | 26,097 (19.1) | 25,976 (19.4) | 1.00x |
| messages page | 16 | 183,259 (16.5) | 185,907 (16.3) | 1.01x |
| messages page | 1 | 26,684 (18.5) | 26,792 (18.6) | 1.00x |
| sidebar | 16 | 184,098 (15.5) | 198,311 (14.8) | 1.08x ¹ |
| sidebar | 1 | 27,121 (17.6) | 27,421 (17.5) | 1.01x |
| search | 16 | 194,487 (15.1) | 192,499 (15.3) | 0.99x |
| search | 1 | 27,452 (17.6) | 27,278 (17.8) | 0.99x |
| post a message | 16 | 12,653 (177.0) | 12,439 (179.1) | 0.98x |
| post a message | 1 | 3,851 (254.2) | 5,019 (253.8) | 1.30x ² |

¹ Nothing in the change makes the sidebar cheaper; R2.5's tier 3 measured 196-198k. The before rep is low. ² The before rep did not settle (its
warm-up reached the maximum), at the same CPU per post. R2.4's tier 3 was 5,172. Neither is a gain.

**Post c=16, alternated** (`post-ab/`, mounted builds of `64a714d` and `2ea9ae9` over the same image, one container each): before 16,142 (172.1) and
14,142 (170.3); after 16,201 (173.2) and 16,219 (171.1).

**Tier 2, realistic workloads** (`t2-real-*`, crowd seed, c=16 readers, 1 rep each), req/s (CPU us/req, all lanes):

| Workload | lane | before | after | after / before |
|---|---|---|---|---|
| mixed | reads | 42,074 | 42,583 | 1.01x |
| mixed | posts | 1,355 (79.7) | 1,341 (78.6) | 0.99x |
| spread | reads | 188,633 (16.4) | 186,629 (16.6) | 0.99x |
| spread_mixed | reads | 11,125 | 10,802 | 0.97x |
| spread_mixed | posts | 666 (329.0) | 650 (338.4) | 0.98x |
| search_spread | reads | 13,999 (269.2) | 17,244 (212.9) | 1.23x ³ |

³ The before rep is 21% below R2.5's stored 17,802, the after rep at it. R2.5 already reported this workload moving 14% between series. Not a gain.
`spread_mixed` is 2-3% lower on one rep each, within that noise.

**Tier 3, rebuilt image, 3 reps** (`t3`), req/s median [min-max] (CPU us/req), against the stored phase7-final medians (Rust and the F# port, one
session):

| Workload | c | onCrack | / Rust | / F# port |
|---|---|---|---|---|
| room page | 16 | 175,720 [174,258-175,871] (17.6) | 6.14x | 4.35x |
| room page | 1 | 26,426 [25,541-26,783] (18.3) | 4.08x | 3.47x |
| messages page | 16 | 185,184 [184,660-186,353] (16.2) | 6.16x | 4.89x |
| messages page | 1 | 26,607 [26,042-27,008] (18.2) | 3.90x | 3.20x |
| sidebar | 16 | 196,907 [196,219-199,848] (14.9) | 6.97x | 5.24x |
| sidebar | 1 | 26,904 [26,666-27,069] (17.5) | 4.34x | 3.36x |
| search | 16 | 196,012 [193,879-196,439] (15.0) | 7.37x | 5.75x |
| search | 1 | 28,118 [27,824-28,203] (16.9) | 4.98x | 4.64x |
| post a message | 16 | 11,050 [10,562-11,344] (174.5) | 1.54x | 1.24x |
| post a message | 1 | 3,999 [3,345-5,130] (246.0) | 1.44x | 1.31x |

The post rows: see the verdict. In the alternated runs above, posts at c=16 are 2.26x Rust and 1.82x the port.

Every tier 2 and tier 3 run is in `oncrack-log.jsonl` (unit `r2-verifier`; the before runs are marked `kept: false`).

## Open

- **Two unexplained 302s under the whole-solution test run.** `bin/verify` runs all test projects in parallel (about 6.5 cores). In 26 such runs
  with this change, two tests each got one 302 for a signed-in browser: once in `ForeignWriteTests`' warm-up, before any foreign write, and once
  in `PresenterAccountsTests` ("administers the account"). Neither repeated in 24 more full runs or in 9 runs of three App suites at once. HEAD
  before the change showed none in 16 runs. That difference is not significant, and I found no mechanism: the watch never touches a session row,
  and an unexplained commit only moves counters. `warm` now prints the status and Location, so the next one will say whether it was a session
  miss. The other flakes seen (`DirectTests`' probe, `MiscTests`' fixed window) happen at HEAD too.
- **The writer's WAL-restart stall under sustained c=16 posting** (since R2.2) is what makes tier 3's post rows swing.
- `CAMPFIRE_RESPONSE_CACHE_MB` splits its N 1:4 between the two caches; upstream has one cache, so that split is onCrack's own choice.
