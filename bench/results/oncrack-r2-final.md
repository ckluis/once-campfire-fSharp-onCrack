# onCrack round 2: final re-baseline against current upstream, by upstream's method, 2026-10-09

Round 2 closes the way Basecamp now reviews every Campfire implementation:
[`once-campfire-verification`](https://github.com/basecamp/once-campfire-verification)'s `docs/performance-review.md`
(copied as [`oncrack-r2-final/upstream-performance-review.md`](oncrack-r2-final/upstream-performance-review.md)).

- **What ran:** its harness, its seed, its load generator and its two profiles, in one session.
- **Who ran:** current upstream Rust (`f9dca47`), C (`cd0cbe4`) and Rails (`0aa339d`), each built as its repository
  describes, beside the F# port and onCrack rebuilt from HEAD.
- **What counts now:** the comparisons are against current Rust and C, not the pinned `ccece30` the climb chart divides by.
  That history moved to a panel on the page.

onCrack is scored on its own terms (plan rule 4). It is not a like-for-like port result.

- Raw data: [`oncrack-r2-final/`](oncrack-r2-final/). `upstream-normal/` and `upstream-mixed/` are `bin/benchmark`'s output
  directories, copied whole (summary, one JSON per app and round, every raw sample, the console log).
- `tables.md` is `table.py`'s output.
- `review.jsonl` is the hand re-run (`review.py`).
- `t3/` is this project's own suite on the rebuilt image.
- `kloc.json` holds the source counts.

## Verdict

- **Against current Rust (`f9dca47`), their harness, same session:** onCrack serves 3.25x Rust's requests/sec over the five workloads
  (geometric mean at 16 clients):
  - Read pages: 3.34-3.89x.
  - Posts: 2.32x.
  - Mixed profile (16 readers, plus a writer at 10 posts/s): 3.64x on reads.
- **Against current C (`cd0cbe4`):** 2.37x over the five workloads (reads 2.29-2.37x, posts 2.59x), and 2.36x on mixed reads.
  C is the faster of the two upstream engines here, as in upstream's own report. C over Rust is 1.45-1.64x on reads here;
  upstream published 1.23-1.41x.
- **Against the F# port it was forked from:** 3.93x over the five workloads and 4.99x on mixed reads. Posts are 1.61x.
- **The lead is the caching design, not a faster engine.**
  - With both caches off (`CAMPFIRE_RESPONSE_CACHE_MB=0`), onCrack is the port: room page 38,668 req/s at 91.0 µs of CPU, which is
    0.79x Rust and 0.51x C.
  - With the read cache on and the front server's fast path off, onCrack serves 122,749 req/s (30.4 µs): 2.49x Rust and 1.62x C.
  - The shipped default replays from the fast path: 170,643 req/s (17.9 µs) on the hand re-run, against Rust's 58.4 µs and C's 43.5 µs.
- **The mechanism differs from upstream's contract, and that has to be said next to every multiple.**
  - Upstream's implementations re-read the session and the room membership on every cache hit ("fresh authorization").
  - onCrack keeps the authorization decision. It drops it on any commit, by any connection: it watches SQLite's WAL index change
    counter (the round 2 verifier's fix).
  - So a hit costs onCrack a memory read and a hash lookup, and costs Rust and C SQL queries.
  - The outcome held under the verifier's attacks (revoked and rotated sessions, removed memberships, foreign writers, kill -9). The
    work per hit is not the same as theirs.
- **Search is checked against a different order.** onCrack and the port render Rails `90b3300`, whose search lists the last 100
  matches by time. Upstream (since Rails `dbc7620`) lists them by message id.
  - Under the unchanged contract, onCrack's search fails preparation: one of 13 results sits elsewhere.
  - The adapter checks the pinned ports against the old order. Every other check is unchanged.
- **Everything validated.** The two sessions together:
  - 68.5M timed responses, every one passing its full content contract, with 0 errors or invalid responses.
  - 1,049,504 acknowledged posts audited against the messages, rich-text and search-index rows.
  - 270 raw samples, every one reconciled against the per-app rows.
  - Peak load generator CPU: 257% of 400%.
- **The hand re-run agrees.** For onCrack, Rust and C, the room page and the mixed reads are within 3.5% of the harness's medians,
  and posts within 5%.
- **Posts under sustained load are lower than the harness shows.** This project's suite (90 s warm-ups) reads 11,292 posts/s at c=16
  on the same image, against 15,214 on upstream's harness. The writer's WAL-restart stall, open since R2.2, appears only after
  longer posting than upstream's samples.
- **Pixels:** 252 screenshots of the states this round's fixes reach, plus every small seed, are pixel-equal to Rails. This is a
  targeted gate, not the full 940.
- **Code size** (cloc 2.10, upstream's rules): onCrack 44.4 KLOC of F#, the port 42.5, Rust 29.8, C 94.8 and Rails 4.4 (the last three
  as upstream published them). 3.6 KLOC of onCrack and the port is an F# port of the html5ever tokenizer, which Rust takes as a crate.

**Plainly:**
- Measured their way, onCrack is about 3.3x current Rust and 2.4x current C. That is because it does less work per cache hit than their
  contract asks for, while giving the same answers under every attack we and the verifier tried.
- Measured their way with its caches off, it is slower than both.
- Against the port, the same caches make it about 4x.

## Current production HTTP results (normal profile)

`bin/benchmark --rounds 3 --duration 8 --concurrencies 16 --routes room_show,messages_page,sidebar,search,post_message`.
16 clients, three alternating rounds (order reversed in round 2), two seconds of warm-up at 4 clients per route, eight-second samples.
Median requests/sec [observed min-max]:

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| Rails `0aa339d` | 5,325 [5,316-5,371] | 5,414 [5,332-5,424] | 5,734 [5,522-5,982] | 5,841 [5,784-5,853] | 401 [399-409] |
| Rust `f9dca47` | 50,006 [49,938-50,293] | 46,785 [46,730-47,255] | 55,116 [54,642-55,674] | 55,752 [54,803-55,852] | 6,549 [6,544-6,560] |
| C `cd0cbe4` | 75,833 [75,283-75,877] | 76,804 [75,898-78,612] | 82,969 [81,437-83,172] | 80,600 [76,815-84,866] | 5,867 [5,648-5,872] |
| F# port | 35,882 [35,876-36,117] | 42,124 [41,978-42,453] | 38,008 [34,155-38,052] | 33,641 [31,013-33,983] | 9,472 [8,976-9,568] |
| **onCrack** | **173,975** [173,803-174,889] | **182,064** [174,088-182,332] | **190,284** [189,321-192,205] | **186,369** [184,586-187,118] | **15,214** [15,012-15,396] |
| onCrack / Rust | 3.48x | 3.89x | 3.45x | 3.34x | 2.32x |
| onCrack / C | 2.29x | 2.37x | 2.29x | 2.31x | 2.59x |
| onCrack / port | 4.85x | 4.32x | 5.01x | 5.54x | 1.61x |

Geometric means over the five workloads:

| onCrack over | ratio |
|---|---|
| Rust | 3.25x |
| C | 2.37x |
| the port | 3.93x |
| Rails | 33.8x |

C over Rust is 1.37x and the port over Rust 0.83x. The port has no response cache, since it ports Rust `ccece30`.

| Implementation | Timed responses validated | Acknowledged writes audited (warm-up included) | Peak generator CPU % | Room page p50 / p99 ms |
|---|---:|---:|---:|---|
| Rails | 545,111 | 11,234 | 30.3 | 2.881 / 6.751 |
| Rust | 5,140,478 | 192,540 | 101.7 | 0.296 / 0.700 |
| C | 7,725,125 | 171,787 | 140.7 | 0.202 / 0.422 |
| F# port | 3,770,879 | 260,137 | 149.5 | 0.402 / 1.057 |
| onCrack | 17,895,090 | 407,821 | 255.4 | 0.082 / 0.213 |
| all | 35,076,683 | 1,043,519 | 255.4 | |

- All 150 raw samples (a warm-up and a timed sample per app, route and round) reconcile with the per-app rows.
- Errors plus invalid responses: 0.
- Every app's audit verified each acknowledged message's row, room, exact body and search-index entry, with no duplicates or extras,
  and `PRAGMA integrity_check` passed.

## Reads with a paced message writer (mixed profile)

`--mixed-write-rate 10 --routes room_show,messages_page,sidebar,search`. The writer posts into HQ at up to 10 messages/s, with no
catch-up. The 16 readers read Watercooler.

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| Rails `0aa339d` | 3,057 [2,973-3,069] | 3,921 [3,856-4,003] | 4,789 [4,759-4,805] | 4,700 [4,610-4,704] |
| Rust `f9dca47` | 47,636 [47,488-47,918] | 44,472 [43,782-44,530] | 54,992 [54,837-55,131] | 52,884 [51,026-54,241] |
| C `cd0cbe4` | 72,453 [71,830-73,058] | 74,442 [74,415-75,589] | 81,947 [81,521-82,832] | 79,534 [76,707-80,989] |
| F# port | 32,411 [32,337-33,614] | 41,592 [39,657-41,805] | 37,571 [36,719-37,769] | 34,389 [34,292-34,662] |
| **onCrack** | **170,862** [169,773-170,888] | **180,240** [179,902-181,130] | **190,099** [182,136-191,484] | **184,827** [184,206-185,074] |

Geometric means over the four reads:

| onCrack over | ratio |
|---|---|
| Rust | 3.64x |
| C | 2.36x |
| the port | 4.99x |
| Rails | 44.8x |

**Writer:**
- Each app acknowledged 960 timed writes, at 10.0/s in every sample (Rails 9.9-10.0).
- Writes audited, warm-up included: 1,200 for each app (Rails 1,185), 5,985 in all.

**Reads:**
- Timed reads validated: 33,451,818.
- All 120 raw samples reconcile; errors plus invalid responses: 0.
- Peak generator CPU: 257.0%.

**Why onCrack loses 0-2% here, where Rails loses 16-43%:**
- Upstream invalidates its pages on a global SQLite epoch, so every post into HQ empties Watercooler's pages as well.
- onCrack's page counters are per room and per user. A post into HQ moves HQ's counter, its members' counters, and the
  accounted commit counter. Watercooler's room and messages pages stay stored.
- This is the cache-design difference the profile was written to expose (upstream: "Global SQLite epochs invalidate these read
  pages even when the write belongs to another room"). Rust and C lose 0-5%, because 10 writes a second is little churn.

## Application source size

Counted with cloc 2.10 (`--by-file --skip-uniqueness`, F# only).
- **Counted:** handwritten `src/**/*.fs`.
- **Excluded:** `obj/` and `bin/` (generated); `src/Campfire.Assets.Build` (a build-time tool, as Rust's `build.rs` sits outside `src/`);
  and tests, parity and bench tooling.
- Templates are F# modules, so they count as rendering code, as Rust's do.

| Implementation | Counted source revision | Files | Code lines | Backend KLOC |
|---|---|---:|---:|---:|
| onCrack | `f5352d0` | 333 | 44,445 | 44.4 |
| F# port | `2e6c08e` (the image's; HEAD `9954ad0` changes no `src/`) | 327 | 42,475 | 42.5 |
| Rust (upstream's count) | `6838ead` | 223 | 29,784 | 29.8 |
| C (upstream's count) | `ddaafaf` | 223 | 94,816 | 94.8 |
| Rails (upstream's count) | `0aa339d` | 194 | 4,443 | 4.4 |

`Campfire.RichText/Html5ever` (4 files, 3,582 lines) is a first-party F# port of the html5ever tokenizer, which Rust takes as a crate.
Without it, onCrack is 40.9 KLOC and the port 38.9. onCrack adds 2.0 KLOC to the port (`kloc.json`).

## Source, images and checks

| Implementation | Measured source | Image (this VM, arm64) | Built how |
|---|---|---|---|
| onCrack | `f5352d0` (clean worktree; HEAD of `crack`) | `campfire-oncrack:app` `sha256:155ea5d0e559` | `docker build` from HEAD, label `f5352d0`. `src/` equals `2ea9ae9`, the verifier fixes' image |
| F# port | `2e6c08e` | `campfire-fsharp:app` `sha256:421f335c3ff8` | Untouched since round 1 |
| Rust | `f9dca47` | `campfire-rust-upstream:f9dca47` `sha256:63d7de5e36bb` | `docker build .` with the `reference` submodule (`90b3300`); the media stages came from the build cache |
| C | `cd0cbe4` | `campfire-c-upstream:cd0cbe4` `sha256:cce0f35ccdc1` | See below |
| Rails | `0aa339d` | `campfire-rails-upstream:0aa339d` `sha256:55c45a003ba7` | `docker build .` (Ruby 4.0.7), under ten minutes |

**How C was built:**
- The pinned dependency fetch scripts ran, except Fil-C, which is x86-64 only and not part of the production image.
- Then `make deps-build MODE=bench` and `make MODE=bench build-app` ran with clang 19.1.7 in `debian:trixie`.
- The binary is `sha256:4f2ab17f882c`, static except libc and libm.
- `bench/image/Dockerfile.c` packaged it on `fedora:latest`, as `bench/run-c` does.

The image digests differ from upstream's published ones (theirs are amd64 builds of the same revisions).
`campfire-fsharp:app` and `campfire-oncrack:app` are the only .NET images. The pinned `campfire-rust:app` (`ccece30`) was not used.

**Harness:** `once-campfire-verification` `e244051`, plus two local commits that are not pushed:
- `ea9024a` adds `oncrack` and `fsharp` to the allowed apps, with their topology rows. onCrack honours
  `CAMPFIRE_RESPONSE_CACHE_MB`; the port has no response cache.
- `4e926db` validates those two apps' search against Rails `90b3300`'s order, and records `metadata.search_order` per app.

`git diff e244051 4e926db` (13 insertions, 5 deletions) is kept as [`oncrack-r2-final/scripts/verification-adapter.diff`](oncrack-r2-final/scripts/verification-adapter.diff),
with the build and run scripts beside it. The HTTP and write contracts, the load generator and the audits are unchanged.

**Load generator:** built from the harness's `loadgen/` (`--locked`) with Rust 1.98.1, statically linked for aarch64.
Its SHA-256 is `a0ac759b7407…`; upstream's x86-64 build is `26ac5ed0…`.

**Seed:** built by `bin/seed --image campfire-reference:app`, the project's pinned Rails `90b3300` image (`sha256:d2ca3b5d7a7f`; its env
carries `GIT_REVISION=90b3300…`).
- Its SHA-256 is `e0489b5ad564…`, not upstream's `036edd6a…`.
- Upstream's value cannot be reproduced by construction. `bin/seed` generates fresh credentials on every build (secret key base,
  login password, tokens), and their bcrypt digests are written into the database.
- A second build here gave a third SHA-256 (`d46fe052…`): the files differ in 584 bytes, and the `password_digest` values differ.
- Row counts are equal in every table checked: 10 users, 11 rooms, 39 memberships, 169 messages, 169 rich texts, 12 boosts and
  14 blobs.
- `fixtures/default` was made group-writable (`chmod -R g+w`), because the containers run as uid 1000 and the VM user is uid 501 in
  gid 1000. Nothing else about it changed.

**Topology, as `bin/benchmark` sets it:**
- Every app gets `WEB_CONCURRENCY=3`, `JOB_CONCURRENCY=3` and `RAILS_MAX_THREADS=5`.
- Rails gets `RAILS_BENCH_ENV` with 4 Puma workers × 1 thread, as upstream ran it.
- Cache budgets are 64 MiB:
  - onCrack: `CAMPFIRE_RESPONSE_CACHE_MB=64` (upstream's setting), split 1:4 between its read cache and its fast path.
  - Rust and Rails: their default of 64.
  - C: its default `CF_CACHE_BYTES`.
- Host network.

**CPUs:**
- Upstream's server CPUs 8-11 and generator CPUs 12-15 map to this VM's 0-3 (`--cpus 0-3`) and 4-7 (`--client-cpus 4-7`).
- The VM is colima, 8 vCPUs, 6 GiB, on an Apple M4 (4 performance and 6 efficiency cores). vCPUs are not pinned to host cores, so
  the 4 + 4 split is the VM's, not the hardware's.
- Databases and files ran on a tmpfs (`/mnt/cfv`, 3 GiB), as upstream's run on `/tmp` tmpfs.

**Same-machine scale:** this VM reaches 0.46-0.47x Rust's published Ryzen read rates, 0.53-0.55x C's, and 1.30-1.36x Rails'.
Compare ratios, not absolute numbers, with upstream's report.

## The review (assume it is wrong until shown otherwise)

**1. Could the load generator be the limit?**
- At onCrack's rate it used 2.55 of its 4 cores.
- The hand re-run read onCrack's server at 3.04-3.06 of 4 cores busy, at 17.6-17.9 µs of CPU per read.
- So the server is the limit, at its CPU per request. Neither side is saturated by the other.
- Rust and C ran at 2.9-3.3 cores busy.

**2. Hand re-run** ([`oncrack-r2-final/review.py`](oncrack-r2-final/review.py), `review.jsonl`). Done outside `bin/benchmark`:
- One container per app, the same seed, environment, CPUs and validation contracts.
- A 20 s warm-up at 16 clients before each 15 s window.
- Server CPU read from the container's cgroup.
- Every acknowledged post audited afterwards by the harness's own `AcknowledgedWrites.verify`.

| App | room page req/s (CPU µs, cores) | mixed reads (CPU µs) | post req/s (CPU µs) | harness medians: room / mixed / post | posts audited |
|---|---|---|---|---|---|
| onCrack | 170,643 (17.9, 3.06) | 173,605 (17.6) | 15,902 (184.9) | 173,975 / 170,862 / 15,214 | 555,345 ok |
| Rust | 49,228 (58.4, 2.88) | 46,039 (63.8) | 6,396 (456.2) | 50,006 / 47,636 / 6,549 | 225,197 ok |
| C | 75,843 (43.5, 3.30) | 73,953 (43.4) | 5,732 (587.6) | 75,833 / 72,453 / 5,867 | 200,835 ok |

Every hand-run read cell is within 3.5% of the harness's median for the same app, and every post cell within 5%. onCrack's lead is CPU per request:
- 3.3x less CPU than Rust and 2.4x less than C per room page read.
- 2.5x less than Rust and 3.2x less than C per post.

**3. Where does the lead come from?** The same image, same harness contracts, room page at c=16:

| onCrack setting | req/s | CPU µs | / Rust | / C |
|---|---:|---:|---:|---:|
| default (`CAMPFIRE_RESPONSE_CACHE_MB=64`) | 170,643 | 17.9 | 3.47x | 2.25x |
| fast path off (`CAMPFIRE_FAST_PATH=off`) | 122,749 | 30.4 | 2.49x | 1.62x |
| both caches off (`CAMPFIRE_RESPONSE_CACHE_MB=0`) | 38,668 | 91.0 | 0.79x | 0.51x |
| the F# port, for reference | 39,020 | 90.6 | 0.79x | 0.51x |

Two things follow:
- With its caches off, onCrack does the port's work and is slower than current Rust and C, which now have response caches of their own.
- Even without the fast path, its read cache keeps the authorization decision and does no SQL on a hit. That is the difference
  from upstream's "fresh authorization on every hit".

**4. Is that authorization still fresh?**
- The round 2 verifier attacked it with a second SQLite connection: a deleted session, a rotated token, a removed membership, a
  timestamped message, a rename, and timestamp-free edits of body, creator and boosts.
- After the WAL index watch, every case that Rails `90b3300` and Rust `ccece30` pass passes, plus the timestamp-free edits they
  fail ([`oncrack-r2-verifier.md`](oncrack-r2-verifier.md)).
- So in outcome, onCrack never serves a page or authorization older than the last commit. In mechanism, it does not re-read the
  session and membership rows that upstream's contract names.
- The multiples above are onCrack's design against theirs. Neither engine is doing the same work.

**5. Search order:**
- Without the adapter's order option, `bench/contracts.rb` refuses onCrack at preparation. The expected ids are
  `… 933434610 933434620`; onCrack and the port list 933434483 (created 2026-03-01, after the others) last.
- That is Rails `90b3300`'s `ordered.last(100)`. onCrack must keep it to stay pixel-identical with the reference the parity harness
  pins.
- On this seed the search work is 13 matches either way. On a large history, ordering by time sorts every match, where upstream's
  id order stops at the page.

**6. Gzip:**
- onCrack's room page is 24,074 bytes on the wire, the port's the same and current Rust's 24,230. C sends 21,251 and Rails 20,709, for
  the same 40 messages: they compress harder. The decoded HTML differs by under 1% (upstream's markup has moved on from `90b3300`, for
  one thing it no longer emits CSRF token fields).
- On loopback this costs nothing measurable. On a real network, onCrack sends about 13% more bytes per page than C.

**7. Short warm-up:**
- The harness warms each route for 2 s at 4 clients.
- onCrack reads the same on the harness and on the hand re-run (173,975 against 170,643).
- The port reads 8% lower on the harness than on the hand re-run (35,882 against 39,020). This is .NET's JIT tiering. The port's
  harness numbers are slightly pessimistic; onCrack's are not.

**8. Mixed profile:** onCrack's 0-2% loss is per-room invalidation, explained above. It is not an error: the validated reads are the
fixture's exact 40 messages and contents, and the writer's 960 posts were audited.

**9. Posts:**
- 15,214 posts/s at c=16, at 185 µs per post on the hand re-run. Every acknowledged post is in the database with its body and search
  entry.
- Rails-default durability: WAL with `synchronous=NORMAL`, as Rails. Group commit has a 0 µs window, and every post commits before
  its answer.
- The R2.2 WAL-restart stall did not show in these 8 s and 15 s windows: the post samples range 15,012-15,396.

**10. Disk:**
- The Mac's free space fell to 4.9 GB after the three image builds, below the 12 GB floor, just as the first session started. I
  stopped it at once, before any sample.
- I removed rebuildable images (`campfire-oncrack:r24`, the AOT images and toolchain, `debian:trixie`, `rust:1.98.1-trixie`), the
  cargo cache mounts and the verifier's 1.9 GB parity report, and trimmed the VM disk. Free space was 17 GB at the start.
- The VM disk grew by about 4 GB per session (containers' logs and layers, freed when each was removed), so I ran `fstrim` at every
  poll. Free space stayed at 13-17 GB.
- During the targeted pixel parity it fell to 11 GB; nothing else ran after that. Deleting the parity reports (their logs are kept) and
  trimming brought it back to 14 GB.

**11. A session I discarded:**
- The first full normal session failed in round 3: "oncrack: source changed between rounds". I had edited `site/build.py` in the
  checkout the harness reads.
- The rerun used a clean worktree of the same commit, and that rerun is the data.
- The aborted rounds (not committed) read within 3% of the rerun for onCrack, Rust, C and the port, and 2-7% lower for Rails.

**12. Pixel parity** (`oncrack-r2-final/pixel-parity/`). `src/` changed after the verifier's full 940-screenshot run (the fixer's WAL
index watch, per-epoch fragments, the messages page's ETag), so I ran the gate again on `campfire-candidate-oncrack` built from `f5352d0`:
- The four small seeds, lean matrix: 80/80 screenshots pixel-equal.
- The default seed, `--fast` (Chromium, light, desktop and phone), the states those changes reach: `messages/**` and `search/**` 72/72,
  `rooms/**` and `realtime/**` 100/100.
- So 252 screenshots, all equal. This is not the full gate: the rest of the default seed, dark mode, Firefox and WebKit were not re-run.
- `parity/bin/candidate build` rebuilt `campfire-oncrack:app` with its own build arguments, so the tag now points at `sha256:2b0ea6bc1d20`
  (same commit, same `src/`). The measured `sha256:155ea5d0e559` is no longer in the VM; the harness's `summary.json` records it.

**Nothing in this report has been adjusted. Not re-verified here:**
- `bin/verify`, the differentials and the verifier's attack scripts. No `src/` changed since the verifier fixes, which ran them.

## Appendix: this project's own suite

These are this project's harness and parity seed, not upstream's.

**Tier 3 on the rebuilt image** (`t3/`, `bench/quick`, 3 reps, image `sha256:155ea5d0e559`). onCrack is scored against the stored
phase7-final medians of the pinned Rust `ccece30` and the port. Median req/s [min-max] (CPU µs per request); `t3/vs-stored.md` has the
full table.

| Workload | c=1 | c=16 | c=16 / pinned Rust | c=16 / port |
|---|---|---|---|---|
| room page | 26,215 (18.9) | 177,276 [174,732-178,994] (17.4) | 6.19x | 4.39x |
| messages page | 26,199 (18.7) | 185,538 [178,378-187,179] (16.2) | 6.17x | 4.90x |
| sidebar | 26,821 (17.9) | 198,161 [198,115-198,627] (14.7) | 7.02x | 5.28x |
| search | 27,765 (17.3) | 192,737 [192,538-194,164] (15.4) | 7.24x | 5.66x |
| post a message | 5,112 (248.0) | 11,292 [10,732-12,470] (178.2) | 1.57x | 1.27x |

These agree with the verifier-fix image of the same `src/` within 1% on the read pages
([`oncrack-r2-verifier.md`](oncrack-r2-verifier.md)). Every response was 2xx, and post rows equal the answers. The run is logged to the
climb chart (unit `r2-final`, tier 3).

**Posts at c=16 read 11,292 here and 15,214 on upstream's harness.** This suite warms each route until it is flat, up to 90 s. After
that much sustained posting, the writer's WAL-restart stall (open since R2.2) hits every window, and all three post reps reached the
warm-up maximum. Upstream's two-second warm-up and eight-second samples end before it. Both numbers are real; the lower one is what
sustained posting costs today.

**Realistic workloads** (unit R2.0's suite, crowd seed, c=16 readers), from the round's last measurements of this `src/`. Tier 2,
`oncrack-r2-verifier/t2-real-after`:

| Workload | lane | req/s |
|---|---|---|
| mixed | reads | 42,583 |
| mixed | posts | 1,341 |
| spread | reads | 186,629 |
| spread_mixed | reads | 10,802 |
| spread_mixed | posts | 650 |
| search_spread | reads | 17,244 |

R2.5's tier 3 is in [`oncrack-r2-mem.md`](oncrack-r2-mem.md): spread 190,209, which is 7.41x the pinned Rust and 6.36x the port.
`spread_mixed` reads remain the one realistic lane below the pinned Rust (0.84x), the cost of a busy room invalidating its readers'
pages.

**Classic numbers against the pinned Rust (`ccece30`) are history now.** The climb chart keeps them (the page's panel "The climb
against pinned Rust").

## Reproducing

All of this runs inside colima.

```sh
# Upstream checkouts, built as their repositories describe (C: scripts/build-c.sh in a debian:trixie container, then Dockerfile.c)
git -C once-campfire-rust checkout f9dca47 && git -C once-campfire-rust submodule update --init reference
docker build -t campfire-rust-upstream:f9dca47 once-campfire-rust
docker build -t campfire-rails-upstream:0aa339d --build-arg APP_VERSION=0aa339d --build-arg GIT_REVISION=0aa339d81e05… once-campfire
docker build -t campfire-oncrack:app --build-arg SOURCE_REVISION=$(git rev-parse HEAD) --build-arg APP_VERSION=parity --build-arg GIT_REVISION=90b330024dec… .
# Harness on a tmpfs, workspace of symlinks to the five checkouts, adapter commits ea9024a + 4e926db
ruby bin/seed --image campfire-reference:app && chmod -R g+w fixtures/default/db fixtures/default/storage
export ONCRACK_IMAGE=campfire-oncrack:app ONCRACK_BENCH_ENV='{"CAMPFIRE_RESPONSE_CACHE_MB":"64"}' FSHARP_IMAGE=campfire-fsharp:app \
  RUST_IMAGE=campfire-rust-upstream:f9dca47 C_IMAGE=campfire-c-upstream:cd0cbe4 RAILS_IMAGE=campfire-rails-upstream:0aa339d \
  RAILS_BENCH_ENV='{"WEB_CONCURRENCY":"4","RAILS_MAX_THREADS":"1","RAILS_MIN_THREADS":"1"}'
bin/benchmark --workspace WS --rounds 3 --duration 8 --concurrencies 16 --cpus 0-3 --client-cpus 4-7 \
  --apps oncrack,rust,c,fsharp,rails --routes room_show,messages_page,sidebar,search,post_message
bin/benchmark … --mixed-write-rate 10 --routes room_show,messages_page,sidebar,search
python3 bench/results/oncrack-r2-final/table.py DIR...          # the tables above
python3 bench/results/oncrack-r2-final/review.py APP IMAGE OUT.jsonl [--env JSON] [--phases …] [--tag T]
```
