# onCrack unit C3: search

Date 2026-10-07, branch `crack`. Commits `cbb1643` (Content-Length on gzipped answers, tests, `bench/paths`), the log commit and the docs/results commit after it.
Image `campfire-oncrack:app` rebuilt from `460e89d` (same source as `cbb1643`; `campfire-fsharp:app`, the port, untouched). Every number is onCrack's, scored
against the stored medians of `phase7-final` (Rust and the F# port in one session, not re-measured), never a like-for-like port result.

## What the unit found

**The search page was already cached.** C1 caches search pages per user, per request (query included) and under the global counter, the user's and every room
the user is in, with the read cache's rule (edits, deletes, new messages, boosts, bans and membership changes all move one of those counters; the tests are
`ReadCacheTests.fs`). Nothing new was needed for invalidation, and it is not made finer: a post in any of a user's rooms moves that room's counter, so it
drops that user's cached searches, and telling "this post can't match that query" would need FTS5's tokenizer (porter stemming) reimplemented, which is not
worth an exactness risk. Listed under deferred.

**The search c=16 ceiling C1 could not explain was not about search.** At c=16 a cached search for `coffee` ran 72k req/s on 2.2 of 4 server cores
while the sidebar ran 104-112k. `bench/paths` (new: any GET paths, one container) showed it was bistable by response, not by route:

| `/searches?q=` (wire bytes) | c=16 req/s before |
|---|---|
| thanks (6.9 KB), hello (7.2 KB) | 115-118k |
| to, you, coffee, and, i (9.4-10.4 KB) | 70-73k |
| a (13.7 KB) | 96k |
| for, in (17-18 KB) | 70-74k |
| is, the (24-29 KB) | 98-101k |

A concurrency sweep (c=4/8/32/64: coffee 31k/45k/125k/135k, sidebar 32k/51k/138k/143k) showed both pages latency-bound at c=16 with idle cores, and `perf stat`
on the slow case showed 18 syscalls per request and 16k CPU migrations in a run, against 10 syscalls per request and 1k migrations in the fast case. The cause: every
gzipped answer went out chunked (`Transfer-Encoding: chunked`; Rack::Deflater's behavior, which the port copies), so each response was a send for the headers
and body and then another for the terminating chunk. On a hit that costs 27-32 us of CPU, the second send and the extra wake-ups of the client and of the
pool's workers are the round trip.

**The change** (`src/Campfire.Kit/Adapter.fs`, `IPageParts.GzipIfReady`): for a gzipped buffer (through the digest-keyed gzip cache) or a frozen page (its stored
member) the adapter makes the member before the headers, sends `Content-Length`, and writes it once. Streams, files and pages in parts that are not frozen (a
cache miss, or the cache off: CPU-bound at 100-200 us, where chunking measured no difference) stay chunked. `CAMPFIRE_GZIP_LENGTH=off` restores chunking. The
bytes, ETag, Vary and Content-Encoding are unchanged; HEAD is unchanged. This applies to every route, not only search.

Tried and dropped: re-deflating a frozen page as one stream at level 9 (3% smaller for search, 16% for the room page, 18 bytes bigger for the sidebar) moved
neither throughput nor CPU with the length in place, so it was not kept.

## FTS query: looked at, nothing changed

The statements are already prepared and reused per connection, the query already has `LIMIT 100`, and it orders by `created_at`, not rank, so there is no
ranking work to share. The plan is FTS rowid scan, then messages, rooms and memberships by key, then a temp b-tree for the order. On the seed the search read is
14.5 us (port's `phase7-database.md`). On a copy of the seed with 200k messages, a query matching all of them took 84 ms; dropping the redundant `rooms` join
or turning the membership join into an `IN` subquery gave 75-77 ms (-8..-10%) with byte-identical output in four cases. Not applied: the `IN` form changes the
result if `(room_id, user_id)` were not unique, dropping the join makes an orphaned message visible, and walking FTS in rowid order instead of sorting would
reorder messages that share a second-resolution `created_at` (the seed has them) relative to what SQLite's sorter gives today. A saving of under 10% on a miss that
costs milliseconds in a 200k-message database is not worth any of those.

## Tests

`ReadCacheTests.fs`: a gzipped room page, sidebar and two searches, uncached and cached, carry `Content-Length` equal to the bytes sent, no
`Transfer-Encoding`, and decode to the identity page; a post's gzipped answer likewise; a HEAD still has no body. With `CAMPFIRE_GZIP_LENGTH=off` the first test
fails (checked). Two port tests that asserted chunking now assert the length (a buffer in `AdapterTests`; a frozen page in `RoomsTests`, still chunked with the
cache off); a stream and a file stay chunked. `bin/verify`: 1,066 tests, 1,059 passed, 7 skipped, 0 failed; the App tests also pass with
`CAMPFIRE_READ_CACHE=off`. Not run: `bin/pixel-parity` (the decoded bodies are unchanged: `bench/run`'s probe finds them equal to Rust's on every probed route), the
differentials (`bin/kit-differential http` compares headers with the Rust kit and would show this as a deliberate difference).

## Measurements

Tier 2 (mounted build, one rep, same build with the setting off and on; `oncrack-c3/t2-length-off`, `t2-length-on`, logged):

| Workload | c=1 off -> on | c=16 off -> on (CPU us) |
|---|---|---|
| room page | 11,790 -> 13,179 | 100,974 (32.1) -> 122,477 (30.7) |
| messages page | 11,899 -> 13,420 | 102,770 (30.9) -> 122,358 (29.9) |
| sidebar | 12,970 -> 15,674 | 115,253 (26.8) -> 137,123 (26.8) |
| search | 12,785 -> 14,071 | 72,058 (31.4) -> 136,805 (27.3) |
| post a message | 3,112 -> 3,100 | 11,819 (257.6) -> 13,049 (233.5) |

Tier 3 (the rebuilt image, all five workloads at c=1 and c=16, 3 reps, warm-up until flat; every response 2xx with 0 connection errors in 30 runs; decoded bytes
equal Rust's on every probed route; post rows equal the 2xx answers). Raw: `oncrack-c3/tier3/` (`vs-stored.md`), logged in `oncrack-log.jsonl`. Ranges are min-max of the 3 reps.

| Workload | c | onCrack req/s | / F# port | / Rust | CPU us/req | port | Rust | C1/C2 (req/s) |
|---|---|---|---|---|---|---|---|---|
| room page | 16 | 124,328 [121,730-125,408] | **3.08x** | **4.34x** | 30.2 | 93.6 | 122.4 | 102,722 |
| room page | 1 | 13,548 | **1.78x** | **2.09x** | 143.1 | 208.7 | 142.1 | 12,004 |
| messages page | 16 | 124,328 | **3.29x** | **4.14x** | 29.8 | 102.2 | 114.2 | 101,682 |
| messages page | 1 | 13,837 | **1.67x** | **2.03x** | 142.2 | 199.3 | 139.2 | 12,032 |
| sidebar | 16 | 138,274 | **3.68x** | **4.90x** | 26.9 | 101.8 | 123.2 | 112,827 |
| sidebar | 1 | 16,349 | **2.04x** | **2.64x** | 122.9 | 181.0 | 149.0 | 13,600 |
| search | 16 | 136,313 [135,560-136,920] | **4.00x** | **5.12x** | 27.0 | 107.3 | 123.9 | 72,311 |
| search | 1 | 14,677 | **2.42x** | **2.60x** | 136.0 | 315.1 | 158.3 | 12,885 |
| post a message | 16 | 13,249 | **1.49x** | **1.85x** | 231.2 | 353.0 | 385.6 | 12,953 (C2) |
| post a message | 1 | 3,399 | **1.11x** | **1.22x** | 581.1 | 629.1 | 403.7 | 3,123 (C2) |

Geometric means of the five: c=16 **3.84x Rust, 2.95x the port** (C1: 2.75x Rust, 2.11x the port, at c=16); c=1 **2.04x Rust, 1.75x the port** (C1: 1.78x Rust, 1.52x the port).
Search at c=16 went 72,311 -> 136,313 (+88%) at 27 instead of 31 us CPU; the sidebar's 112,827 -> 138,274. At c=1 every page gained 12-20%.

## Checked because it looked too good

Search c=16 almost doubling is the biggest number in this round, so: the same build with `CAMPFIRE_GZIP_LENGTH=off` gives back the old 72k (tier 2 above, and
in `bench/paths` runs of one build), so it is the setting and not the build; CPU per request fell only 4 us, the rest is the idle cores now being used
(2.28 -> 3.64 server cores); syscalls per request fell from 18.1 to 10.0 and CPU migrations from 16.3k to 0.96k per run (`PERFSTAT=1 bench/paths`); every response
is 2xx, the load generator would error on a length that disagreed with the bytes (0 errors), and the tests compare decoded bytes with the identity page. The
effect is partly the load generator's (hyper reads a chunked body in more steps), but a client gets one packet less per response either way, and the
c=1 gains (a single connection, 12-20%) show it is not only a c=16 artifact. It does not change what the post workload does beyond its small gzipped answer.

## Deferred

- Search pages are invalidated by any change in any of the user's rooms; a precise rule needs the tokenizer (above).
- The FTS plan on very large databases (sort of all matches; see above for why it was left).
- Pages in parts on the miss path and static files and streams are still chunked (no measurable effect where CPU is the limit; not tested for static assets).
- `bin/pixel-parity` and the differentials on this build.
