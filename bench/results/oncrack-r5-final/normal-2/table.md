## normal-2 (read-and-post-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| Rails 0aa339d | 4,181 [3,430-4,852] | 4,795 [2,866-4,796] | 5,111 [2,316-5,136] | 5,086 [2,624-5,345] | 373 [262-378] |
| Rust f9dca47 | 47,153 [30,806-48,636] | 42,141 [30,112-43,209] | 55,036 [35,604-55,055] | 44,424 [34,833-51,305] | 5,153 [4,073-6,076] |
| C cd0cbe4 | 71,446 [67,947-73,247] | 73,544 [63,986-76,997] | 47,710 [47,519-77,639] | 48,534 [39,698-79,294] | 3,269 [1,092-5,648] |
| F# port | 19,068 [17,103-28,149] | 26,722 [26,354-34,805] | 24,648 [22,901-32,195] | 24,496 [23,587-29,481] | 7,824 [6,788-7,863] |
| onCrack (fresh authorization, default) | 156,055 [153,660-161,968] | 157,290 [155,205-166,087] | 170,442 [168,348-170,975] | 164,928 [133,877-174,672] | 13,708 [8,726-13,732] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 157,148 [100,266-161,633] | 164,972 [27,602-174,024] | 175,264 [76,324-191,247] | 173,695 [111,461-176,596] | 12,583 [9,072-13,112] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| Rails 0aa339d | 412,638 | 9,210 | - | - | 28.1 | 3.577 / 9.799 |
| Rust f9dca47 | 4,269,497 | 152,153 | - | - | 97.5 | 0.310 / 0.786 |
| C cd0cbe4 | 6,221,419 | 97,851 | - | - | 135.7 | 0.209 / 0.486 |
| F# port | 2,656,247 | 205,304 | - | - | 131.6 | 0.739 / 2.267 |
| onCrack (fresh authorization, default) | 15,759,543 | 322,551 | - | - | 247.3 | 0.093 / 0.245 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 13,803,372 | 309,807 | - | - | 261.6 | 0.096 / 0.234 |
| all | 43,122,716 | 1,096,876 | 0 | | 261.6 | |

| ratio (medians) | Room page | Messages page | Sidebar | Search | Post a message | geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 3.31x | 3.73x | 3.10x | 3.71x | 2.66x | **3.28x** |
| oncrack / c | 2.18x | 2.14x | 3.57x | 3.40x | 4.19x | **2.99x** |
| oncrack / fsharp | 8.18x | 5.89x | 6.91x | 6.73x | 1.75x | **5.23x** |
| oncrack / oncrack-cached | 0.99x | 0.95x | 0.97x | 0.95x | 1.09x | **0.99x** |
| oncrack-cached / rust | 3.33x | 3.91x | 3.18x | 3.91x | 2.44x | **3.31x** |
| oncrack-cached / c | 2.20x | 2.24x | 3.67x | 3.58x | 3.85x | **3.02x** |
| oncrack-cached / fsharp | 8.24x | 6.17x | 7.11x | 7.09x | 1.61x | **5.29x** |

| Implementation | Image id | Image label (revision) | Source HEAD (dirty?) |
|---|---|---|---|
| Rails 0aa339d | `sha256:a9a31e4b152d` | `-` | `0aa339d81e05` (clean) |
| Rust f9dca47 | `sha256:b0e047159ee2` | `-` | `f9dca47e592f` (clean) |
| C cd0cbe4 | `sha256:51001f452cc5` | `-` | `cd0cbe4b24bc` (clean) |
| F# port | `sha256:cccad24be9a1` | `` | `9954ad0b01e3` (clean) |
| onCrack (fresh authorization, default) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |

Harness `a05b344`; seed sha256 `34f665764593`; load generator sha256 `351a66af1ea1`; profile `read-and-post-v1`; started 2026-10-13T02:42:54Z.


180 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

