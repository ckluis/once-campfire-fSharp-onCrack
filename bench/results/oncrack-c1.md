# onCrack unit C1: the versioned read cache

Date 2026-10-07, branch `crack`, commits `a7bdc1b` (version counters), `651c5f5` (page cache), `23cf334` (authentication through the cache).
Image `campfire-oncrack:app` `sha256:75caf211cc37`, label `revision=23cf334`; `campfire-fsharp:app` (the port) untouched.

## What it is

**Version counters** (`src/Campfire.Db/Versions.fs`): a global counter, one per room, one per user, one for sessions. The writer connection
carries TEMP triggers (they live in the connection, never in the database file, so the schema stays the reference's) on every table the
pages read, calling `campfire_bump(kind, id)`:

| Table | Marks |
|---|---|
| messages | its room |
| boosts, and rich texts and attachments of a message | the message's room (global if the message is gone) |
| rooms | updated: the room; created or destroyed: the room and global |
| memberships | added or removed: the room and the user; updated (involvement, unread, connections): the user only, unless it moved |
| searches, push subscriptions | the user |
| sessions | sessions |
| accounts, users, bans, webhooks, blobs, variant records, other rich texts and attachments | global |
| the FTS5 search index (no triggers possible) | marks the message's room itself (always inside the job that already did) |

**The rule (invalidation):** the first mark of a counter in a write job makes it odd, before the row changes; the job's end (after the
commit and the after-commit work, before the caller's task completes) makes it even, one past. A reader takes its counters before its first
query, keeps the page only if all were even and are unchanged when it finishes, and serves a kept page only while every counter equals the
kept value. So nothing is served across a committed change, a writer reads its own write, and a page read while a write is in flight is never
kept under values a later request can match. A database opened without the full schema gets no triggers, and the cache stays off.

**Page cache** (`src/Campfire.App/ReadCache.fs`): the room page, the messages page, the sidebar and search. The whole body is kept frozen
(`src/Campfire.Kit/FrozenPage.fs`): the parts with their ETag and the finished gzip member, worked out once; a hit is a copy of the stored
member. The key starts with the user's id (never shared across users), then everything the render reads from the request: route, full URL,
scheme/host/port, Turbo-Frame, Referer, User-Agent, the `last_room` cookie. Flash present: not cached. Dependencies: room and messages pages
on global, the user and the room; sidebar and search on global, the user and every room the user is in (the room list read after the user's
counter is taken). On a hit the controller still does what it does besides rendering (`last_room` cookie, `fresh_when` and its 304, the format
check, the layout's `Link` header). Bounded at 64 MB (`CAMPFIRE_READ_CACHE_MB`) in two generations, one store per database;
`CAMPFIRE_READ_CACHE=off` turns it off.

**Authentication**: the session by token under the sessions counter, the user by id under global. With both, a cached page runs **no SQL**.

## Tests that try to break it

`tests/Campfire.Db.Tests/VersionsTests.fs` (7) and `tests/Campfire.App.Tests/ReadCacheTests.fs` (9). The App tests first check that the page
really came from the cache (the store's hit count moves), then: a post, an edit and a delete on the room page, the older messages page and
search; a boost; read-after-write by the poster over HTTP, five times; David and Jason on the same URL get their own pages, Kevin (not a
member) is redirected and gets 404 on the messages page, David can't get Kevin and Bender's direct room; a membership removed takes the room
off the page, messages page, sidebar and search at once; a ban takes the user's messages off cached pages and signs him out (his cached
session no longer authenticates); a rename shows in a direct room's title, custom styles on the room page; involvement changes the user's own
sidebar and not another's; six readers racing a poster (40 posts) never get a page missing the last acknowledged post (100+ pages checked,
some from the cache). The Db tests check what each change marks, odd inside the write and its after-commit hook, even after a rollback, and a
reader racing a writer never sees two different counts under one unchanged even counter. **All pass with the cache on and with it off**
(the off run is the oracle that the tests' expectations are the app's, not the cache's). `bin/verify`: 1,054 tests, 1,047 passed, 7 skipped,
0 failed. One port test changed: "pages of messages go out in parts" counted more than 40 body writes; a frozen page's plain body is now one
write.

Not run in this unit: `bin/pixel-parity` (63 minutes; the bodies are byte for byte the port's, which `bench/run`'s probe confirms below, so
the screenshots can't differ, but the gate was not run), the differentials.

## Measurements

Tier 2 (mounted `23cf334`, one rep, c=16), A/B on the same build with `CAMPFIRE_READ_CACHE=off`, which isolates the cache from the triggers:

| Workload, c=16 | cache on req/s (CPU µs) | cache off (CPU µs) | C0, unchanged fork |
|---|---|---|---|
| room page | 95,310 (32.2) | 39,379 (90.6) | 38,994 (91.6) |
| messages page | 103,268 (30.7) | 42,134 (84.8) | 41,859 (84.9) |
| sidebar | 110,523 (27.3) | 38,162 (94.6) | 37,894 (95.1) |
| search | 71,472 (31.4) | 33,729 (108.3) | 33,931 (107.5) |
| post a message | 8,735 (354.5) | 8,626 (364.0) | 8,566 (359.9) |

The triggers cost nothing measurable on posts (cache off is C0 within noise).

Tier 3 (the rebuilt image, all five workloads at c=1 and c=16, 3 reps, warm-up until flat; every response 2xx with 0 connection errors in
30 runs, decoded bytes equal Rust's on every probed route, post rows equal the 2xx answers). Raw: `oncrack-c1/tier3/` (`report.md`,
`vs-stored.md`), logged with `bench/quick log` (`oncrack-log.jsonl`). Against the stored medians of `phase7-final` (Rust and the F# port
measured in one session; not re-measured here); onCrack's numbers are onCrack's, not a like-for-like port result:

| Workload | c | onCrack req/s | / F# port | / Rust | CPU µs/req | port | Rust |
|---|---|---|---|---|---|---|---|
| room page | 16 | 102,722 | **2.54x** | **3.59x** | 32.4 | 93.6 | 122.4 |
| room page | 1 | 12,004 | **1.58x** | **1.85x** | 151.1 | 208.7 | 142.1 |
| messages page | 16 | 101,682 | **2.69x** | **3.38x** | 29.8 | 102.2 | 114.2 |
| messages page | 1 | 12,032 | **1.45x** | **1.76x** | 153.6 | 199.3 | 139.2 |
| sidebar | 16 | 112,827 | **3.00x** | **4.00x** | 26.6 | 101.8 | 123.2 |
| sidebar | 1 | 13,600 | **1.70x** | **2.20x** | 137.7 | 181.0 | 149.0 |
| search | 16 | 72,311 | **2.12x** | **2.72x** | 31.1 | 107.3 | 123.9 |
| search | 1 | 12,885 | **2.13x** | **2.28x** | 144.7 | 315.1 | 158.3 |
| post a message | 16 | 8,631 | 0.97x | 1.20x | 357.3 | 353.0 | 385.6 |
| post a message | 1 | 3,026 | 0.99x | 1.09x | 635.3 | 629.1 | 403.7 |

Geometric means of the five: c=16 **2.75x Rust, 2.11x the port** (C0: 1.31x Rust); c=1 **1.78x Rust, 1.52x the port** (C0: 1.13x).
Posts are unchanged (they are writes; group commit is the next lever). Warm-up hit its 90 s maximum on the messages page in 3 of 6 runs.

Investigated, not explained: **search at c=16** runs 72k req/s at 31 µs CPU, which is 2.2 of the 4 server cores; the other cached pages at
the same CPU per request reach 100-113k (3.3-3.6 cores). Its page is smaller (9.7 KB gzipped against the room page's 24 KB), its hit path is the
same code, and its p99 is no worse (0.37 ms). Something waits rather than works; not found within the unit. Nothing else looked too good for
what it is: a hit does no SQL and no render, and its CPU per request (27-32 µs) sits 6-12 µs above the port's `/up` (20.5 µs), the floor of any
request through Kestrel, the kit and the request log.

## What remains on the request path of a cached page

Kestrel's parse and the route table; the kit's `Ctx`, params and cookies; the signed `session_token` cookie's HMAC; the Rails session cookie's
decryption (the flash check, which the uncached page also does); `set_version_headers`; the cache key (a string of about 300 bytes) and its
lookup under a lock; 3 counter reads (or one per room of the user's, for the sidebar and search); the `last_room` cookie when it changes;
headers (`Link`, ETag from the memo, `Cache-Control`, `Vary`); one copy of the stored gzip member into the response pipe; the request log
line. At c=1 the CPU per request (138-154 µs) is mostly the thread pool spinning between requests, as the port measured.

## Deferred

- The search c=16 ceiling (above).
- A browser-shaped hit rate: the key includes Referer and the full URL, so a browser's navigation (Referer changes) gets fewer hits than the
  benchmark's identical requests; correct, but the cache could ignore inputs a page provably doesn't render.
- Message fragments keep Rails' fragment-cache behavior (a rename doesn't reach a cached message); unchanged from the port.
- Global bumps from uploads (blobs, variants) invalidate every page once per upload.
- `bin/pixel-parity` and the differentials on this build.
