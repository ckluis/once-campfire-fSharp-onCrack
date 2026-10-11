# once-campfire-fSharp-onCrack

**This repository is onCrack, not the port.** Read `plans/oncrack.md` first: the UI must stay pixel-identical
(the parity harness's screenshot layer) and correct, but the work per request may differ from Rails and Rust
in any way that makes it faster (caches, group commit, AOT, Datastar). Everything below about matching Rust's
implementation applies to the port this was forked from; where it conflicts with `plans/oncrack.md`, the plan
wins. The image is `campfire-oncrack:app` (`bench/run`'s `oncrack` app, `bench/quick`'s default and the parity candidate's default here);
keep `campfire-fsharp:app` (the port) untouched for comparison.

**Fast inner loop (Chris, 2026-10-08): incremental checks should take 1-3 minutes, not 10-20.** Tier 3 and the
re-baselines stay full-length; the inner loop gets faster by removing setup, not by measuring less carefully:
- **A/B in one warm process:** put a change behind a runtime switch (env var read per request, or an admin-only
  toggle) and alternate old/new by window in the same container: no restart, no re-warm-up, and host drift cancels.
- **AOT for direction:** the `NATIVE_AOT=true` build has no JIT warm-up, so it reaches steady state at once; use it to
  see which way a change moves CPU per request, then confirm with the JIT image at tier 3.
- **CPU per request is the inner-loop signal** (`bench/quick cpu`, 2-3 s windows), not req/s over 8 s x 3 reps.
- **Reuse sign-ins:** snapshot the realistic workloads' 525 signed-in sessions into the seed copy once and reuse the
  cookies instead of signing in every rep (25-31 s each).
- **Targeted pixel parity:** `bin/pixel-parity --fast --only <states the change can affect>` while iterating; the full
  run on every seed is the round verifier's job.
- **In-process harness for logic questions** (is the hit path cheaper, did the post pipeline shrink): host the app in a
  test server, drive requests directly, report CPU and allocation per request, seconds per run.
Disk: run `bin/clean-parity` with `bin/clean-docker` at every gate (old parity reports reached 5 GB in round 2). The full gate is `bin/pixel-parity` on every seed (round 3's run: the default seed in twelve `--only` slices, one foreground call each, `bin/clean-docker` between them; `bench/results/oncrack-r3-pixels.md`); it deletes a `parity/core*` dump after every compare and prints the VM's free space, but the Mac's floor (12 GB) is yours to watch.
If one of these tools doesn't exist yet, building it is part of your unit. Record the loop time before and after.

**onCrack's gates and scoring** (unit C0): `bin/pixel-parity` is the one-command "the UI is identical" check (the parity harness's
screenshot layer, per seed; see its header for the retry of cells the harness could not capture). `bench/quick` runs onCrack only and
`bench/quick compare DIR` scores it against the stored Rust and F# port medians of `bench/results/phase7-final/`; `bench/quick log` appends to
`bench/results/oncrack-log.jsonl` (the port's own `phase7-log.jsonl` is history) and rebuilds `index.html`. Its hero is the current-upstream
comparison (`site/build.py`'s `hero`, from `bench/results/oncrack-r3-fresh-auth/upstream-*`: fresh authorization, two normal sessions pooled; round 2's cached-decision sessions are the panel `p-upstream`); the climb chart (`bench/progress/climb.py`: onCrack over the pinned
Rust `ccece30`, starting from the port's final result) is the panel "The climb against pinned Rust", and the port's dots are in another. `bench/run --apps
reference,rust,fsharp,oncrack` measures all four in one session (`fsharp` is the port). Tier 3 of an unchanged image must land within noise of
the port: `bench/results/oncrack-c0.md`.

**Group commit** (unit C2, `bench/results/oncrack-c2.md`): the writer runs every write already queued (up to 64) in one transaction, a
savepoint each, one COMMIT, then their after-commit work in one more transaction (`Writer` in `src/Campfire.Db/Database.fs`). Every write
still commits before its caller hears back. A write closure must do database work only (non-database effects go in after-commit hooks): a
group whose transaction breaks runs again write by write. `CAMPFIRE_GROUP_COMMIT=off` restores one write per transaction;
`tests/Campfire.Db.Tests/GroupCommitTests.fs` holds the writer to form groups and compares a grouped run with a one-by-one run. A post's broadcast
goes out in commit order (`BroadcastOrder` in `src/Campfire.App/Channels/Broadcasts.fs`): messages#create takes a place in line in its write's
after-commit hook and publishes through it once rendered, giving it up in a `finally`; a place nobody fills is skipped after a second. Posts with
an attachment, bots' posts and webhook replies broadcast at once, as before.

**Content-Length on gzipped answers** (unit C3, `bench/results/oncrack-c3.md`): a gzipped buffer or frozen page goes out with the length of its
gzip member (made, or fetched from the digest-keyed gzip cache or the frozen page, before the headers) instead of chunked; streams, files and pages in
parts that are not frozen stay chunked. A chunked answer cost a second send for the terminating chunk, which on a cached hit (27-32 us of CPU) doubled
the round trip at c=16. `CAMPFIRE_GZIP_LENGTH=off` restores chunking; `bin/kit-differential http` accepts the length where Rust's kit chunks only when it is exactly the gzip member's (its `fuzz.py selftest` checks that filter); `bench/paths` measures arbitrary GET paths (with `HEADERS=1`, `SIZES=1`, `PERFSTAT=1`).

**Native AOT** (unit C4, `bench/results/oncrack-c4.md`): `docker build --build-arg NATIVE_AOT=true` makes `campfire-oncrack:aot` (cold start ~95 ms, idle 22 MB, 36% smaller image; c=1 +14%,
c=16 -10% against the default; no HTTP/2-over-cleartext). An opt-in: the default image stays JIT + ReadyToRun. `bench/boot` measures cold start and idle memory; tier 2 AOT builds are `AOT=1 bin/publish-mounted DIR`.

**Cable fan-out** (unit R2.1, `bench/results/oncrack-r2-cable.md`): on plain TCP a Cable connection writes to its socket itself, not through
Kestrel's upgraded stream. After the welcome it pings with a random payload (the probe) and holds its writes until the pong echoing it proves
Kestrel's pipe is empty (`Connection.run`, `Writer.Detach`; `CAMPFIRE_CABLE_DIRECT=off`). `WakeBatch` wakes a post's subscribers once for both
of its broadcasts, and `BroadcastOrder` holds the wakes while later posts in line are still rendering, up to `CAMPFIRE_CABLE_HOLD_US` (1000).
Turbo Stream frames leave `<`, `>` and `&` unescaped (`Config.CompactJson`, `CAMPFIRE_CABLE_COMPACT_JSON=off`; the Rails-golden tests run with
it off). Any WebSocket client in a test or a bench must answer pings, as a library does, or the connection waits 2 s and stays on the stream.
The cable suite reports the server's CPU per delivery and both sides' cores busy (`bench/lib/procmem.py`). With round 2's tungstenite client the load generator was
the limit at 1,000 clients (3.85 of 4 cores); R4.1's raw client (below) is not. `bench/cable/perf` profiles a saturated fan-out (`--loadgen` for the
client side). A tier 2 cable loop is about 2.5 minutes: `bin/publish-mounted`, then `bench/run` with `SUITES=cable`. The SSE prototype
(`bench/cable/run --sse`) is measured and left off.

**The cable load generator** (unit R4.1, `bench/results/oncrack-r4-fanout-baseline.md`): `loadgen cable` now defaults to `--client raw`, epoll loops with
no WebSocket library (`bench/loadgen/src/rawcable.rs`, `--threads` 3; `--client tungstenite` is what rounds 1-3 measured with and their stored cable
numbers are not comparable). At 1,000 clients it uses 1.8-2.7 of the 4 cores and the servers are the limit (3.8-3.9 cores). The saturated phase keeps at
most `--window` (128) messages posted and not yet delivered to every client: without it a client that keeps up lets the posters outrun the fan-out, the
256-frame stream rings (rounds 1-4; R4.5 replaced them with a byte-bounded log, `CAMPFIRE_CABLE_LOG=ring` keeps them) lap the slowest subscribers and the server closes them, so messages go missing; check `posted == complete` and `client.closed_midrun
== 0` in any cable result. `bench/cable/ab` alternates load generator variants against one running app; `CABLE_ARGS` passes loadgen arguments from
`bench/run`; `CABLE_SENDS=1` counts the app's send syscalls (a pass of its own); `bench/run` raises the soft descriptor limit (2,000 clients). The baseline
for R4.2 (100/500/1,000/2,000 clients, Rust f9dca47, the port, onCrack, one session) is in that file; the host drifts 25-30% over 20 minutes, so judge a
change against a control from its own session.

**Gather writes** (unit R4.2, `bench/results/oncrack-r4-fanout.md`): on a detached connection (Linux, plain TCP) `Writer.Send` hands the kernel the
frames' shared payload arrays where they are, one non-blocking `sendmsg` over header and payload pairs (`Socket.fs`: `Sendmsg`, pinned by a `fixed`
local per payload in a recursion, a thread-static `GatherScratch`), instead of copying them into a pooled send buffer first (that copy was 16% of the
server's CPU at 1,000 clients). What the socket does not take (`EAGAIN`, a partial send) is copied and finished by `FinishSend`, with the write timeout.
`CAMPFIRE_CABLE_GATHER=off` copies as before; elsewhere (macOS) the copy is always used, and the gather tests skip: `bin/linux-tests Cable` runs them.
.NET's own `Socket.Send(IList<ArraySegment>)` was tried first and discarded: it makes a GC handle per segment per call (about 9% of the CPU, as much as
the copy), and on macOS with `Blocking <- false` it made an unrelated test flake. `bench/cable/perf` takes `KEEP_SCRIPT=1` (keeps the call chains);
`bench/results/oncrack-r4-fanout/breakdown.py` splits them by layer; `pair.sh` and `table.py` there run and print one tier 2 A/B run.

**Cable reliability** (unit R4.5, `bench/results/oncrack-r4-reliability.md`, plan `plans/r4-reliability.md`): a slow reader is never silently dropped, and
memory stays bounded. Action Cable queues without bound per connection and cuts nobody for being slow; onCrack keeps what one group's subscribers have not read in
one shared log, with a bound.
- **The log** (`Pubsub.fs`, `LogGroup`): an append-only list of chunks (`Config.StreamCapacity`, 256 frames each) shared by a group's subscribers; each subscriber
  is a cursor (chunk, index) and a chunk nobody is in is left to the GC. The group's head is the oldest chunk any subscriber is in (one pass over the subscribers
  per chunk, or when over budget, and the heartbeat calls `Hub.Trim`). When the log held behind the head is over `CAMPFIRE_CABLE_LAG_BYTES` (256 MB, about 26,000
  messages: a message's frame is about 10 KB, not 1.4 KB; 64 MB cut 90% of a saturated room) the subscribers in the oldest chunk are marked lagged and removed, and a
  thread pool item wakes their connections (they send `reconnect: true` and close; the browser treats it as a dropped network and refreshes the room through
  `/rooms/:id/refresh?since=`) and aborts the socket a second later if it has not finished. Gauges: `Hub.RetainedBytes`, `RetainedPeakBytes`, `CutCount`.
  `CAMPFIRE_CABLE_LOG=ring` is rounds 1-4's fixed 256-frame ring (the A/B switch; it also turns the publish order off).
- **Order across streams:** every frame has a hub-wide number from the group's publish; `Connection.Merge` takes the lowest next number among a connection's streams,
  so a deep stream does not starve the others. `CAMPFIRE_CABLE_ORDER=stream` is the old stream-at-a-time order.
- **Stall, not slowness:** a socket write is cut when the peer takes no bytes for `CAMPFIRE_CABLE_STALL_MS` (30,000); on Linux the progress is the kernel's
  acknowledged-byte count (`TCP_INFO`, `Socket.AckedBytes`), looked at every eighth of the time, so a slow reader of a multi-megabyte backlog is never cut; on macOS only a
  completed send counts. A peer that reads nothing is cut at the stall time.
- **Pressure on posters:** a server that takes posts faster than it can fan them out has to slow the posters or cut the clients. `Broadcasts.AwaitRoom` makes
  `MessagesController#create` wait, before it writes, while more than half of the room's subscribers are more than `CAMPFIRE_CABLE_PRESSURE_FRAMES` (2,048) frames
  behind, at most `CAMPFIRE_CABLE_PRESSURE_MS` (2,000) per post; `CAMPFIRE_CABLE_PRESSURE=off` never waits. Nothing waits unless the fan-out is seconds behind (the cable suite at
  window 128 never does). On by default, unlike the plan: with it off, `bin/reliability`'s cable_heavy ends with posts undelivered when the harness stops waiting.
  Round 4's verifier (`bench/results/oncrack-r4-verifier.md`): the verdict counts all of the room's groups together (a client writes its own identifier, so a group can be
  one client) and counts a subscriber whose connection has waited `Hub.ReaderBoundAfter` (250 ms, `CAMPFIRE_CABLE_PRESSURE_READER_MS`) on one socket write
  (`Wake.WriteWaitSince`) as not behind: a slow reader, which waiting posters cannot help. (Leaving such subscribers out of the count altogether closed the gate more often
  under bin/reliability's cable profiles, 10-15% fewer messages a second.) `CablePressureTests` (App) are the gate's tests.
- **The hub's total** (round 4 verifier): a group's budget bounds one backlog, not how many there are (every room, private stream and identifier is a group with its own
  copy of the frames). `CAMPFIRE_CABLE_HUB_BYTES` (1 GiB, `Hub.TotalBudget`) bounds all logs together: over it a pool item (`Hub.Shed`, at most every 10 ms, and from the
  heartbeat's `Trim`) cuts the subscribers in the oldest chunk of the log that would free the most, until under. Each group's newest chunk (up to 256 frames) is never shed.
- **Measuring it:** `bench/reliability/run OUT --apps oncrack --profiles cable --rounds 1` runs upstream's `bin/reliability` (the verification repo's
  `oncrack-reliability-working` branch, its tmpfs copy at `/mnt/cfv` in colima, `--workspace /mnt/cfv/ws`) with the descriptor limit raised (a login shell's 1,024 refused the 64
  posters of cable_heavy beside 1,000 clients: every app's first baseline row said 13 posts and 18 million refusals), a Pss sampler and the Mac's load beside it;
  `bench/reliability/summarize DIR...` prints the table. Its loadgen must be built from the harness's current `loadgen/` (the first baseline's binary had no `disconnected`
  counter). The harness's `oncrack-cached` is the same image with `CAMPFIRE_FRESH_AUTH=0` (`reliability.rb` here maps it to `oncrack`'s runtime; local, uncommitted in that repo).

**Round 4's final run** (`bench/results/oncrack-r4-final.md`, data and scripts in `bench/results/oncrack-r4-final/`, plan `PLAN.md` there): one session per harness profile (the noise rule passed), the cable suite, four hand re-run sets, and PR #6's reliability profiles (incomplete: stopped by the disk floor in round 2 of 3; to finish, `scripts/setup-reliability.sh` inside colima, then `PORT_DONE=1 reliability/session.sh` detached in the VM, about 70 minutes). Tooling kept there: `scripts/hostload-wait.sh NAME pid:PATTERN` (host sampling while a VM-detached session runs, chunks under the Bash tool's ten minutes, stops under 12 GiB free), `reliability/{table,overload}.py`, `pool.py`, `table.py`, `totals.py`, `noise.py`, `cable/{session,session-rest,part}.sh`. Lessons: inside the VM `bench/reliability/run` needs a `colima` shim (the script calls `colima ssh --`); `sync; sudo fstrim -av` returns the VM's freed space to the Mac, a bare `fstrim /var/lib/docker` trims nothing; a killed guard subshell leaves the harness running; the reliability harness copy needs `.git`, `fixtures/default` and a static loadgen built with `--target aarch64-unknown-linux-gnu`; the F# port cannot take the overload profile (its search order fails upstream's contract). Other sessions' caches (a 21 GB Go build cache) can take the Mac under the 12 GB floor mid-session: free your own build output first, never lower the floor.

**Realistic workloads** (unit R2.0, `bench/results/oncrack-r2-bench.md`): the five classic workloads are a 100%-hit benchmark for the read
cache (one URL, one user, no writes). `bench/quick --real` runs `mixed` (16 connections read a room while one posts into it), `spread` (2,112
pages of the crowd seed's 525 users), `spread_mixed` (spread plus one connection posting into rooms of 526 members) and `search_spread`
(524 users x 200 queries), on the crowd seed, at c=16 readers; `bench/lib/realistic.py` signs the people in and writes the load generator's
lanes (`loadgen http --mix-spec`). `bench/quick compare` prints them against the same-session baseline in `bench/results/oncrack-r2-bench/`
(Rails, Rust, the port and onCrack). Run any change to the read cache, the write path or search on them as well as on the five. At the default
64 MB budget onCrack is 0.95x the port on `spread` (the cache thrashes; 512 MB gives 127k). Run them as a part of their own: `bench/run`
refuses to mix them with the classic routes. Load generator headroom (same file): not tool-bound at 4 cores, but it costs 19-23 us a request,
so its 4-core ceiling is about 170-210k req/s.

**The post path** (unit R2.2, `bench/results/oncrack-r2-post.md`): `bench/post-micro` is its tier 1, the whole app in process over a
parity seed copy, N connections posting, windows alternating `Campfire.Db.PostPath`'s switches (each also an environment variable read at
start-up), CPU and allocation per post, slow answers and WAL restarts; about 40 s for two variants at two concurrencies (macOS: direction
only). Outside direct rooms a post marks unread only memberships not yet unread (`CAMPFIRE_POST_UNREAD_SKIP`; `unread_at` is read only for
being set, direct rooms keep Rails' rewrite for the sidebar fragment keyed by `updated_at`). `Tx.OnCommit` runs a post's index row and unread
marks in its own transaction, after every write of the group, with no savepoint (a savepoint makes FTS5 flush a segment per post;
`CAMPFIRE_POST_ON_COMMIT`); `Tx.AfterCommitEffect` is for non-database after-commit work. `Database.Write` runs a write on its caller's
thread when the writer is idle, nothing is queued and `WriteLoad` (requests in flight that may write, counted in the app's dispatch) is one
(`CAMPFIRE_WRITE_INLINE`; tests that hold the writer must do so from a thread of their own); such a write never runs the WAL restart.
Whole bodies gzip with libdeflate (`CAMPFIRE_GZIP_LIBDEFLATE`), and the answer to anything but a GET or HEAD is gzipped once at level 1,
outside the gzip cache (`CAMPFIRE_GZIP_ONCE_LEVEL`). `POST_RATE` paces the posts lane of `mixed`/`spread_mixed` (compare builds reading under
the same writes; a paced run is not comparable with the stored baseline and stays out of the climb log). Open: sustained c=16 posting
stalls 0.8-2.5 s every 20-30 s on the writer's WAL RESTART (`WARN campfire_db: WAL restart took N ms`); R3.4 (below) traced it to the VM's disk.

**The front server's fast path** (unit R2.3, `bench/results/oncrack-r2-front.md`): a read cache hit authenticated by its session cookie
offers its answer (`Campfire.Kit.FastCandidate`, set in `ReadCache.offerFast`); the front server (`FastStore` in `Front/Handler.fs`)
keeps the finished response under every byte of the request the app can read (all headers but `X-Request-Start`, `X-Request-Id`,
`X-Forwarded-For`) and replays it before the proxy headers, routing, the kit and the cookie jar, while the page's counters and the
sessions counter are unchanged and until the session's activity refresh is due or a read cookie expires (`CookieJar.VerifiedUntil`,
`ExpiryWatch`). `X-Request-Id`, `X-Runtime` and a permanent cookie's expiry are made per replay. `CAMPFIRE_FAST_PATH=off`,
`CAMPFIRE_FAST_PATH_MB` (32). `CAMPFIRE_INLINE` (`replays` by default, `all`, `off`) reads requests on the socket's event thread
(Kestrel inline scheduling plus the runtime's inline socket completions, set in `Program.main`) and answers replays there; anything
else hops to the pool before the app. `FastPathTests` are its attack tests (each guard has a mutation that fails one); the in-process
host `Support.startFronted` serves an app behind the front server, and `CAMPFIRE_TEST_FRONT=1` runs the whole App suite that way (the
read cache tests then count replays as hits; the avatar removal test fails behind the front because Thruster's public cache keeps the
avatar, as it does in front of Rails). Open: `spread_mixed` reads and posts are 12% and 10% below the pool with `replays`.

**One connection** (unit R2.4, `bench/results/oncrack-r2-c1.md`): a request that is not a replay used to hop to the thread pool, and the
pool's workers then spun for about 100 us. Now (a) a request that arrives on an event thread that has served only its own connection for
`CAMPFIRE_INLINE_SOLO_MS` (200; `off` restores R2.3, 0 runs every app request in place, which the App suite is run with as a stress test:
`CAMPFIRE_TEST_FRONT=1 CAMPFIRE_INLINE_SOLO_MS=0`) runs the app right there (`EventThreadWatch` in `Front/Handler.fs`; never an Upgrade),
(b) paths in `Campfire.Kit.CheapPaths` (`/up`) always do, and (c) idle pool workers do not spin: `Program.main` sets
`DOTNET_ThreadPool_UnfairSemaphoreSpinLimit=0` unless given (and only while `CAMPFIRE_INLINE` is on; the AOT image no longer sets a longer one).
A post at one connection costs 242 us of CPU (was 393), `/up` 22 (was 110). Tools: `bench/paths` takes `POST` and `THREADS=1` (CPU per request by
thread name), `bench/c1-wakes` lists the futex calls per request by call chain. The pool still wakes three times per post (the push job's
channel, `WebPushPool.DeliverLater`'s `Task.Run`, a worker waking a worker); each is asynchronous work Rails does too.

**Memory and cold start** (unit R2.5, `bench/results/oncrack-r2-mem.md`): `bench/mem` runs a list of scenarios (`idle:S`, `get:room:C:S`, `post:C:S`,
`cable:N`, `upload:N`, `real:spread:S` with `--seed crowd`) in one container and prints every phase's peak and end memory (cgroup current and anon,
the process's Pss and Rss) beside the GC's own view (`CAMPFIRE_MEM_LOG_MS`); `bench/mem-sweep` repeats it per environment setting; `SMAPS=1` splits
the end state into the managed heap and the rest. Anon, not `memory.current`, is the memory a process holds: current counts the page cache the
database and the log write. `bench/boot --timeline` prints the start-up milestones (`CAMPFIRE_BOOT_LOG`). What decided memory: (a) the two page caches
were mis-sized: the read cache keeps a page three ways (raw, gzip, plain) and the fast path keeps the gzip member alone, so the read cache is 16 MB
and the fast path 64 MB (`CAMPFIRE_READ_CACHE_MB`, `CAMPFIRE_FAST_PATH_MB`); (b) libvips' operation cache is 16 MB and its workers two, glibc has two
arenas (`MALLOC_ARENA_MAX=2` in the Dockerfile; `CAMPFIRE_VIPS_CACHE_MB`, `CAMPFIRE_VIPS_CONCURRENCY`); (c) no GC setting helped (gen0 size, DATAS,
conserve memory, heap count, hard limit, concurrent, workstation: all measured, none kept; they move a read-only phase and cost a write one).
`CAMPFIRE_PREWARM=off` turns off the start-up thread that warms the route table, SQLite and the host builder.

**Search order** (unit R3.3, `bench/results/oncrack-r3-search.md`): `Message.searchReachable` lists the newest 100 reachable matches by message id (`ORDER BY idx.rowid DESC`), as Rails `dbc7620` does; the parity oracle gets the same one-method change from `parity/docker/parity_search_order.rb` (rebuild its layer with `docker build -t campfire-reference -f parity/docker/Dockerfile --build-context fixtures=reference/test/fixtures parity/docker`), and `search/results/order` is the state that tells the orders apart. The F# port keeps `90b3300`'s order and differs from that oracle in that state by design.

**The WAL** (unit R3.4, `bench/results/oncrack-r3-wal.md`): the c=16 post stall is the VM's disk stopping for 0.3-1.7 s under the 250-300 MB/s of
WAL that sustained posting writes (about 5.3 frames a post, ~20 pages rewritten per group commit, FTS5 36% of them), not the checkpoint policy; any
sync in that time waits it out. The default stays R2.2's restart. `CAMPFIRE_WAL_DEFER` (opt-in) restarts the WAL only when that is cheap (checkpointer
idle, at most 1,000 frames to copy, last checkpoint under 25 ms) and otherwise keeps writing up to `CAMPFIRE_WAL_CEILING_PAGES` (40,000; the writer's
`journal_size_limit` is then raised so the WAL is never truncated: a truncation's trim on the `discard`-mounted disk stalled syncs for seconds); no
ceiling measured gave a gain that held up in alternating reps. A quiet WAL is checkpointed every 250 ms, as current Rails does
(`CAMPFIRE_WAL_CHECKPOINT_MS`). Tools: `CAMPFIRE_WAL_TRACE=/path` (checkpoints, restarts, writer groups over 20 ms) with `bench/run`'s `TRACE_DIR`;
`bench/results/oncrack-r3-wal/trace-run.sh` (a traced tier 2 rep plus the VM's disk stats) and `trace.py`; `bench/lib/walmix.py` (a WAL's frames by
b-tree, from `bench/post-micro`'s `POST_MICRO_KEEP`). The lever left is fewer WAL frames per post.

**WAL volume per post** (unit R4.4, `bench/results/oncrack-r4-wal.md`): a post's commit rewrites ~18 pages (one right-edge page per b-tree touched, FTS5 40% of them), so frames a post
is about 18 / writes per group (4.4 at c=16, 1.75 at c=64). A group window halves the bytes and costs throughput (-25% at c=16, -7.5% at c=64, alternating windows), FTS5 `automerge=16`
(`CAMPFIRE_FTS_AUTOMERGE`, opt-in, stored in the index's config table) showed 0-5% in the container; nothing became a default. `WriterStats.Frames` counts the frames the writer
appends (`CAMPFIRE_WAL_TRACE` logs the totals per restart); `bench/wal-ab` alternates a post-path setting (`CAMPFIRE_POSTPATH_FILE`, `group_window_us=N`, `fts_automerge=N`) by window in one
container and prints frames and bytes per post for each; `bench/results/oncrack-r4-wal/replay.py` attributes a commit's frames to b-trees offline. Single tier 2 reps on a busy host
misled twice here: alternate.

**Upstream's method** (round 2 final, `bench/results/oncrack-r2-final.md`): the comparison that counts is Basecamp's
`once-campfire-verification` harness (`bin/benchmark`, its seed, loadgen and contracts) against current upstream Rust and C, not the pinned
`ccece30`. Its checkout is `~/Desktop/projects/once-campfire-verification` (branch `oncrack-adapter`: the `oncrack`/`fsharp` apps and the
Rails 90b3300 search order for the port only since R3.3: onCrack lists search by message id as upstream does; `oncrack-cached`, `oncrack-prev`; never pushed); the upstream checkouts and build scripts are in `~/Desktop/projects/upstream-campfire/`
(`scripts/env.sh`, `run.sh`, `build-c.sh`). Run it in colima from a tmpfs copy (`/mnt/cfv`), with the seed group-writable (the VM user is uid
501, the containers 1000), and point the harness's workspace at a clean worktree of onCrack: it refuses a checkout that changes between rounds.
`bench/results/oncrack-r2-final/table.py` prints its tables in upstream's form, `review.py` re-runs room page, mixed and post by hand with the
server's CPU. onCrack's lead there is its caches (with `CAMPFIRE_RESPONSE_CACHE_MB=0` it is the port, 0.79x Rust). Since R3.2 a hit re-checks the session
and membership as upstream's contract asks (`CAMPFIRE_FRESH_AUTH`, below), and that mode is the headline; the cached decision is an opt-in
and is never quoted as the comparable number.

**Fresh authorization** (unit R3.2, `bench/results/oncrack-r3-fresh-auth.md`): `CAMPFIRE_FRESH_AUTH` (on by default; `0`, `off`, `false`) is
upstream's contract of fresh authorization on every cache hit. On, every request reads its session and user rows (the authentication maps in
`ReadCache.session`/`user` are skipped), a cached room or messages page is served only after `FreshAuth.membership` finds the row (`ReadCache.page`'s
`room`), and a fast path replay first runs `FreshAuth.replay` (session by token, id and user, its user row and, for a room page, the membership and
room) on `Database.CheckNow`, a bag of read-only connections of its own (never the readers: on them, replays that found every reader taken fell into
the app and dragged the fast path down for whole samples). The counters still guard content in both modes. `FreshAuthTests` attack it in both modes,
in process and fronted; `ForeignWriteTests` run in both modes; `CAMPFIRE_FRESH_AUTH=0 bin/verify App` runs the suite in the cached mode. Upstream's
harness takes a second onCrack as `oncrack-cached` (adapter commit `d7fab45`); `~/Desktop/projects/upstream-campfire/scripts/setup-r32.sh` rebuilds its
tmpfs after a VM restart (upstream's load generator is kept built in `tools/loadgen-1.98.1-static/`), and `run-r32.sh` starts a session with `guard.sh`
beside it. **Disk, during upstream sessions:** upstream Rust writes ~1.3 GB of stdout log per container, and the VM's disk gives space back to macOS only
when trimmed; an untrimmed session filled the Mac (2026-10-09) and the ext4 journal aborted (`e2fsck` repaired it). Trimming during a session costs the
measured app (Rust -6%), so cap container logs in the VM's dockerd instead (`/etc/docker/daemon.json` `log-opts` max-size 64m, max-file 2; a colima restart
drops it) and let `guard.sh` stop the session under 12 GB free. **Host load:** the VM's vCPUs are not pinned; other work on the Mac (another session's
builds) moves them to efficiency cores and every app's samples swing 30-50%. Sample the host while a session runs (`host-load-*.txt`) and read the hand
re-run's CPU per request beside the harness's medians.

**Held read transactions for the fresh checks** (unit R4.3, `bench/results/oncrack-r4-fresh.md`): a fresh check is one narrow query, and starting and ending its
read transaction cost more than the query (SQLite's shared lock on a WAL read mark: an `fcntl` each way, plus an `fstat` for an empty WAL). `Database.CheckNow`
(`CheckerPool` in `Database.fs`, slots with a compare-and-swap state in place of the bag) keeps the connection's read transaction open after a check and runs
the next check's query in it while `Versions.ChangeStamp` (the WAL index header's change counter, which every commit by any connection moves; the watch's own
mapping) still reads what it read before that transaction began; a moved counter ends it and begins another before the query. Every check still runs its query
against the database, and nothing is remembered between checks but SQLite's own snapshot, so a revoked session, a removed membership or a deleted room is seen by the
first check that starts after the commit returned. A kept transaction pins the WAL, so a 5 ms timer ends the stale and the idle ones (armed only while one is
kept), and the writer's RESTART calls `ReleaseHolds` first (`Checkpoints.BeforeRestart`), which also keeps checks from beginning one for 50 ms.
`CAMPFIRE_FRESH_HOLD=0` restores one transaction per check; `CAMPFIRE_FRESH_HOLD_FILE` (benches only) flips it from a file within 20 ms. `CheckHoldTests` (Db) hold it to
the rule (a stress run that fails if any check answers from before a commit that returned ahead of it; mutation: comparing the stamp for "held at all" fails three
tests). Rejected: remembering a check's answer under the change counter (or the version counters) and skipping the query while it holds; that is the cached decision
with a database stamp, not upstream's contract of re-reading on every hit. Tools: `bench/fresh-micro` (Linux, `bench/micro-linux fresh-micro`, the whole app in one
process, a page read by N connections beside optional posts, windows alternating the setting), `bench/fresh-ab` (one running container, the setting alternating by
window, CPU per request from the cgroup), `bench/db-micro` (`fresh` scenarios: the check's shapes).

**Commits by other connections** (round 2 verifier, `bench/results/oncrack-r2-verifier.md`): the version counters' triggers live in the
writer's connection, so nothing else's commits (a Rails console or rollback, a second container, the sqlite3 shell) moved them. Now `Versions`
watches the WAL index's change counter (`iChange` in `<db>-shm`, mapped read-only through libc; never through `FileStream`, whose `flock`
fights SQLite's locks on macOS, and never closed before every SQLite connection is: closing a descriptor drops the process's POSIX locks). The
writer's commits go through `Versions.Committing` (`DbRun.committing`: every `COMMIT` and every autocommitted after-commit hook), which tells its
own commits from others' by its connection's `PRAGMA data_version`; `Versions.Sync`, called before every cache serves anything (pages, sessions,
users, fast path replays) and by every request and job before its first read, moves every counter by 2 and the epoch by 1 for a commit nobody
accounted for, and logs `WARN campfire_db: a commit by another connection` (a bench that shows it has a write path outside `Committing`). Fragments
are kept per epoch (`AppState.FragmentStoreNow`; a request takes its store in `Boot.dispatchWithFragmentCache`, a job in `Registry.Scope`). The
messages page has no `fresh_when` (content ETag). `ForeignWriteTests` (App, in process and fronted) and `VersionsWatchTests` (Db) are the attack
tests; a write on the writer's connection that bypasses `Committing` costs every cache, never correctness. `CAMPFIRE_READ_CACHE_MB=0` and
`CAMPFIRE_FAST_PATH_MB=0` turn those caches off, and upstream's `CAMPFIRE_RESPONSE_CACHE_MB` sets both (`Campfire.Kit.ResponseCacheBudgets`).
The fast path keeps offered targets as hashes.

# once-campfire-fsharp

Campfire in F#. It is a port that has to be indistinguishable in use from the Rails app in
`reference/` (basecamp/once-campfire, pinned at `90b3300`) and from the Rust port in `rust/`
(basecamp/once-campfire-rust, pinned at `ccece30`). It must also be faster than the Rust port on
every benchmarked workload.

## Sources of truth, in order

1. **`rust/` is what we translate from.** It already reproduces Rails exactly, and its tests and
   golden vectors prove it. Port a Rust module to F# with the same responsibilities and function
   boundaries, and port its tests with it. Rust's "Known differences" (`rust/README.md`) are ours
   too: same cookies, same CSRF policy, same job model, same limits.
2. **`reference/` is the oracle** for anything Rust doesn't settle or that looks wrong. When in
   doubt about behavior, read the Ruby. When it depends on Rails or gem internals, read the gem
   source in the reference image (`docker run --rm campfire-reference bundle show <gem>`).
3. **Bugs are the one exception.** We may fix a bug instead of copying it. Every deliberate
   divergence goes under "Known differences" in `README.md`, citing the reference file, and gets a
   test plus any parity mask it needs.

Stay compatible with existing installs: the SQLite schema, the storage layout
(`/rails/storage/{db,files,backups}`) and signed or encrypted cookies, so nobody is signed out by
an upgrade and rolling back to Rails works on data we wrote.

Don't edit `reference/`, `rust/` or `vectors/`. Vectors are generated by the reference app (see
`vectors/README.md`).

## Layout

| Project | Rust crate | What |
|---|---|---|
| `src/Campfire.Ruby` | `crates/ruby` | Ruby string behavior the rest share (ERB escaping, `to_i`/`to_f`/`strip`, `Float#to_s`, `CGI.escape`, `url_encode`, Rack byte ranges), checked by `vectors/ruby_core.json` |
| `src/Campfire.RailsCompat` | `crates/rails_compat` | Message verifier/encryptor, key generator, cookie and JSON formats, `Clock` |
| `src/Campfire.Routes` | `crates/routes` | Path helpers mirroring `config/routes.rb` |
| `src/Campfire.Assets` | `crates/assets` | Propshaft-compatible digests, importmap, vendored JS/CSS, port-owned overrides |
| `src/Campfire.Assets.Build` | `crates/assets/build.rs`, `build/` | Build-time tool `Campfire.Assets` runs before it compiles: Propshaft digests and compilers, importmap, the embedded asset blob (depends on `Campfire.Ruby`, as `build.rs` does on `ruby_compat`) |
| `src/Campfire.Db` | `crates/db` | SQLite over the existing schema: one writer, a reader pool, models, queries, fixtures |
| `src/Campfire.RichText` | `crates/richtext` | Action Text pipeline: sanitize, attachments, autolink, plain text |
| `src/Campfire.Storage` | `crates/storage` | Active Storage blobs, disk service, variants (libvips via NetVips), previews (ffmpeg) |
| `src/Campfire.Cable` | `crates/cable` | Action Cable protocol over the upgraded Kestrel stream (the WebSocket framing is in `Socket.fs`), in-process pub/sub |
| `src/Campfire.Kit` | `crates/kit` | Request context, params, cookies, session, forgery protection, flash, formats, responses, gzip, response cache, front server |
| `src/Campfire.Views` | `crates/views` | Templates (one F# module per ERB file, at the same relative path, under `Templates/`), view helpers (`Helpers/`), the template writer and the fragment cache (`Core/`), and the view-models |
| `src/Campfire.App` | `crates/campfire` | Controllers, routing (Falco on Kestrel), channels, jobs, integrations; the `campfire` executable |
| `tests/Campfire.*.Tests` | tests beside each crate | xUnit v3, one project per source project |
| `parity/`, `bench/`, `vectors/`, `reference-tools/` | same paths | Copied from `rust/` (MIT); the harness runs our image as the candidate |

Project references follow the crate graph. Don't add an edge Rust doesn't have.

## F# conventions

- Modules and functions first. Use records and unions for data, and classes only where .NET
  interop needs them (ASP.NET Core hosting, `IDisposable` resources).
- `Result` for expected failures a caller handles (bad signature, record not found, invalid
  params); exceptions for bugs and broken invariants.
- `task { }` for async. No `Async` on hot paths, and no `.Result` or `.Wait()`.
- Match the shape of the Rust code you're porting: if it is one function there, it is one function
  here, with the same name in F# casing. Cite the Rust file at the top of each module
  (`// Port of rust/crates/db/src/messages.rs`). Cite the reference file when matching Rails
  directly, and say why when diverging.
- Comments only where behavior is non-obvious. Write code that reads like the code around it.
- Shared package versions live in `Directory.Packages.props`. Ask before adding a package Rust has
  no equivalent of.

## Performance rules (the hot paths are the five benchmarked workloads plus Cable fan-out)

- Render templates straight into pooled UTF-8 buffers (`IBufferWriter<byte>` / `ArrayPool`), never
  through intermediate strings, a DOM or a markup library.
- No reflection-based serialization on request paths; use `Utf8JsonWriter` or source-generated
  `System.Text.Json`.
- Prepared SQLite statements, reused per connection. Reads go to the reader pool; writes go to the
  single writer, as in Rust.
- Anything Rust caches (page parts, ETags, gzip output, avatar paths), we cache the same way.
- Performance changes come with before-and-after numbers from `bench/`, recorded under
  `bench/results/`.

## Working rules

- `bin/verify` must pass before you report work as done: a Release build with warnings as errors,
  then every test. Say exactly what ran and what didn't.
- Golden-vector tests read `vectors/*.json` through `tests/Shared/Repo.fs` (`Repo.vector "name"`).
- `bin/db-differential` compares `Campfire.Db` with the reference app: the fixtures and a long scenario
  loaded through Active Record against what the F# models write, the schemas, and the reference booting on
  a database F# wrote. It needs the reference image and colima; run it after changing a model or the schema.
- `bin/richtext-differential` compares `Campfire.RichText` with the Rust crate on generated inputs: how markup
  parses in 20 contexts, and what a body presents as, as plain text, as an editor value and for its mentions.
  It needs mise for the Rust toolchain; run it after changing the parser, the sanitizer or the pipeline.
- `bin/kit-differential` compares `Campfire.Kit` with the Rust kit on generated inputs: Accept headers and format
  negotiation, cookie headers, host/protocol/client address from proxy headers, JSON and form bodies, strong
  parameters, and multipart bodies and content types. `bin/kit-differential golden` refreshes the sample of
  Rust's answers that `Campfire.Kit.Tests` replays. `bin/kit-differential http` serves the app of the Rust kit's
  `tests/http.rs` from both kits and sends them the same random requests, comparing status, headers and body.
  It needs mise for the Rust toolchain; run it after changing params, cookies, formats, request, the multipart
  reader, `Ctx` or the adapter.
- `bin/views-test-parity` lists any `#[test]` of `rust/crates/views` without an F# test of the same name (spaces for
  underscores) in `tests/Campfire.Views.Tests`, and any file of `rust/crates/views/templates` without an F# module at the
  same relative path under `Templates/`. It prints a count of each and exits 1 if anything is missing; run it after
  porting a test or a template.
- `bin/views-differential` compares `Campfire.Views` with the Rust views crate, byte for byte: every template ported so far,
  every view helper, the fragment cache's keys and eviction, and the view-model helpers, on cases made from the parity seeds
  (`parity/.seed/*`) and the views crate's golden facts plus generated variations (hostile text, every combination of platform
  flags, attribute kinds, sizes). `bin/views-differential golden` refreshes the sample of Rust's answers that
  `Campfire.Views.Tests` replays, and `bin/views-differential bench` records render times (`bench/results/views-foundations.md`, for a busy room page
  and a messages page `bench/results/views-hot-paths.md`, and for the account, profile, person, sign-in and manifest pages
  `bench/results/views-remaining-templates.md`).
  Adding a template or helper to it is a branch in `reference-tools/views/differential/src/ops.rs` (what Rust renders; the
  hot-path templates are in `src/pages.rs`, the account, session, user, profile and PWA ones in `src/rest.rs`), one in
  `fsharp/Operations.fs` (`fsharp/Pages.fs`, `fsharp/Rest.fs`), and cases for it in `generate.py`;
  run `golden` after, so `bin/verify` replays them. A page case also renders cold and warm and plain and recorded and checks
  they are the same bytes, and takes `frame` (the Turbo-Frame layout) and `mode` ("mixed" gives half the messages to the
  template as cached fragments). It needs mise for the Rust toolchain.
- Porting a template: read the comment at the top of `src/Campfire.Views/Core/Out.fs` (the writer, `Utf8.lit` for static text, `w.Text`
  for escaped values, blocks as functions of the writer, no strings for markup), and run `reference-tools/views/transcribe.py
  <path under rust/crates/views/templates>`: it cuts the askama template into its literal text (exact bytes, with askama's whitespace
  control and its dropped trailing newline applied) and a skeleton of the render steps, translating the common helper calls and
  conditions. The result is a starting point; compare the module with Rust's through the differential, and with the Rails golden
  renders through `ParityATests`-style DOM tests (`Campfire.Views.Tests/Support`; `GoldenB` for the messages, rooms and search
  goldens). A page module exposes its regions (`head`, `nav`, `content`, `footer`, `sidebar`) as functions of the writer, which
  `render` hands to the layout and `Layouts.frame` (a `RenderSize` the page module keeps, `head` and `content`) to the Turbo-Frame layout. A module and a namespace of
  one name can't both be in an assembly, so `rooms/show.html` is `Templates/Rooms/Show.fs` as module `ShowPage`, beside the
  `rooms/show/` partials' namespace.
- `Campfire.Kit`'s front server tests (`FrontTests`, `FrontAcmeIntegrationTests`) open real sockets on loopback and take
  about 20 seconds; ACME is tested against a stub CA in the tests, and against a real Pebble CA when `PEBBLE_MINICA`
  names its `pebble.minica.pem` (the recipe is at the top of `FrontAcmeIntegrationTests.fs`; in colima, give Pebble
  `--add-host campfire.test:192.168.5.2`, the VM's name for the Mac, and `docker cp` the root into `target/`).
  `bench/front/run` measures the front server against Rust's; run it after changing `Front/` or `Splice.fs`.
  The TLS session-resumption test needs Linux (Kestrel issues no session tickets through macOS's TLS stack, so it skips
  there) and `openssl`; `bin/linux-tests Kit` runs `Campfire.Kit.Tests` in `Dockerfile.toolchain` inside colima.
- Measuring (Phase 7's discipline, all inside colima, `SERVER_CPUS=0-3 LOADGEN_CPUS=4-7`): `bench/quick` is the before/after runner, **onCrack only by default**
  (`--remeasure-rust` adds Rust, for the re-baseline that closes a phase; otherwise `bench/quick compare DIR` prints onCrack against the stored Rust and F# port
  medians of `bench/results/phase7-final/`, "vs stored Rust baseline" and "vs stored F# port baseline"): the five workloads at c=1 and c=16, 3 reps, `bench/run`'s validity checks and report, plus CPU per
  request from the container's cgroup; run it a rep at a time, `--only oncrack:1 --part 1/2` and so on, then `bench/quick report DIR`. Tier 2 builds nothing into
  an image: `bin/publish-mounted` (in colima) publishes the app as the Dockerfile does, and `bench/quick --mounted /var/tmp/campfire-mounted` runs it mounted over
  `/opt/campfire` of `campfire-oncrack:app`; `bench/quick log DIR --unit ... --tier 2 --change ... --kept true|false` appends to `bench/results/oncrack-log.jsonl` (stamped with the commit the measured build came from: the mounted build's `REVISION` file or the image's revision label; pass `--commit` when building an image another way) and rebuilds `index.html` (its hero is the climb chart, `bench/progress/climb.py`). Tier 1 is
  `dotnet run -c Release --project bench/db-micro` (the database path in process, ns and bytes per page);
  `bench/quick cpu` is CPU per request alone. Crypto and syscall costs differ between macOS and the container, so tier 1 for anything that touches them runs on Linux: `bench/micro-linux crypto-micro|log-micro [args]` runs a `bench/*-micro` project in the toolchain image on two pinned cores with tier-up at once (a single core leaves a hot loop unoptimized for seconds and the numbers swing 5x). `bench/lib/logcount` checks that the batched request log wrote every line (N requests, SIGTERM, count). `bench/run` keeps the last log lines of each rep in `APP-REP-logtail.txt`. Every run warms each route at its measured concurrency until the app is flat
  (`bench/lib/warmup.py`, `WARMUP_SECS`/`WARMUP_MAX_SECS`; `bench/warmup` draws the curve) and `bench/report` flags runs that did
  not settle. `bench/breakdown alloc` traces allocation by type and by the code that allocates, bytes per request (GC allocation ticks with stacks through dotnet-trace; `bench/alloc-analyze` reads the trace; build it once into `/var/tmp/alloc-analyze/out` in the toolchain image). `bench/breakdown perf` scales perf's shares to the unprofiled CPU per request and attributes allocation the same
  way for both apps (`bench/lib/clr-symbols` installs the libcoreclr and libc symbols it needs). Container logs are capped
  (`LOG_MAX_SIZE`, `LOG_MAX_FILE`; request logging itself stays on). Before every benchmark check `df -h ~`
  (stop under 15 GB free), and run `bin/clean-docker` after image rebuilds and `bin/clean-rust-builds` after Rust builds.
  Rebuild `campfire-oncrack:app` from HEAD before measuring (`CAMPFIRE_REVISION=$(git rev-parse HEAD) parity/bin/candidate build`
  in colima labels the image with its commit; `bench/run`'s env.txt records the label and the digest). `campfire-fsharp:app` is the port, never rebuilt here.
- `bench/cable/run` measures fan-out to 1,000 local subscribers against `campfire_cable` (needs python3 and mise, like
  `bench/kit/run`); `FanOutTests` measures the same in process, without Kestrel. Run both after changing `Pubsub.fs`,
  `Connection.fs` or `Socket.fs`; the results and what they say of the host's settings are in `bench/results/cable-fanout.md`.
- `Campfire.Storage` needs libvips (`brew install vips` on macOS; `bin/verify` points NetVips at Homebrew's) and,
  for video, ffmpeg and ffprobe. The storage vectors' byte comparisons run only against libvips 8.16.1 and
  ffmpeg 7.1.5 (rust/Dockerfile's builds); otherwise they are skipped with a note on stderr, so say so when
  reporting. `bin/storage-media-vectors` runs them in `Dockerfile.toolchain` inside colima, with
  `CAMPFIRE_REQUIRE_MEDIA_VECTORS=1` (the header says why it checks vectors the reference image makes there
  rather than `vectors/storage.json` on aarch64).
- `Dockerfile` builds the production image (`campfire-oncrack:app` here; `campfire-fsharp:app` is the port's) in colima, a drop-in for the reference's as
  `rust/Dockerfile` is; its `media-base`, `vips`, `ffmpeg` and `dotnet` stages are copies of `Dockerfile.toolchain`'s, so
  the two share layers, and they must stay identical to each other. `parity/bin/candidate build` builds it and the parity
  candidate image on top (`campfire-candidate-oncrack`; `PARITY_CANDIDATE_APP=fsharp` or `rust` runs the port or the Rust port in the same harness instead); `parity/bin/candidate
  up` then serves a seed (`curl /up`, `POST /session` with `david@37signals.com` / `secret123456`).
  `bin/linux-tests App` runs `Campfire.App.Tests` on Linux in the toolchain image (the transparent-huge-pages test skips on
  macOS); it builds a private copy of the sources there.
- `Campfire.App`'s controllers take `Ctx` and are listed in `Controllers.fs` (module `RouteTable`, the 177 rows of
  `config/routes.rb`): every row is routed to its controller now; a controller added later goes in as
  `Controllers/<Name>.fs` before `Controllers.fs`, and a row of a controller not yet written answers 501 through
  `unported "controller#action"`. The tests boot the whole app over a copy of a parity seed (`Support.bootSeeded`).
- `reference-tools/campfire/controllers_a/replay.py` runs the session, account and user controllers against the reference and
  the candidate image, both on a seed with the clock frozen (inside colima, `PARITY_NET_DIR=/tmp/parity-net`):
  `parity/bin/reference up --seed default --port 4311 --time 2026-03-02T16:00:00Z --freeze`, `parity/bin/candidate up --seed
  default --port 4312 --time 2026-03-02T16:00:00Z --freeze`, then `reference-tools/campfire/controllers_a/replay.py
  http://127.0.0.1:4311 http://127.0.0.1:4312 [--seed crowd|first_run]` (restart both servers per seed: it mutates). It masks
  the differences the ports have by design and says so at the top; run it after changing an account, session or user controller.
- Tests that need the parity seed (`parity/.seed/default`) must skip with a message when it isn't
  built; `CAMPFIRE_REQUIRE_SEED=1` turns the skip into a failure.
- Rust helper builds (differentials, bench servers, loadgen, one-off comparisons) all use the shared
  `CARGO_TARGET_DIR=target/rust`, never a per-tool or scratch target directory: each separate target
  costs ~500 MB of duplicated dependencies. Differential scripts delete both sides' outputs when the
  comparison passes and keep them only on failure. Run `bin/clean-rust-builds` when you're done measuring,
  and `bin/clean-docker` after rebuilding images (each rebuild leaves gigabytes of old layers in colima).
- Run one parity compare at a time in colima (6 GB): two at once OOM-kill Chromium and cells error with "browser.newContext: Target
  page, context or browser has been closed". `parity/bin/candidate compare` refuses a second one (`PARITY_ALLOW_CONCURRENT=1` overrides,
  for a bigger VM); `parity/bin/test-compare-lock` tests the guard. An error status like that is the harness: re-run those cells with `--only`.
- Commit each logical unit on the current branch with a message saying what and why. Don't push.
- Toolchain: .NET SDK 10.0.401 in `~/.dotnet` (`export PATH="$HOME/.dotnet:$PATH"`).
- Docker runs in colima. Run `parity/`, `bench/` and `reference-tools/` scripts inside the VM,
  where they get GNU userland and host networking:
  `colima ssh -- bash -c "cd $PWD && parity/bin/..."`.
  The reference image is `campfire-reference:app`. Set `PARITY_NET_DIR=/tmp/parity-net` (create it
  first) for anything that captures pages: the repo is a virtiofs mount in the VM, and a Unix socket
  there refuses connections between containers (`parity/capture/sandbox/run.sh`).
