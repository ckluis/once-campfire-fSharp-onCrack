## normal-3 (read-and-post-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| Rails 0aa339d | 3,728 [1,329-4,160] | 3,628 [891-4,280] | 4,271 [4,114-4,298] | 2,971 [2,626-5,108] | 97 [36-328] |
| Rust f9dca47 | 17,807 [11,516-21,599] | 14,182 [4,663-25,702] | 17,335 [7,412-30,641] | 9,338 [4,203-9,970] | 3,720 [1,099-3,947] |
| C cd0cbe4 | 60,537 [54,914-73,659] | 73,880 [63,669-75,718] | 69,074 [65,397-71,229] | 59,600 [43,438-63,639] | 3,517 [1,973-4,297] |
| F# port | 3,892 [2,989-15,832] | 21,489 [10,928-35,136] | 19,884 [8,130-21,725] | 4,330 [2,419-9,603] | 3,671 [864-4,708] |
| onCrack (fresh authorization, default) | 135,859 [83,372-159,975] | 146,038 [74,786-172,988] | 66,048 [50,451-169,116] | 106,306 [60,920-166,161] | 2,608 [850-11,101] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 63,795 [55,229-145,943] | 162,359 [19,458-182,910] | 180,585 [155,200-191,386] | 165,760 [53,961-170,166] | 11,542 [5,856-12,289] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| Rails 0aa339d | 335,784 | 4,223 | - | - | 27.4 | 4.005 / 10.959 |
| Rust f9dca47 | 1,467,224 | 78,611 | - | - | 77.2 | 0.551 / 8.823 |
| C cd0cbe4 | 6,276,926 | 99,604 | - | - | 132.6 | 0.235 / 0.716 |
| F# port | 1,326,692 | 83,002 | - | - | 130.5 | 1.519 / 58.111 |
| onCrack (fresh authorization, default) | 11,262,065 | 131,560 | - | - | 247.9 | 0.109 / 0.350 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 12,617,068 | 260,676 | - | - | 246.6 | 0.133 / 1.782 |
| all | 33,285,759 | 657,676 | 0 | | 247.9 | |

| ratio (medians) | Room page | Messages page | Sidebar | Search | Post a message | geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 7.63x | 10.30x | 3.81x | 11.38x | 0.70x | **4.74x** |
| oncrack / c | 2.24x | 1.98x | 0.96x | 1.78x | 0.74x | **1.41x** |
| oncrack / fsharp | 34.91x | 6.80x | 3.32x | 24.55x | 0.71x | **6.72x** |
| oncrack / oncrack-cached | 2.13x | 0.90x | 0.37x | 0.64x | 0.23x | **0.63x** |
| oncrack-cached / rust | 3.58x | 11.45x | 10.42x | 17.75x | 3.10x | **7.49x** |
| oncrack-cached / c | 1.05x | 2.20x | 2.61x | 2.78x | 3.28x | **2.23x** |
| oncrack-cached / fsharp | 16.39x | 7.56x | 9.08x | 38.28x | 3.14x | **10.62x** |

| Implementation | Image id | Image label (revision) | Source HEAD (dirty?) |
|---|---|---|---|
| Rails 0aa339d | `sha256:a9a31e4b152d` | `-` | `0aa339d81e05` (clean) |
| Rust f9dca47 | `sha256:b0e047159ee2` | `-` | `f9dca47e592f` (clean) |
| C cd0cbe4 | `sha256:51001f452cc5` | `-` | `cd0cbe4b24bc` (clean) |
| F# port | `sha256:cccad24be9a1` | `` | `9954ad0b01e3` (clean) |
| onCrack (fresh authorization, default) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |

Harness `a05b344`; seed sha256 `34f665764593`; load generator sha256 `351a66af1ea1`; profile `read-and-post-v1`; started 2026-10-13T03:26:29Z.


180 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

