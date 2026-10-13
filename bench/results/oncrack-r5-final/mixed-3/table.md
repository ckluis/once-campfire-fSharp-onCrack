## mixed-3 (mixed-read-write-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| Rails 0aa339d | 620 [78-2,287] | 886 [493-3,306] | 727 [662-3,353] | 1,110 [794-3,495] |
| Rust f9dca47 | 30,324 [25,102-34,150] | 30,271 [22,690-31,484] | 37,991 [11,534-38,675] | 37,689 [31,433-47,124] |
| C cd0cbe4 | 8,382 [5,003-62,230] | 18,519 [11,144-39,838] | 60,010 [9,753-69,949] | 53,835 [10,403-78,362] |
| F# port | 3,589 [927-28,389] | 10,246 [3,396-34,027] | 11,766 [2,592-29,660] | 16,014 [5,456-18,071] |
| onCrack (fresh authorization, default) | 106,496 [77,034-121,851] | 163,923 [124,098-174,600] | 70,045 [17,142-167,524] | 86,798 [41,843-161,717] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 129,493 [102,807-164,342] | 144,855 [138,199-177,601] | 149,539 [50,321-171,920] | 132,299 [10,636-166,093] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| Rails 0aa339d | 144,742 | 937 | 767 | 2.4-10.0 | 23.2 | 7.795 / 270.335 |
| Rust f9dca47 | 3,030,356 | 1,193 | 953 | 9.4-10.0 | 91.3 | 0.451 / 1.451 |
| C cd0cbe4 | 3,424,624 | 1,179 | 939 | 9.2-10.0 | 129.0 | 0.542 / 33.023 |
| F# port | 1,315,630 | 1,176 | 937 | 9.1-10.0 | 128.6 | 0.962 / 61.343 |
| onCrack (fresh authorization, default) | 10,508,804 | 1,192 | 952 | 9.6-10.0 | 239.8 | 0.119 / 0.701 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 12,307,146 | 1,190 | 950 | 9.4-10.0 | 246.8 | 0.106 / 0.465 |
| all | 30,731,302 | 6,867 | 5,498 | | 246.8 | |

| ratio (medians) | Room page | Messages page | Sidebar | Search | geometric mean |
|---|---:|---:|---:|---:|---:|
| oncrack / rust | 3.51x | 5.42x | 1.84x | 2.30x | **3.00x** |
| oncrack / c | 12.70x | 8.85x | 1.17x | 1.61x | **3.81x** |
| oncrack / fsharp | 29.67x | 16.00x | 5.95x | 5.42x | **11.13x** |
| oncrack / oncrack-cached | 0.82x | 1.13x | 0.47x | 0.66x | **0.73x** |
| oncrack-cached / rust | 4.27x | 4.79x | 3.94x | 3.51x | **4.10x** |
| oncrack-cached / c | 15.45x | 7.82x | 2.49x | 2.46x | **5.22x** |
| oncrack-cached / fsharp | 36.08x | 14.14x | 12.71x | 8.26x | **15.21x** |

| Implementation | Image id | Image label (revision) | Source HEAD (dirty?) |
|---|---|---|---|
| Rails 0aa339d | `sha256:a9a31e4b152d` | `-` | `0aa339d81e05` (clean) |
| Rust f9dca47 | `sha256:b0e047159ee2` | `-` | `f9dca47e592f` (clean) |
| C cd0cbe4 | `sha256:51001f452cc5` | `-` | `cd0cbe4b24bc` (clean) |
| F# port | `sha256:cccad24be9a1` | `` | `9954ad0b01e3` (clean) |
| onCrack (fresh authorization, default) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |

Harness `a05b344`; seed sha256 `34f665764593`; load generator sha256 `351a66af1ea1`; profile `mixed-read-write-v1`; started 2026-10-13T03:56:48Z.


144 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

