# R5 final: PR #6 reliability (step 8 of PLAN.md), 2026-10-13

Upstream's `bin/reliability` (verification repo branch `oncrack-reliability-working`, eed4105 plus its local `bench/reliability.rb` change that adds the onCrack apps),
through `bench/reliability/run` (descriptor limit 65,536, Pss sampler, loadgen rebuilt from the harness's `loadgen/`, sha `4568f79e1ce2`), 3 rounds, profiles `overload`
(room page, messages page, sidebar, search at 64 and 256 clients) and `cable` (1,000 clients; 4 posters, then `cable_heavy`: 64 closed-loop posters, 60 s drain limit).
Apps: Rails `0aa339d`, Rust `f9dca47`, C `cd0cbe4`, onCrack HEAD (image `bfcbb4633485`, sources `ee5a2e9`, src unchanged since `6abc183`), `oncrack-cached` (same image,
`CAMPFIRE_FRESH_AUTH=0`, opt-in), onCrack before R4.5 (image `campfire-oncrack:r45-before`, built from `21791e2`; worktree `/Users/clank/Desktop/projects/oncrack-r45-before`).
CPUs: server 0-3, client 4-7. Raw data: `main/` (six apps, overload and cable), `fsharp/` (the F# port, cable only), `fsharp-overload-check/`.

## Headline

| cable_heavy (1,000 clients, 64 posters, no limit) | disconnected (3 rounds) | delivered to every client / posted | msgs/s (median of rounds) |
|---|---|---|---|
| **onCrack HEAD (fresh authorization)** | **0 / 0 / 0** | every round: 13,571 of 13,571, 12,737 of 12,737, 13,608 of 13,608 | **738 / 710 / 741** |
| onCrack, cached decision (opt-in) | 0 / 0 / 0 | all delivered in all 3 | 629 / 738 / 705 |
| Rust f9dca47 | 944 / 902 / 959 | 65 of 76,602 ... | 4.3 |
| C cd0cbe4 | 809 / 848 / 821 (116 / 110 / 238 ever subscribed) | 67 of 66,217 ... | 4.5 / 1.6 / 1.0 |
| onCrack before R4.5 | 860 / 833 / 844 | 1 of 78,325 ... | 0.1 / 3.4 / 7.8 |
| Rails 0aa339d | 0 / 0 / 0 | all delivered in all 3 (705, 545, 356 posts) | 17 / 24 / 19 |
| F# port | 0 / 229 / 5 | 6,305 of 6,305; 3,375 of 5,757; 2,092 of 6,081 | 412 / 223 / 137 |

PR #6's claim holds again on the final code: onCrack keeps all 1,000 clients and every message in all 3 rounds (0 disconnected, 0 refused posts), where Rust and the
onCrack of before R4.5 lose 83-96% of the clients at saturation. Rails keeps everyone at 17-24 posts a second and 14-38 s p99. onCrack's price is memory
(Pss peak 947-1,068 MB at cable_heavy against Rust's 125 MB; the hub's total is bounded by `CAMPFIRE_CABLE_HUB_BYTES` 1 GiB) and a 8-10 s p99 from post to last client under a
workload that posts faster than 1,000 clients can read (the pressure gate holds posters).

The default `cable` profile (4 posters): onCrack 609-619 msgs/s against Rust's 507-520 (1.21x on the medians), 0 disconnected, p99 39-44 ms against Rust's 41-49 ms.
Overload (64 / 256 clients): onCrack is 211k-257k requests/s against Rust's 33k-56k, with 0 errors and 0 invalid in every round.

## Tables

### cable_heavy: 1,000 clients, 64 closed-loop posters with no limit, the harness waits up to 60 s for every client to have every message

| App | Rounds | Subscribed | Disconnected | Delivered to every client / posted | Messages/s | p99 post to last client, ms | Pss peak, MB |
|---|---:|---|---|---|---|---|---|
| Rails 0aa339d | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 705 of 705 / 545 of 545 / 356 of 356 | 17.4 / 24.3 / 18.5 | 37,519 / 13,754 / 15,876 | 3,259 / 3,357 / 2,864 |
| Rust f9dca47 | 3 | 1,000 / 1,000 / 1,000 | 944 / 902 / 959 | 65 of 76,602 / 64 of 68,190 / 65 of 77,958 | 4.3 / 4.3 / 4.3 | 430 / 391 / 408 | 125 / 126 / 125 |
| C cd0cbe4 | 3 | 116 / 110 / 238 | 809 / 848 / 821 | 67 of 66,217 / 24 of 58,385 / 15 of 51,202 | 4.5 / 1.6 / 1.0 | 231 / 54 / 39 | 71 / 71 / 71 |
| F# port | 3 | 1,000 / 1,000 / 1,000 | 0 / 229 / 5 | 6,305 of 6,305 / 3,375 of 5,757 / 2,092 of 6,081 | 412.4 / 222.7 / 137.0 | 666 / 831 / 749 | 2,651 / 2,591 / 2,693 |
| onCrack before R4.5 (`21791e2`) | 3 | 1,000 / 1,000 / 1,000 | 860 / 833 / 844 | 1 of 78,325 / 51 of 69,389 / 117 of 49,412 | 0.1 / 3.4 / 7.8 | 13 / 484 / 631 | 632 / 690 / 706 |
| **onCrack, fresh authorization (HEAD)** | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 13,571 of 13,571 / 12,737 of 12,737 / 13,608 of 13,608 | 738.3 / 710.0 / 741.0 | 9,773 / 8,008 / 9,339 | 996 / 1,068 / 947 |
| onCrack, cached decision (opt-in) | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 11,761 of 11,761 / 13,725 of 13,725 / 12,988 of 12,988 | 628.5 / 737.9 / 705.4 | 10,568 / 10,215 / 9,363 | 922 / 983 / 954 |

### cable: 1,000 clients, 4 posters (the default posting load)

| App | Rounds | Subscribed | Disconnected | Delivered to every client / posted | Messages/s | p99 post to last client, ms | Pss peak, MB |
|---|---:|---|---|---|---|---|---|
| Rails 0aa339d | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 428 of 428 / 301 of 301 / 420 of 420 | 27.5 / 19.7 / 27.7 | 1,511 / 1,806 / 738 | 3,003 / 2,910 / 3,244 |
| Rust f9dca47 | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 7,608 of 7,608 / 7,799 of 7,799 / 7,605 of 7,605 | 506.7 / 519.5 / 506.8 | 49 / 45 / 41 | 100 / 100 / 99 |
| C cd0cbe4 | 3 | 344 / 285 / 95 | 918 / 940 / 876 | 43 of 62,699 / 122 of 56,812 / 181 of 79,494 | 2.9 / 8.1 / 12.1 | 49 / 165 / 36 | 73 / 71 / 71 |
| F# port | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 5,021 of 5,021 / 3,892 of 3,892 / 4,471 of 4,471 | 334.5 / 259.1 / 297.7 | 90 / 122 / 89 | 570 / 586 / 551 |
| onCrack before R4.5 (`21791e2`) | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 8,682 of 8,682 / 8,934 of 8,934 / 8,751 of 8,751 | 578.4 / 595.1 / 583.0 | 43 / 48 / 172 | 281 / 279 / 304 |
| **onCrack, fresh authorization (HEAD)** | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 9,282 of 9,282 / 9,182 of 9,182 / 9,141 of 9,141 | 618.5 / 611.7 / 608.9 | 39 / 42 / 44 | 283 / 289 / 286 |
| onCrack, cached decision (opt-in) | 3 | 1,000 / 1,000 / 1,000 | 0 / 0 / 0 | 8,025 of 8,025 / 9,294 of 9,294 / 8,400 of 8,400 | 531.6 / 619.3 / 559.7 | 138 / 39 / 49 | 284 / 284 / 294 |


## Overload

Median requests/sec at 64 clients, 8 s per route, over the rounds that ran [rounds]; errors / invalid responses summed over them

| Implementation | Rounds | Room page | Messages page | Sidebar | Search | Errors / invalid |
|---|---:|---:|---:|---:|---:|---|
| Rails 0aa339d | 3 | 4,876 | 4,711 | 4,127 | 4,623 | 0 / 0 |
| Rust f9dca47 | 3 | 36,795 | 35,932 | 44,661 | 54,680 | 0 / 0 |
| C cd0cbe4 | 3 | 97,557 | 99,112 | 107,748 | 102,467 | 0 / 0 |
| onCrack before R4.5 | 3 | 165,545 | 220,230 | 216,686 | 207,246 | 0 / 0 |
| **onCrack, fresh (HEAD)** | 3 | 211,367 | 225,413 | 250,343 | 238,609 | 0 / 0 |
| onCrack, cached decision | 3 | 215,544 | 238,084 | 258,824 | 247,413 | 0 / 0 |

Median requests/sec at 256 clients, 8 s per route, over the rounds that ran [rounds]; errors / invalid responses summed over them

| Implementation | Rounds | Room page | Messages page | Sidebar | Search | Errors / invalid |
|---|---:|---:|---:|---:|---:|---|
| Rails 0aa339d | 3 | 5,087 | 4,498 | 4,928 | 5,269 | 0 / 0 |
| Rust f9dca47 | 3 | 35,985 | 35,420 | 56,294 | 48,064 | 0 / 0 |
| C cd0cbe4 | 3 | 89,202 | 96,323 | 109,829 | 104,824 | 0 / 195 |
| onCrack before R4.5 | 3 | 169,272 | 179,716 | 216,873 | 196,527 | 0 / 0 |
| **onCrack, fresh (HEAD)** | 3 | 196,107 | 218,411 | 257,084 | 242,023 | 0 / 0 |
| onCrack, cached decision | 3 | 199,882 | 233,804 | 269,079 | 247,644 | 0 / 0 |


## Notes, as observed (not investigated)

- **C's connection counts.** In every C cable round the load generator subscribed only 95-344 of the 1,000 clients on the default `cable` profile (and 110-238 in
  `cable_heavy`), and the rest are recorded as disconnected. Noted as observed; C is not investigated here. C also returned 195 invalid responses at 256 clients over the three
  rounds of overload (53 in the search route in one round; 0 errors); every other app: 0 / 0.
- **The F# port** was run on the cable profiles alone: its search order still fails the overload contract (`fsharp-overload-check/run.log`: `search: differs from seed SQL`,
  the harness's contract preparation, as in round 4). In `cable_heavy` it disconnected 229 clients in round 2 and 5 in round 3 and finished with posts undelivered (3,375 of 5,757; 2,092 of 6,081); its Pss peak is 2.6 GB.
- **onCrack before R4.5** is the control: 833-860 clients disconnected in cable_heavy, as round 4 measured (945 then).
- **The session was one run of the harness, but its wrapper was disturbed once.** At 04:09:32 the VM's disk guard (the Mac fell to 11.9 GiB because another project's Go build cache
  reached 7.0 GiB) killed the session's subshell. The harness itself (`ruby bin/reliability`) kept running: the guard watches the wrapper's pid, not the harness's (round 4's lesson, met
  again). The runner, believing it stopped, saved its directory aside, ran `go clean -cache` (no go process running; free 11.9 -> 19 GiB) at 04:09:39, started a second session (refused by the
  harness's benchmark lock, nothing run), then put the directory back and put a new guard on the harness's own pid. What the session lost is its wrapper's host-load loop for two minutes (the Mac sample
  file `host-load-reliability-main.txt` is unbroken but for that), its guard for two minutes, and its automatic copy of the harness JSON (copied by hand after it ended). `go clean -cache`
  ran during rust round 2's overload. Nothing was dropped or re-run: `main/` is rounds 1-3 as the one harness process wrote them.
  `session.sh` now stops the harness when the guard kills its wrapper.
- **Host noise (PLAN rule 2):** `main` 38 of 375 host samples (10%) with non-VM CPU >= 150%, `fsharp` 5 of 38 (13%): both under the 25% NOISY line.
- **Disk:** the Mac was at 11.9 GiB once (above), 15-19 GiB otherwise; `bin/clean-docker` and `bin/clean-parity` run before the session. No `src/` change.

## Scripts

`start.sh PART` (Mac: quiet wait and the detached start), `session.sh PART` (in the VM), `gocache-watch.sh` (started once; cleans another project's Go cache under 14 GiB free when no go process runs; it never fired),
`table.py`, `overload.py`, `bench/reliability/summarize` (`summarize.md`). Setup: `bench/results/oncrack-r4-final/scripts/setup-reliability.sh` (the harness copy with `.git`, `fixtures/default`, the static aarch64 loadgen)
plus a fourth fix found here: the harness workspace (`/mnt/cfv/ws`) needs `once-campfire-oncrack-prev` (symlink to the 21791e2 worktree).
