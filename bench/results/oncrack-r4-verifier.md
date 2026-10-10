# Round 4 adversarial verify

Scope: `git log 37c5988..43e7be3`, the round 4 work: A7, R4.1-R4.5. Branch `crack`; nothing pushed. The Mac was shared with other sessions throughout (load 6-21), and free disk fell from 14 GB to 4-7 GB during the session because of other sessions' Docker work. So after the reliability runs I stopped all Docker work (no image builds, no `bin/linux-tests`, no pixel parity). Raw data is in `bench/results/oncrack-r4-verifier/`.

## Verdict

Four real defects found, each fixed with a test that fails without the fix:

| # | Defect | Severity | Commit |
|---|---|---|---|
| 1 | One room member could make every post in a room wait the full 2 s. It took one socket that subscribed with a reordered identifier (a group of its own) and read slowly. Without the identifier trick, N+1 slow sockets in a room of N live subscribers did the same. | High (denial of service by one user) | `5c52709`, refined in `72fba92` |
| 2 | The 256 MB byte budget was per group, and nothing bounded the total. Every room, private stream and client-chosen identifier holds its own copy of the frames. | High (memory denial of service) | `4a77ba4` |
| 3 | A remote disconnect (ban, sign-out, revoked membership) went out *after* up to 64 frames published after it. The connection read its streams before its internal channel. | Medium (a revoked client receives later messages); present since the port, made likelier by R4.5's log | `669b62f` |
| 4 | `Broadcasts.AwaitRoom` and the gate in `MessagesController#create` had no tests. | Gap | `5c52709`, `72fba92` (`CablePressureTests`, 5 tests) |

Also added: a revocation test that commits through a separate process (`11021cb`), and a kill -9 crash test followed by a Rails round trip (`crash-rails.sh`). Both pass with nothing to fix.

The final `bin/verify` with `CAMPFIRE_REQUIRE_SEED=1` passed: 1,188 tests, 0 failed, 12 skipped. The 12 skips are the ones that existed before: Linux-only gather and stall tests, the Linux-only transparent-huge-pages test and the reference recorder. It ran in three parts because one foreground call is capped at 10 minutes:
- `bin/verify Ruby RailsCompat Routes Assets RichText Storage Views Kit` and `bin/verify Db Cable` at `72fba92`.
- `bin/verify Cable App` again at `669b62f` (the last change touches only `Connection.fs`).

Each part is the Release build with warnings as errors, then the tests.

## 1. The posting pressure gate (R4.5, `7e83a8d`)

**Attack.** `Hub.Congested` answered "congested" if *any* group of the room's broadcasting had more than half of *its* subscribers more than 2,048 frames behind.
- A group is the subscribers of one channel identifier, byte for byte, and the client writes the identifier. The same Turbo subscription with its keys in another order is a group of one.
- A socket that reads a few hundred bytes a second makes progress, so the 30 s stall never cuts it. The 256 MB budget cuts it only after about 26,000 messages.
- So one member with one such socket made every post in the room wait the full 2 s once 2,048 frames had gone by.
- Without the identifier trick, N+1 slow sockets did the same in a room of N live subscribers. No per-user connection cap stops that.

**Fix.**
- The verdict is counted over all of the broadcasting's groups.
- A subscriber whose connection has waited `Hub.ReaderBoundAfter` (250 ms, `CAMPFIRE_CABLE_PRESSURE_READER_MS`) or longer on one socket write counts as *not behind*. `Connection.run` stamps `Wake.WriteWaitSince` around a send the socket did not take at once.

The first version (`5c52709`) left such subscribers out of the count altogether. Measured on `bin/reliability`, that closed the gate *more* often, giving 10-15% fewer messages/s. On those profiles the connections that wait on their sockets are mostly near the head, so dropping them raised the share of subscribers that are behind. `72fba92` counts them as not behind. The verdict can then only be R4.5's or more open.

**Is the wait bounded, does it hold anything, is every post written and broadcast once in order?** Yes, by test (`tests/Campfire.App.Tests/CablePressureTests.fs`):
- With nobody behind, or no subscribers, `AwaitRoom` is already complete and the post takes under 1 s. `PressureWaits` stays 0.
- With 3 of 3 subscribers 2,100 frames behind, a post waits 1.8 to 4 s. It is stored once and broadcast once, after the backlog, to every subscriber.
- The post goes within 1.2 s of two subscribers catching up at 0.3 s.
- 24 posts wait at once, more than the read pool's connections. Beside them, a page read, a post into another room with its broadcast, and a bare `WriteBlocking` all finish in under 1 s. So the waiting posts hold no read connection, no writer or group commit, and no place in `BroadcastOrder`: the ticket is taken after the wait. Afterwards each of the 24 is stored once and broadcast once, in id (commit) order.
- One never-reading subscriber under a group of its own, plus four whose connections have waited 1 s on their sockets, beside three readers that keep up: not congested, and a post takes under 1 s.

Mutations:
- Removing the `AwaitRoom` call from `create` fails 3 of the 5 tests.
- The old any-group verdict fails the lone-group Pubsub test.
- Counting waiting connections as behind fails 2 tests.
- Never stamping the wait in `Connection.run` fails the end-to-end DirectTests test. In that test, two of three real clients stop reading during 40 MB of broadcasts; the room is not congested, and they then read all 5,000 frames in order.

**Inert?**
- Under upstream's benchmark profiles it is inert: there the posters' room has no Cable subscribers, and `Congested` is false without a stream.
- Under normal traffic it is inert: subscribers that keep up never wait (test above).
- Under `bin/reliability`'s saturated `cable_heavy` (64 closed-loop posters) it engages, as designed. In run 15, post durations from the front server's log were p50 44 ms, p99 343 ms and max 574 ms, so no post waited the full 2 s.
- In `cable` (4 posters), posts took p99 19 ms and max 71 ms.

The new gauge (`Broadcasts.PressureWaits`, `PressureWaitTicks`, and a warning at most every 5 s) did not show in the harness's captured logs. They hold only the front server's request lines, so I could not count the gate's waits there.

**Reliability A/B** (`reliability/table.md`; same session, image `campfire-oncrack:app` = R4.5 `f5429fc` against a derived image of HEAD's publish). Every run had 1000/1000 subscribed, 0 disconnected and every post delivered.

| runs | cable msgs/s | cable_heavy msgs/s |
|---|---|---|
| R4.5 image (2, 3, 6, 12, 13) | 435, 466, 476, 370, 332 | 572, 516, 570, 455, 381 |
| `5c52709` (1, 4, 5, 8, 9) | 337, 418, 436, 399, 391 | 384, 491, 498, 486, 492 |
| `5c52709` with the exclusion off (7, 10) | 462, 442 | 490, 577 |
| final (11, 14) | 366, 385 | 436, 487 |

Runs 11-14 alternated new, R4.5, R4.5, new at load 10-12. The final version is level with R4.5 within this host's noise.

**Residual.** An attacker can still close the gate if their sockets outnumber the room's live subscribers *and* each reads fast enough never to wait 250 ms on a write (about 2.6 MB/s per socket for a 64-frame batch of 10 KB frames) while still falling 2,048 frames behind. That is a room posting more than 260 messages/s, which is already the saturated case the gate exists for. Opening many sockets also costs the server real fan-out CPU, which is ordinary load.

## 2. The byte budget across rooms, private streams and identifiers

**Bound before.** `CAMPFIRE_CABLE_LAG_BYTES` (256 MB) bounded one group. A group is one broadcasting under one identifier, with its own copy of every frame (the identifier is inside the frame). Nothing bounded the number of groups:
- every room and every user's private streams;
- 64 subscriptions per connection, each able to use a distinct identifier variant;
- unlimited connections.

So the total was groups x 256 MB. One member with ten slow sockets in a room posting 10 messages/s of 10 KB frames pins about 64 MB/s, up to 160 GB. Action Cable has no bound either. But R4.5 says memory is bounded, and for a production server that bound has to be global.

**Fix.** `CAMPFIRE_CABLE_HUB_BYTES` (default 1 GiB) sets `Hub.TotalBudget` over all logs together.
- A broadcast that finds the hub over the total queues one pool item, at most every 10 ms. The heartbeat's `Trim` does the same, for a hub nobody publishes to any more.
- The pool item cuts the subscribers in the oldest chunk of the log with the most bytes before its newest chunk, repeating until the hub is under. Those subscribers are the furthest behind anywhere.
- They get `reconnect: true`, as with the group budget.

Tests:
- Nineteen slow groups across ten rooms and nine identifiers, each under its own 1 MB budget, are held to a 2 MB total. The readers in every room still get all 600 frames in order. As a control, with no total nobody is cut and the hub holds 11 MB.
- The furthest-behind subscriber is cut first, in another room, and the nearer one reads all 500 frames.

Mutations: never shedding fails both tests, and shedding the smallest log first fails both.

**Residual, deferred.** A group's newest chunk (up to 256 frames, about 2.5 MB of room frames) is never shed. It is held even when every subscriber has read it. So the floor above the total is up to 2.5 MB per group. A client that reads everything but subscribes 64 times with distinct identifiers holds about 160 MB per connection. That is bounded by connections x 64 x 2.5 MB but not by the total, and it existed with rounds 1-3's per-group rings too. The fix is to share the payload across groups and keep only the identifier prefix per group (gather writes already send header and payload separately), or to cap distinct identifiers per broadcasting per user.

## 3. The Cable write path

- **Remote disconnect order (fixed, `669b62f`).** In each turn, `Connection.run` read its streams, then its internal channel, and sent what the streams gave before the goodbye.
  - A ban, sign-out or membership revocation followed by posts that land before the connection wakes sent the revoked client up to 64 frames published after its revocation. That ordering is common under load and certain inside one `WakeBatch`.
  - The new DirectTests test publishes a disconnect then 100 frames inside one `WakeBatch`. The client's next frame was `{"after":0}`; it is now the disconnect.
  - Now the internal channel is read first and a disconnect ends the turn. Frames the streams held from before it are dropped too, since the connection is closing for a revocation.
- **Slow and stalled readers, order, loss and duplication.**
  - New: two of three real connections stop reading during 40 MB, then read all 5,000 frames in order (above).
  - Existing and passing: the 100,000-frames-behind reader; chunk edges; 8 stalling reader threads; the merge order and starvation; the stall cut and the slow reader not cut (Linux only, not run, see below); "many connections, each sees every frame once and in order" (40 clients, a quarter never answering the probe); a reader that stops then reads again; unsubscribe stops delivery; lagged subscribers disconnect with reconnect.
- **Not newly attacked:** a client disconnecting mid-batch (a failed send ends the loop and disposes every reader; read, not tested) and reconnection.

## 4. Fresh authorization (R4.3)

- **New test** (`ForeignWriteTests`, `11021cb`): the sqlite3 shell, a separate process with its own POSIX locks and its own `-shm` mapping, as Rails would be.
  - Each round, right after a cached hit, it revokes David's session token or his All Talk membership, then restores it. Meanwhile Jason reads without pause, so the checks' transactions are held.
  - Thirty rounds in each of four configurations: fresh and cached authorization, in process and fronted. Every request after a revocation was refused and every request after a restore was served.
  - The same classes plus `FreshAuthTests` and `CablePressureTests` (18 tests) also pass with `CAMPFIRE_TEST_FRONT=1` and with `CAMPFIRE_FRESH_AUTH=0`.
- **Finding (no defect):** the test still passes with R4.3's hold mutated to never renew (`Prepare` comparing "held at all" instead of the stamp), the mutation `CheckHoldTests` catch.
  - A foreign commit makes `Versions.Sync` drop every cache, so the request after it is a miss and never asks the held checks.
  - The held transactions answer only hits, so their correctness rests on the Db-level `CheckHoldTests` (in `bin/verify`, passing) and on the counters for the writer's own commits.
  - Nothing found that a hit can be served on across a revocation.

## 5. Durability, the search index, and Rails reading what onCrack wrote

The image is R4.5's `f5429fc`; nothing since touches the database path. R4.4 changed no default.

`killtest.py` was run four times in colima (`killtest.log`, `crash-rails.log`):

| kill after | acknowledged | lost | duplicated | no index row | room page after restart |
|---|---|---|---|---|---|
| 3 s | 2,644 | 0 | 0 | 0 | 200, newest post shown |
| 5 s | 6,317 | 0 | 0 | 0 | 200, newest post shown |
| 8 s | 11,672 | 0 | 0 | 0 | 200, newest post shown |
| 15 s | 19,612 | 0 | 0 | 0 | 200, newest post shown |

Each run posts from 16 threads (group commit on) and sends SIGKILL to the container mid-run. The 8 s run had 13 posts stored that were never acknowledged, which a kill legitimately produces. The traceback in `killtest.log` is the script's second invocation in its first call: the script stops the container when it ends, so it found nothing to connect to. It is not a finding.

`crash-rails.sh` continues after the 5 s kill:
- `pragma integrity_check` ok and the FTS5 `integrity-check` ok. `MATCH 'kt<run>*'` finds 6,317 of 6,317 stored posts.
- Rails (`campfire-reference:app`, `bin/rails runner` on the same storage) found 6,317 through `Message.search`. It then created a post of its own, which its search found.
- onCrack, restarted on that database, showed Rails' post on the room page and found it through `/searches`.

## 6. A7 (R4.0)

I reviewed it. The fix is test support only: the cookie jar's deleting forms are read from attributes, not from a "1970" substring. `CookieJarTests` pass in `bin/verify`. I made no further attack: the cause is deterministic, not timing.

## Not run, and why

- **`bin/linux-tests Cable`.** The gather, stall and acknowledged-byte tests skip on macOS. It builds a private copy in the toolchain image, and the Mac was at 4-7 GB free, under the 12 GB floor, so I made no further Docker builds.
- **Pixel parity.** Nothing renders differently: no HTML, CSS or frame content changed, only when and to whom frames go.
- **Upstream's `bin/benchmark` session.** Not re-run, so round 3's multiples are not restated.
- **`bin/db-differential`.** No model or schema change. `crash-rails.sh` covers Rails reading and writing the database.
- **`bin/clean-docker`.** At the end it refused to run: another session's containers (`samenlx`, `samenpg`) were running. I removed my own image (`campfire-oncrack:verify`), publish directory and candidate container, ran `bin/clean-parity` and trimmed the VM disk (5 GiB).
