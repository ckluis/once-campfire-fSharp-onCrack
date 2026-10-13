## mixed-2 (mixed-read-write-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| Rails 0aa339d | 2,532 [1,818-2,805] | 341 [256-2,706] | 3,374 [1,951-3,636] | 3,774 [3,367-3,819] |
| Rust f9dca47 | 37,918 [31,170-39,247] | 18,726 [11,186-27,412] | 30,245 [7,052-47,491] | 35,179 [25,687-50,054] |
| C cd0cbe4 | 50,283 [36,492-61,800] | 67,177 [49,452-70,066] | 70,942 [11,891-74,709] | 62,442 [58,819-65,632] |
| F# port | 15,648 [15,286-24,635] | 21,452 [21,385-21,913] | 21,453 [6,122-21,506] | 19,252 [2,788-21,942] |
| onCrack (fresh authorization, default) | 117,098 [9,787-152,834] | 118,810 [51,347-134,121] | 86,479 [18,282-180,293] | 59,141 [28,056-105,540] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 156,243 [43,741-162,054] | 158,977 [23,038-163,595] | 168,332 [164,172-175,420] | 158,101 [86,519-164,552] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| Rails 0aa339d | 243,916 | 1,081 | 880 | 4.0-10.0 | 25.0 | 4.135 / 59.743 |
| Rust f9dca47 | 2,892,956 | 1,191 | 951 | 9.6-10.0 | 94.5 | 0.348 / 1.079 |
| C cd0cbe4 | 5,438,125 | 1,198 | 958 | 9.9-10.0 | 130.7 | 0.270 / 0.815 |
| F# port | 1,707,457 | 1,194 | 954 | 9.6-10.0 | 112.2 | 0.870 / 3.015 |
| onCrack (fresh authorization, default) | 8,497,203 | 1,178 | 938 | 9.1-10.0 | 241.2 | 0.116 / 0.575 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 12,999,738 | 1,192 | 954 | 9.8-10.0 | 246.0 | 0.091 / 0.278 |
| all | 31,779,395 | 7,034 | 5,635 | | 246.0 | |

| ratio (medians) | Room page | Messages page | Sidebar | Search | geometric mean |
|---|---:|---:|---:|---:|---:|
| oncrack / rust | 3.09x | 6.34x | 2.86x | 1.68x | **3.12x** |
| oncrack / c | 2.33x | 1.77x | 1.22x | 0.95x | **1.48x** |
| oncrack / fsharp | 7.48x | 5.54x | 4.03x | 3.07x | **4.76x** |
| oncrack / oncrack-cached | 0.75x | 0.75x | 0.51x | 0.37x | **0.57x** |
| oncrack-cached / rust | 4.12x | 8.49x | 5.57x | 4.49x | **5.44x** |
| oncrack-cached / c | 3.11x | 2.37x | 2.37x | 2.53x | **2.58x** |
| oncrack-cached / fsharp | 9.99x | 7.41x | 7.85x | 8.21x | **8.31x** |

| Implementation | Image id | Image label (revision) | Source HEAD (dirty?) |
|---|---|---|---|
| Rails 0aa339d | `sha256:a9a31e4b152d` | `-` | `0aa339d81e05` (clean) |
| Rust f9dca47 | `sha256:b0e047159ee2` | `-` | `f9dca47e592f` (clean) |
| C cd0cbe4 | `sha256:51001f452cc5` | `-` | `cd0cbe4b24bc` (clean) |
| F# port | `sha256:cccad24be9a1` | `` | `9954ad0b01e3` (clean) |
| onCrack (fresh authorization, default) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |

Harness `a05b344`; seed sha256 `34f665764593`; load generator sha256 `351a66af1ea1`; profile `mixed-read-write-v1`; started 2026-10-13T03:09:25Z.


144 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

