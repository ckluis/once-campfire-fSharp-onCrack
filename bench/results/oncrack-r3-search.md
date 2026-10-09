# onCrack round 3, unit R3.3: search order, 2026-10-09

Upstream's harness contract orders a search's results by message id (Rails `dbc7620`, `Message.search_reachable`). onCrack and the
F# port kept Rails `90b3300`'s created_at order, so round 2 needed a local adapter that checked the two against the old order. This unit
makes onCrack list search results the way current upstream does, removes onCrack from the adapter's special case, and measures search with
upstream's harness.

## What upstream does now

Read from `basecamp/once-campfire` (`~/Desktop/projects/upstream-campfire/once-campfire`):

- `edaab3e` ("Read the newest search matches off the index instead of sorting them all") orders search results by the full-text index's
  rowid, which is the message id, so SQLite walks the index newest first and stops at the page.
- `dbc7620` ("Bound accessible search probes ...") adds `Message.search_reachable(user, query, size: 100)`. It probes the newest 1,000
  index rows with a left join on the user's memberships, keeps the first 100 reachable ids, loads them `reorder(:id)` and takes the last
  100. When the probe finds fewer than 100 reachable ids and was full, it falls back to `reachable_messages.search(q).last_page_of_matches(100)`
  (ordered by `idx.rowid`). The probe is an optimisation. The answer is always: the newest 100 matches the user can reach, newest by
  message id, shown oldest first.
- `0aa339d` ("Avoid room queries for messages without mentions") does not touch search.
- `6cdcb45` (before both) quotes each word of a query, so `AND` is a word. onCrack already did this (`matchTerms`), as a deliberate
  difference from `90b3300`, which raises on `AND`.

## What changed

- `src/Campfire.Db/Models.fs`, `Message.searchReachable`: `ORDER BY idx.rowid DESC LIMIT 100` where it was `ORDER BY messages.created_at DESC
  LIMIT 100`, still reversed to oldest first. Commit `efd4ba1`. No other `src/` file changed (two doc comments).
- Tests (`tests/Campfire.Db.Tests/MessageTests.fs`): the order is by id when the clock disagrees, and the 100 kept are the 100 newest by id
  even when the lowest id has the latest time. Both fail on the old query and pass on the new one (checked both ways).
- **The parity oracle follows.** `reference/` is Rails `90b3300`, so the screenshot gate would compare onCrack's new order with the old one.
  `parity/docker/parity_search_order.rb` is baked into the reference image's parity layer and changes one method,
  `SearchesController#set_messages`, to `reachable_messages.search(query).reorder("idx.rowid").last(100)`: the same scope and the same 100,
  in upstream's order. Nothing else about the reference changed; `campfire-reference:app` (the image that builds the seeds) is untouched.
- **A parity state that can tell the orders apart.** Every existing search state had matches whose ids and times agree, so the F# port
  (old order) passed against an oracle in the new order. New state `search/results/order`: david searching "launch", 17 matches whose
  order differs by time and by id. onCrack is pixel-equal to the oracle there in all 4 cells; the port is different in all 4
  (`bench/results/oncrack-r3-search/pixels.json`).
- **The harness adapter** (local commit `a05b344`, not pushed): `search_order` is `created_at` only for the F# port and for a new app,
  `oncrack-prev`, onCrack as it was before this unit (`87c1ad1`, image `campfire-oncrack:prev`). `oncrack` and `oncrack-cached` use
  upstream's order and upstream's unchanged contract. The diff against upstream `e244051` is
  [`oncrack-r3-search/scripts/verification-adapter.diff`](oncrack-r3-search/scripts/verification-adapter.diff).
- `bench/results/oncrack-r2-final/review.py` no longer assumes onCrack uses the old order (`SEARCH_ORDER=created_at` for an older image).

## Does each app list the right messages? (`search_order.py`)

Outside the benchmark, on the harness seed: 4 users (david, jason, jz, kevin) x 12 queries = 48 pages per app, each page's message ids in
page order against the database's own answer (newest 100 reachable matches by id, oldest first). 38 of the 48 have results.

| App | pages equal | differ |
|---|---:|---:|
| onCrack (`campfire-oncrack:app`) | 48 of 48 | 0 |
| Rust `f9dca47` | 48 of 48 | 0 |
| C `cd0cbe4` | 48 of 48 | 0 |
| onCrack before this unit (`:prev`) | 30 of 48 | 18 |

The last row is the control: the check can fail, and the old order fails it wherever ids and times disagree.
The benchmark's own preflight agrees: with no special case, onCrack's `/searches?q=coffee` lists the same 13 ids as Rust and C
(`tables.md`, last block), and `oncrack-prev` and the port list the other order.

## Pixels (targeted, not the full gate)

- Image: `campfire-candidate-oncrack` on `campfire-oncrack:app` built from `efd4ba1` (`src/` equals the benchmark's `2b412e5`),
  against the reference with the one-method overlay.
- `bin/pixel-parity --seeds default,custom_styles --only 'search/**'`, the lean matrix: **38 of 38 screenshots pixel-equal**
  (default 34, including the 4 of the new state; custom_styles 4). `pixels.json` keeps every cell.
- This is not the 940-screenshot gate of R3.1: that ran on the code before this change. Only search results are listed differently,
  and only search pages show them; every other state is untouched by a one-query change. A full re-run is the next gate's job.
- `parity/coverage/templates.txt` was stale from earlier units; `check-templates --write` regenerated it with the new state (10 lines).

## Search with upstream's harness

Upstream's harness (`once-campfire-verification` + `a05b344`), `--routes search`, 3 rounds of 8 s at 16 clients each, two sessions pooled
into six rounds (the pooling was decided before the second ran, as in R3.2), and one mixed-profile session (16 readers plus a writer at
10 posts/s). Server CPUs 0-3, generator 4-7, as before. Every response was validated against the contract; the two normal sessions ran on
a quieter Mac than R3.2's (onCrack's, C's and the port's rounds sit within 2-9% of their medians; Rust's first session has one low round, 45,929).

Median requests/sec [observed min-max]:

| App | Normal, session 1 | Normal, session 2 | Normal, pooled (6 rounds) | Mixed (one session) |
|---|---:|---:|---:|---:|
| **onCrack** (fresh authorization, search by id) | 160,502 [158,501-161,260] | 161,476 [159,545-163,398] | **160,881** [158,501-163,398] | **151,590** [150,188-152,011] |
| onCrack before this unit (`87c1ad1`, search by time) | 160,709 [160,247-161,931] | 160,098 [150,191-161,853] | 160,478 [150,191-161,931] | 148,284 [138,548-151,367] |
| Rust `f9dca47` | 53,462 [45,929-56,114] | 55,961 [55,856-56,172] | 55,908 [45,929-56,172] | 54,898 [54,596-54,954] |
| C `cd0cbe4` | 80,622 [80,472-84,388] | 83,101 [82,778-83,981] | 82,940 [80,472-84,388] | 79,824 [79,569-82,092] |
| F# port | 30,795 [29,062-30,973] | 30,391 [30,020-31,038] | 30,593 [29,062-31,038] | 28,399 [24,172-30,072] |

| onCrack over | Normal, pooled | Mixed |
|---|---:|---:|
| Rust | 2.88x | 2.76x |
| C | 1.94x | 1.90x |
| the F# port | 5.26x | 5.34x |
| itself before this unit | 1.00x | 1.02x |

- **Search throughput did not change.** The harness's search page is a cache hit, served by the front server, and the order only matters
  to the query that fills the cache. 1.00x and 1.02x are noise (the old build's lowest round, 150,191, is its own noise).
- **Compared with R3.2's search** (pooled over its two noisy sessions): onCrack 123,356 [91,056-161,791], 3.10x Rust and 1.67x C. Here
  160,881 [158,501-163,398], 2.88x and 1.94x. The code is the same for the harness's page (a cache hit), so this is not a speed-up:
  R3.2's range shows how much the busy Mac moved every engine, and this is a quieter run. Read R3.3's figures as the cleaner ones for
  search, R3.2's as the five-workload headline.
- Validation: 11,640,754, 11,727,822 and 11,045,268 timed responses in the two normal sessions and the mixed one (all five apps, per
  app in `tables.md`), errors plus invalid responses 0 in every row. Mixed: each app acknowledged 300 writes (100 a round), all
  verified in the database and the search index. p50/p99 are in `tables.md`.
- Images (this VM, arm64): onCrack `campfire-oncrack:app` `sha256:88ae3de4b228`, label `2b412e5`; `:prev` `sha256:e4927fa7ec95`, label
  `87c1ad1` (the harness records the worktree's HEAD for both, `2b412e5`, because they share one source checkout);
  Rust, C and the port as in R3.2 (`63d7de5e36bb`, `cce0f35ccdc1`, `421f335c3ff8`). Seed `bc5a851525b4`, load generator `351a66af1ea1`.

## Where the order does change cost: cache misses

The harness never measures the query. `bench/quick --routes search_spread --real` does (525 users x 200 queries, so nearly every
request is a miss; the crowd seed), 6 alternating runs per build on the same container recipe:

| | req/s per run | median | CPU us/req per run | median |
|---|---|---:|---|---:|
| `:prev` (by time) | 23,484, 24,109, 14,995, 22,243, 23,944, 22,322 | 22,903 | 150, 148, 222, 160, 148, 156 | 153 |
| new (by id) | 21,581, 22,450, 21,491, 20,820, 23,748, 22,663 | 22,016 | 164, 158, 164, 172, 148, 155 | 161 |

- **No measurable change, and not a win.** The first four pairs read the new build 5-8% low; the next two pairs read them equal.
  The runs swing by more than that (one `:prev` run at 14,995), and the host probe in each run read 1.06-1.15 of its quiet speed.
  I do not claim a difference in either direction.
- **The query itself, in-process** (the app's SQLite 3.53.3, the crowd seed, 20,000 random user x word pairs, three repeats):
  8.5-8.7 us per query by rowid against 9.1-9.8 by created_at. About 0.6 us of a ~150 us request; the seed has only 169 messages.
- **On a large history** (300,000 messages, 60,000 of them matching "coffee", a user in 10 of 11 rooms; Python's SQLite 3.54):
  28 ms by created_at (it sorts every reachable match) against 0.1 ms by rowid (it walks the index newest first and stops at the page).
  That is the case the upstream change was made for. A page cached by version is not affected after its first read, but a busy
  history misses often.
- **The one case that gets slower, said plainly.** A user who can reach none or few of a very large match set (218,181 matches, user in one
  room that has none of them): 58 ms by rowid against 33 ms by created_at, because the index is walked newest first through every match.
  Upstream's own fallback, after its 1,000-row probe, does the same walk. I tried a bounded probe of my own; SQLite picked a bad join
  order for it (3-9 ms for the common case) and fixing that needs join-order hints, so I left it out. Not done: see the deferred list.

## Not re-verified here

- `bin/verify`, the differentials and the verifier's attack scripts. The change is one `ORDER BY` in a read query; no write path, cache
  rule or authorization check changed. The Db tests for messages and the App tests for searches pass on Linux (`bin/linux-tests`).
- The full 940-screenshot gate (see Pixels).

## Housekeeping

- Disk: the Mac sat at 11.7-13.7 GB free at the start (below or near the 12 GB floor). `bin/clean-docker` (build cache older than 1 h),
  then a full `docker buildx prune` (11.9 GB of cache; rebuilds will be slow once) and an `fstrim` took it to 19.5 GB. A first
  second-normal session was stopped by `guard.sh` when free space fell from 13 GB to 11 GB within 20 s (swap growth under the VM's
  memory load, not container logs); its partial data is in `aborted-guard-normal-2/` and is not used. The rerun is the data.
- Container logs were capped in the VM (`log-opts` max-size 64m, max-file 2) for the sessions and the original `daemon.json` is
  restored. `bin/clean-parity` and `bin/clean-docker` ran at the end; free space 19.5 GB.
- Two foreground commands of mine ran past the 600 s cap and were moved to the background by the tool (the loops of `search_spread`
  runs). Both completed on their own; nothing was interrupted.

## Reproducing

All of this runs inside colima, except the `site/build.py` and table steps.

```sh
# onCrack, before and after: clean worktree ~/Desktop/projects/oncrack-measured
git -C oncrack-measured checkout --detach 87c1ad1 && docker build -t campfire-oncrack:prev ...   # the old order
git -C oncrack-measured checkout --detach 2b412e5 && docker build -t campfire-oncrack:app ...    # this unit (args as parity/bin/candidate build)
scripts/setup-r32.sh                    # tmpfs, harness, loadgen, seed, workspace; harness at a05b344
run-r33.sh r33-normal-1 --apps oncrack,oncrack-prev,rust,c,fsharp --routes search   # and r33-normal-2
run-r33.sh r33-mixed --mixed-write-rate 10 --apps oncrack,oncrack-prev,rust,c,fsharp --routes search
python3 bench/results/oncrack-r3-search/table.py normal-1 normal-2 mixed
python3 bench/results/oncrack-r3-search/search_order.py oncrack campfire-oncrack:app OUT.json   # also rust, c, oncrack-prev
bin/pixel-parity --seeds default,custom_styles --only 'search/**'
ONCRACK_IMAGE=campfire-oncrack:prev bench/quick --routes search_spread --reps 1 --out DIR   # and :app
```

Data: [`oncrack-r3-search/`](oncrack-r3-search/) (`normal-1/`, `normal-2/`, `mixed/` are `bin/benchmark`'s output directories copied
whole; `spread-*/` are `bench/quick`'s; `search-order-*.json`; `pixels.json`; `tables.md`; `scripts/`).
