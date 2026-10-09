# onCrack R3.2: fresh authorization on every cache hit, measured by upstream's method, 2026-10-09

Upstream's contract re-reads the session and the room membership on every cache hit ("fresh authorization"; Laravel uses a narrow
existence query on each hit). Until this unit, onCrack reused the decision its miss made, kept under version counters that any commit
moves. Round 2's final review measured that design at 3.25x current Rust and 2.37x current C, and said beside every multiple that a
hit there was not the same work as theirs.

This unit adds the mode that is the same work. It measures both modes in the same upstream harness sessions as current Rust, C and
the F# port, and decides which one is the headline.

- Raw data: [`oncrack-r3-fresh-auth/`](oncrack-r3-fresh-auth/).
- Pooled tables: `pooled.md`, from `pool.py`.
- Per-session tables: `tables.md`, from `table.py`.
- The rule for the headline was committed before the second normal session ran: `PLAN.md`, commit `ebf27aa`.

## Decision

**Fresh authorization is the default (`CAMPFIRE_FRESH_AUTH`, on), and its numbers are the headline.**
- The rule: the headline number must be the one that meets upstream's contract. Only fresh mode re-reads the session and membership on
  every hit, so only it is comparable.
- `CAMPFIRE_FRESH_AUTH=0` keeps the cached decision as onCrack's opt-in. It is never quoted as the comparable number.
- The page's hero now shows fresh mode, with the cached decision as its last column, labelled as the opt-in.
- Round 2's cached-decision sessions moved to the panel "Round two: the cached decision".

## Verdict

**Against current upstream, their harness, fresh authorization** (normal profile, two sessions pooled, median of six rounds per cell):
- **2.83x Rust `f9dca47`**, 2.07x C `cd0cbe4` and 3.67x the F# port, geometric means over the five workloads.
- Reads are 2.60-3.10x Rust and 1.67-2.15x C; posts are 2.48x Rust and 2.62x C.

**Mixed profile** (one session, 16 readers plus a writer at 10 posts/s): 3.39x Rust, 2.04x C and 4.19x the port over the four reads.
- This is the least certain multiple in the unit: Rust's and C's mixed medians sit 25-29% under their round 2 values on the same
  images (see "The host").

**What fresh authorization costs**, in hand re-runs reading server CPU from the container's cgroup:
- A room-page hit costs 25.1 µs of CPU, against 17.9 with the cached decision: 1.40x.
- Rust spends 62.1 µs per room page and C 48.1, so they spend 2.47x and 1.91x onCrack's CPU per request.
- Mixed reads give 2.31x and 1.72x.
- These CPU ratios agree with the pooled harness multiples (2.83x and 2.07x) within the noise below. They are the steadier
  comparison this round.

**The cached decision** (the opt-in), same sessions: 3.42x Rust, 2.50x C and 4.42x the port. Round 2 measured 3.25x and 2.37x.

**Correctness:** a revoked session, a removed membership and a banned user each take effect on the next request, in both modes, in
process and behind the front server (`FreshAuthTests`). Every check is described below.

**Plainly:**
- Doing the work upstream's contract asks for costs onCrack about a fifth of its cached-decision throughput.
- Measured that way, onCrack is about 2.8x current Rust and 2.1x current C. Per request it needs about 2.5x less CPU than Rust and
  1.9x less than C.
- The host was busy during every session, so the multiples are good to about ±25% (the two normal sessions put onCrack over Rust
  at 2.33x and 4.05x). They are not good to the second digit.

## What changed

Commits `3882e07` and `87c1ad1`.

With `CAMPFIRE_FRESH_AUTH` on, the default (`0`, `off` or `false` turns it off):
- **Every request reads its session and user rows.** `ReadCache.session` and `ReadCache.user` neither read nor write their maps. They
  still record the counter values the rows are as of, which the pages a request keeps depend on. This is the work upstream Rust's
  `before_actions` does on every request.
- **A kept room or messages page is served only after a membership query finds the row.**
  - `FreshAuth.membership`: the membership joined to its room, one prepared statement.
  - If the row is gone, the action runs as it would uncached: its `set_room` redirects or answers 404.
  - The sidebar and search have no room to authorize. Their content, the user's rooms, is covered by the counters, as upstream's
    pages are covered by its global epoch.
- **Every front-server replay first runs `FreshAuth.replay`**: one narrow prepared statement for the session (by token, id and user),
  its user row and, for a room page, the membership and room.
  - It runs on `Database.CheckNow`, a bag of read-only connections of the checks' own. A thread gets back the one it returned; more
    open on demand, up to 16; it never waits.
  - When a check cannot run, the replay goes to the app.
- **The version counters still guard content in both modes**, so fresh mode only adds checks.

### A bug the first measurement found

The first fresh-mode build (`3882e07`) ran its replay check on the app's readers. It took one without waiting, and went to the app
when none was free.

Upstream's harness showed fresh mode swinging from sample to sample, while the cached mode held 164-185k
(`aborted-normal-3882e07/`):
- Room page: 94.6k, 136k, 126k.
- Sidebar: 150k, 149k, 78k.

The cause was a feedback loop:
1. A replay that found every reader taken went to the app.
2. The app's requests then held the readers for three queries each.
3. So more replays found none free, and whole samples ran in the slow regime.

`87c1ad1` gives the checks their own connections. A test holds every reader with a waiting read and checks that a fresh check still
runs, and that 64 concurrent checks open at most 16 connections. The work per hit is the same: one statement, one read transaction.

## Attack tests

`tests/Campfire.App.Tests/FreshAuthTests.fs`. Each attack runs in all four combinations: fresh and cached mode, in process and behind
the front server.

Before each revocation, the test warms every page it attacks until a cache answers it (a read cache hit in process, a fast path
replay fronted). It checks a cache did answer, so no test passes because nothing was cached. In fresh mode it also checks that each
answer ran a fresh check.

| Attack | Through | Next request |
|---|---|---|
| A session signed out elsewhere, its cookie replayed | a second browser with the same cookie, `DELETE /session` | 302 to `/session/new` for room, messages, sidebar and search |
| A membership an administrator removes | `PATCH /rooms/closeds/:id` without the user | room 302 (not to sign-in), messages 404, sidebar without the room |
| A user an administrator bans | `POST /users/:id/ban` | 302 to `/session/new` for all four pages |

Also:
- **The queries refuse on their own.** `FreshAuth.replay` and `FreshAuth.membership` are false for:
  - a wrong token, session id or user;
  - a room the user is not in;
  - a deleted room, membership or session.
- **Mutation:** with the replay's check disabled, all three attacks fail their "ran a fresh check" assertion.
- **The setting parses** on, off and blank as specified.
- **`ForeignWriteTests`** (round 2's verifier attacks through a second SQLite connection) now run in both modes, in process and
  fronted.

Suites:
- `bin/verify App Db` passes: App 248 tests, 1 skipped; Db 207, 5 skipped.
- `CAMPFIRE_FRESH_AUTH=0 bin/verify App` passes 247 of 247 (run before the CheckNow test existed; that test is
  mode-independent).
- `CAMPFIRE_TEST_FRONT=1` passes in both modes, and with `CAMPFIRE_INLINE_SOLO_MS=0`, except the avatar-removal test. AGENTS.md
  documents that failure: Thruster's public cache keeps the avatar, as it does in front of Rails.
- The full `bin/verify` at the final commit passes: 1,138 tests, 0 failed, 8 skipped. Earlier full runs failed one `Campfire.Cable.Tests` case, a timing flake: a different test each time,
  in 2 of 4 runs with the change and 0 of 2 without. `Campfire.Cable.Tests` builds none of the changed projects (only Cable,
  RailsCompat and Ruby), so it runs the same code either way.

## Upstream's method: sessions, normal profile

Command, per session: `bin/benchmark --rounds 3 --duration 8 --concurrencies 16 --cpus 0-3 --client-cpus 4-7 --apps
oncrack,oncrack-cached,rust,c,fsharp --routes room_show,messages_page,sidebar,search,post_message`.

`oncrack` is the shipped default (fresh). `oncrack-cached` is the same image with `CAMPFIRE_FRESH_AUTH=0`. Both set
`CAMPFIRE_RESPONSE_CACHE_MB=64`.

**Pooled** (`pooled.md`): median [min-max] requests/sec over six rounds, 16 clients.

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| **onCrack, fresh authorization (default)** | **122,438** [51,762-148,801] | **131,302** [66,791-157,148] | **138,444** [103,207-166,097] | **123,356** [91,056-161,791] | **12,756** [8,212-15,004] |
| onCrack, cached decision (opt-in) | 149,333 [111,174-172,448] | 161,776 [126,258-181,998] | 168,688 [137,834-188,639] | 178,097 [123,730-187,004] | 12,327 [8,985-15,440] |
| Rust `f9dca47` | 47,154 [30,656-49,753] | 43,128 [29,400-47,645] | 46,094 [38,980-54,049] | 39,845 [34,280-54,686] | 5,144 [3,495-6,431] |
| C `cd0cbe4` | 63,714 [48,918-75,085] | 60,961 [38,125-79,186] | 65,572 [44,544-81,981] | 73,910 [48,861-82,686] | 4,877 [3,206-5,894] |
| F# port | 24,824 [19,549-36,410] | 28,298 [24,030-40,603] | 28,399 [21,211-37,270] | 31,019 [22,408-32,974] | 8,529 [5,061-9,306] |

Geometric means over the five workloads:

| Ratio of pooled medians | Five workloads |
|---|---:|
| onCrack (fresh) / Rust | **2.83x** |
| onCrack (fresh) / C | **2.07x** |
| onCrack (fresh) / port | **3.67x** |
| onCrack (fresh) / cached | 0.83x |
| cached / Rust | 3.42x |
| cached / C | 2.50x |
| cached / port | 4.42x |

**Each session alone** (`tables.md`):

| Session | fresh / Rust | fresh / C | cached / Rust | cached / C | fresh / cached |
|---|---:|---:|---:|---:|---:|
| `upstream-normal-noisy` (12:24Z) | 2.33x | 1.84x | 3.29x | 2.61x | 0.71x |
| `upstream-normal-2` (12:52Z) | 4.05x | 2.45x | 3.90x | 2.36x | 1.04x |

The second session's 1.04x of fresh over cached cannot be right on a quiet machine, because fresh mode does strictly more work per
hit. That one figure is enough to show these sessions measured the host as much as the engines.

## Mixed profile

`--mixed-write-rate 10 --routes room_show,messages_page,sidebar,search`, one session (12:40Z). Median [min-max] reads/sec:

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| **onCrack, fresh (default)** | **110,546** [42,262-126,396] | **105,063** [96,409-139,844] | **136,714** [129,864-145,655] | **133,647** [124,847-142,057] |
| onCrack, cached (opt-in) | 131,578 [121,495-136,060] | 144,926 [135,401-156,876] | 145,814 [111,708-167,782] | 163,500 [125,534-168,525] |
| Rust | 35,697 [28,981-41,236] | 28,990 [28,782-35,317] | 36,147 [27,639-43,539] | 42,816 [31,195-45,710] |
| C | 51,231 [41,158-59,396] | 60,618 [46,733-62,655] | 63,724 [60,243-67,542] | 61,864 [51,682-64,415] |
| F# port | 25,433 [12,372-26,460] | 32,413 [31,876-32,843] | 28,999 [22,720-30,208] | 28,854 [23,161-29,055] |

Geometric means over the four reads:

| Ratio | Four mixed reads |
|---|---:|
| fresh / Rust | 3.39x |
| fresh / C | 2.04x |
| fresh / port | 4.19x |
| cached / Rust | 4.10x |
| cached / C | 2.47x |

Each app acknowledged 957-960 timed writes at 9.6-10.0 a second. Every write was audited, warm-up included: 5,991 in all.

## Validation

Across the three sessions:
- 119,639,189 timed responses passed the full content contract.
- 2,343,502 acknowledged writes were audited against the messages, rich-text and search-index rows. That counts the normal profile's
  posts and the mixed writer's.
- All 420 raw samples reconcile against the per-app rows.
- Errors plus invalid responses: 0.
- Peak load generator CPU: 257% of 400%.

## The host (read this before any multiple above)

The Mac was not quiet. During the sessions, another session on the same machine kept compiling: Erlang `beam.smp` at 110-170% and Go
builds (`go`, `compile`) at 46-121%. Spotlight's knowledge indexer added 38%.

`host-load-*.txt` samples the top non-VM processes every 10 s:
- `beam.smp` appears in 42 of the 79 samples taken during `upstream-normal-2`.
- The host's one-minute load average ranged 5.5-17.8 on 10 cores (the VM alone accounts for about 5-6 of it).

The VM's 8 vCPUs are not pinned to cores. When the host is busy, macOS moves them onto the M4's efficiency cores, and whichever app is
measuring at that moment reads low:
- C's room page spans 48,918-75,085 across the six rounds.
- The port's spans 19,549-36,410.
- Rust's search spans 34,280-54,686.

Round 2 saw ranges of a few percent on the same images.

What does not depend on it:
- **The order** (onCrack fresh > C > Rust > port on every read) holds in every session.
- **The cached decision is the faster mode** in every hand re-run, and in session one.
- **The CPU per request** varies less:
  - onCrack fresh 21.5-28.6 µs per room page over five runs;
  - cached 17.4-18.8 over three;
  - Rust 61.9-71.2 over three;
  - C 43.5-49.8 over three.

The low fresh runs (28.6 and 26.0 µs) coincide with `beam.smp` and `go` in the host samples (`host-load-fresh-c.txt`).

**Hand re-runs** (`review.jsonl`, round 2's `review.py`; a 15 s warm-up and a 10 s window at 16 clients):

| App | Phase | req/s per run | CPU µs/request per run | Median CPU µs/request |
|---|---|---|---|---:|
| onCrack, fresh | room page | 134,170, 129,470, 145,734, 102,815, 107,360 | 24.0, 25.1, 21.5, 28.6, 26.0 | 25.1 |
| onCrack, fresh | mixed | 147,494, 83,422 | 21.2, 32.9 | 27.0 |
| onCrack, cached | room page | 169,145, 172,092, 175,932 | 18.8, 17.9, 17.4 | 17.9 |
| onCrack, cached | mixed | 175,672, 168,129 | 17.4, 18.1 | 17.7 |
| Rust | room page | 45,835, 39,928, 46,378 | 62.1, 71.2, 61.9 | 62.1 |
| Rust | mixed | 47,978, 45,455 | 60.7, 64.1 | 62.4 |
| C | room page | 68,622, 67,070, 75,620 | 48.1, 49.8, 43.5 | 48.1 |
| C | mixed | 71,622, 71,882 | 46.4, 46.4 | 46.4 |

Two rounds ran interleaved, forward and then reversed (fresh, cached, Rust, C). They were bracketed by one earlier room-page run of each
app, and one later fresh run with the host sampled. Posts were not hand re-run this unit: the post path differs between the modes
only by the session and user reads.

## Sessions run and not used

**`aborted-normal-3882e07/`** (07:58): the first fresh-mode build. Its swings found the bug above.
- It was killed in round 3 when the Mac's disk filled. Rounds 1-2 are complete, along with round 3 of both onCrack modes.

**`discarded-trims-normal-87c1ad1/`** (08:17): one round, run beside a guard that trimmed the Docker disk every 20 s.
- Rust, C and the port read 30-50% low: Rust's room page 23,386, against 47,689 at 07:58.
- A controlled probe then measured what a trim loop costs Rust's room page: 44,784 against 47,660 quiet, 6% (64.2 against 59.6 µs).
- I stopped the session and dropped the in-session trims.

Neither enters any table above.

## Disk

**The fill.** At 08:09 the Mac's free space went from 15 GB to 1.1 GB within 12 minutes of the first session. Upstream Rust writes about
1.3 GB of stdout log per container (one measured 1,357,817,969 bytes). The harness removes each container, but the VM's disk image
gives the blocks back to macOS only when trimmed, and I had not trimmed while waiting. Round 2's report had recorded this growth and
trimmed at every poll.

**Recovery:**
1. Killed the session.
2. Freed this project's Rust build intermediates (`bin/clean-rust-builds`, 520 MB).
3. Trimmed (18 GiB returned).
4. The ext4 journal on the VM's data disk had aborted on a failed write. I stopped Docker, ran `e2fsck -fy` (clean, no repairs
   needed beyond the journal) and restarted colima.
5. Images were intact. Free space was back to 16-18 GB.

**Since then:**
- For every later session, container logs were capped in the VM's dockerd (`/etc/docker/daemon.json`: `log-opts` max-size 64m,
  max-file 2). Every app still wrote its full stdout; Docker kept the last 128 MB. The original config is restored since
  (`daemon.json.r32-orig` in the VM).
- `guard.sh` runs beside each session on the load generator's CPUs. It reads the Mac's free space through virtiofs every 20 s, stops
  the session under 12 GB, and trims after the session ends.
- Free space stayed at 14-16 GB through every later session.
- Before each session: `bin/clean-parity` and `bin/clean-docker`.

## Source, images and checks

| Implementation | Measured source | Image (this VM, arm64) |
|---|---|---|
| onCrack and onCrack-cached | `87c1ad1`, clean worktree `~/Desktop/projects/oncrack-measured` | `campfire-oncrack:app` `sha256:ece6fb0ea752`, label `87c1ad1` |
| Rust | `f9dca47` | `campfire-rust-upstream:f9dca47` `sha256:63d7de5e36bb` (round 2's) |
| C | `cd0cbe4` | `campfire-c-upstream:cd0cbe4` `sha256:cce0f35ccdc1` (round 2's) |
| F# port | `9954ad0` | `campfire-fsharp:app` `sha256:421f335c3ff8` (round 2's) |

**Harness:** `once-campfire-verification` `d7fab45`. That is round 2's adapter (`ea9024a` and `4e926db`) plus one local commit, not
pushed. The commit adds `oncrack-cached`: onCrack's runtime and source with its own image and environment variables
(`ONCRACK_CACHED_IMAGE`, `ONCRACK_CACHED_BENCH_ENV`). The contracts, load generator and audits are unchanged.

**Load generator:** rebuilt from the harness's `loadgen/` (`--locked`) with Rust 1.98.1, statically linked for aarch64, in
`rust:1.98.1-slim-trixie`. Its SHA-256 is `351a66af1ea1…`, against round 2's `a0ac759b…` (built in the full trixie image). A copy
is kept at `~/Desktop/projects/upstream-campfire/tools/loadgen-1.98.1-static/`.

**Seed:** built by `bin/seed --image campfire-reference:app` after the VM restart, SHA-256 `bc5a851525b4…`. As round 2 explains,
every build differs: fresh credentials and their bcrypt digests.

**Topology, CPUs, tmpfs:** as round 2.
- Server CPUs 0-3, generator CPUs 4-7.
- `WEB_CONCURRENCY=3`, `JOB_CONCURRENCY=3`, `RAILS_MAX_THREADS=5`.
- A 3 GiB tmpfs at `/mnt/cfv`.

**Pixels:** not re-run in this unit. The change decides whether a kept page is served or the action runs; it renders nothing, and both
paths answer the same bytes the tests compare (`FreshAuthTests`, `ReadCacheTests`, `FastPathTests`). The full gate's 940/940 is
R3.1's, on `d708910`'s `src/`.

## Reproducing

All of this runs inside colima. The scripts are in `~/Desktop/projects/upstream-campfire/scripts/`, copied into
[`oncrack-r3-fresh-auth/scripts/`](oncrack-r3-fresh-auth/scripts/) with the adapter's diff against upstream `e244051`.

```sh
setup-r32.sh                                        # tmpfs, harness d7fab45, loadgen, seed, workspace (after any VM restart)
# cap container logs: /etc/docker/daemon.json log-opts {"max-size":"64m","max-file":"2"}, then systemctl restart docker
run-r32.sh r32-normal --apps oncrack,oncrack-cached,rust,c,fsharp --routes room_show,messages_page,sidebar,search,post_message
run-r32.sh r32-mixed --mixed-write-rate 10 --apps oncrack,oncrack-cached,rust,c,fsharp --routes room_show,messages_page,sidebar,search
python3 bench/results/oncrack-r3-fresh-auth/table.py DIR...   # per-session tables, with both modes' ratios
python3 bench/results/oncrack-r3-fresh-auth/pool.py           # the pooled headline and the hand re-runs' CPU medians
python3 bench/results/oncrack-r2-final/review.py oncrack campfire-oncrack:app OUT.jsonl --env '{"CAMPFIRE_RESPONSE_CACHE_MB":"64","CAMPFIRE_FRESH_AUTH":"0"}' --tag cached --phases room_show,mixed
```

**Next time:** run the sessions when nothing else is building on the Mac, or pin the VM. Sample the host as these did. A quiet
re-run would tighten the ±25% to round 2's few percent.
