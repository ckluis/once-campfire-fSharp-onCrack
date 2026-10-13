# onCrack: the verifier's findings, fixed

Four findings from the onCrack verifier's round on C1-C3, fixed in severity order, each with a test that fails without the fix.
Commits `6ec598f`, `0ce3b21`, `5d91978`, `7f08f77` (results `1598c5e`). `bin/verify`: Release build, warnings as errors, 1,075
tests, 0 failed, 7 skipped (the media vectors and Linux-only tests, as before).

## 1. Major: a page kept from a user row older than its counters (read cache)

Authentication reads the signed-in user (`ReadCache.user`) before the action takes the page's counters, and the page renders
that user: the `current-user-name` meta tag, the composer's template, and the sidebar's name, avatar and the administrator-only
New Chat Room button. A change to the user that committed between those two points was rendered from the old row and kept
under the new counters. The page was then served until an unrelated write moved a counter.

**Rule now:** a page's global dependency is the global counter's value that the user was read under (`UserReadAt`: the users
map's own dependency on a hit, or the value taken before the load on a miss). It is not a value taken when the action starts.
A page whose user changed since then is neither kept (`Keep` checks its dependencies) nor served. A page whose user was not
read through the cache is rendered but not kept.

**Tests** (`ReadCacheTests`). In each, 1,000 changes are made while 12 browsers read the page, and after each change returns, a
fresh request must show it. The three tests cover a rename on the room page (meta tag and template), a rename on the sidebar,
and a role change made by SQL on the `restricted` seed (the New Chat Room button). Before the fix, each failed (stale at rounds
94, 105, 132...; 22, 60, 104...; 2, 44, 58...). After it, all pass twice in a row, and they also pass with
`CAMPFIRE_READ_CACHE=off`.

## 2. Minor: a room counter for every id in a URL

`roomDeps` takes the room's counter for the id in the URL before `set_room` checks that the room exists. `Versions.Room` made
one counter per id and never removed any, about 195 bytes per new id.

**Rule now:** each room counter covers every id that is equal modulo 65,536, and is made on first use. That is at most 65,536
counters and a 512 KB array per database. Rooms that share a counter only invalidate each other's pages, which is conservative.
Sequential ids share no counter until there are that many rooms, and no two of the seeds' rooms share one.

**Tests:**
- `VersionsTests`: a million ids stay within the stripes, and ids a stripe apart share their marks.
- `ReadCacheTests`: 2,000 requests for rooms that don't exist, a stripe apart, make at most one counter.

## 3. Minor: group commit broadcast concurrent posts out of commit order

The writer answers a group's posts one after another, and each request broadcasts from its own continuation. The client
places an appended message by `data-sort-value`, which is in milliseconds. Most out-of-order pairs fell within one
millisecond, so the client's re-sort kept them out of order.

The same test, run before the fix, counted adjacent pairs broadcast out of commit order:

| | Out of order as broadcast | Still out of order after the client's re-sort |
|---|---|---|
| Group commit on | 96-101 | 86-96 |
| `CAMPFIRE_GROUP_COMMIT=off` | 50-56 | 37-48 |

So a live viewer saw those posts in a different order from a reload. The port and Rails reorder too, but less often.

**Fix:** `BroadcastOrder` is a line of places. A post takes its place in its write's after-commit hook, on the writer and in
commit order. `messages#create` renders as before, in its own request and in parallel with the others. It reads the members
for the unread pings and then hands only the publishing to its place. The line publishes a place once every earlier place
has published or given up. Every path gives its place up in a `finally`, and a place nobody fills is skipped after one second
and logged, so a request that is lost cannot hold the line.

Three kinds of post broadcast at once, as before:
- posts with an attachment, because analysis between the commit and the broadcast would hold the line;
- bots' posts;
- webhook replies.

**Tests:**
- 16 browsers post 20 messages each: all 320 arrive with 0 out-of-order pairs, with group commit on and off.
- The line publishes 2,000 places in order when many threads fill them in shuffled order.
- A place given up does not hold the line, and an empty place is skipped after the stall.
- A ticket reserves once even when its hook runs twice, and publishes once.

## 4. Minor: `bin/kit-differential http` failed by default

Since C3, a gzipped answer carries a Content-Length where Rust's kit chunks. The gate passed only with
`CAMPFIRE_GZIP_LENGTH=off`, which turns off the path being shipped.

`fuzz.py` now drops F#'s Content-Length from a gzipped answer only in this case: Rust sends none, and the value is exactly the
length of the gzip member received. For a HEAD, which has no body to measure, any positive value is accepted. Every other
difference still fails.

`fuzz.py selftest` runs first, and it fails if the filter lets through a wrong length, a second length, a length on a chunked
answer, a plain answer's length, or a length both sides send. With the defaults, plain and SSL each had 0 differences in 1,500
requests. With seed 7, plain and SSL each had 0 in 4,000. With `CAMPFIRE_GZIP_LENGTH=off`, still 0. The difference is recorded
with C3's in `AGENTS.md`.

## Measurements

**Tier 2:** mounted builds, one rep each, same session, `oncrack-fixes/t2-before` (`f03b62a`) and `t2-after` (`7f08f77`).
Both are logged. Every workload is within run-to-run noise:
- c=16 reads: -1.2% to +4.7%;
- posts: -1.5% at c=16, +3% at c=1;
- CPU per request at c=16: within 1.3 us.

**Tier 3:** image `1598c5e`, 3 reps, `oncrack-fixes/t3`, logged. Medians, with the ratio to each stored baseline from
`phase7-final`:

| Workload | c | req/s | CPU us/req | vs Rust | vs F# port | C3 tier 3 (`460e89d`) |
|---|---|---|---|---|---|---|
| room page | 16 | 123,248 | 30.4 | 4.31x | 3.05x | 124,329 (30.2) |
| room page | 1 | 13,342 | 145.3 | 2.06x | 1.75x | 13,548 (143.1) |
| messages page | 16 | 123,156 | 30.3 | 4.10x | 3.26x | 124,328 (29.8) |
| messages page | 1 | 13,496 | 144.5 | 1.98x | 1.62x | 13,837 (142.2) |
| sidebar | 16 | 137,500 | 26.9 | 4.87x | 3.66x | 138,274 (26.9) |
| sidebar | 1 | 15,840 | 126.6 | 2.56x | 1.98x | 16,349 (122.9) |
| search | 16 | 135,425 | 27.3 | 5.09x | 3.98x | 136,313 (27.0) |
| search | 1 | 14,669 | 135.5 | 2.60x | 2.42x | 14,677 (136.0) |
| post a message | 16 | 12,991 | 233.4 | 1.81x | 1.46x | 13,249 (231.2) |
| post a message | 1 | 3,374 | 586.8 | 1.21x | 1.11x | 3,399 (581.1) |

Against C3's tier 3, from an earlier session, every workload is 0-3% lower. The same-session tier 2 A/B does not separate that
from noise. The post line's work is one lock, one dictionary entry and the member list per post. That fits the +2 us of CPU at
c=16 on posts, but this measurement cannot tell it apart from noise. All checks passed: every response 2xx, posts written
equal to answers, and decoded bytes equal to Rust's.
