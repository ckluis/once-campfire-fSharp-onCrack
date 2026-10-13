## normal-1 (read-and-post-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| Rails 0aa339d | 4,005 [3,121-4,839] | 2,427 [1,186-4,731] | 4,662 [1,218-5,405] | 4,866 [4,606-5,383] | 360 [312-371] |
| Rust f9dca47 | 37,823 [17,612-41,288] | 43,896 [35,696-44,434] | 53,499 [40,532-55,386] | 48,999 [10,677-55,382] | 5,249 [5,001-6,392] |
| C cd0cbe4 | 63,246 [58,522-74,480] | 74,106 [14,224-74,431] | 70,294 [27,233-77,172] | 78,918 [43,029-80,266] | 5,562 [1,591-5,636] |
| F# port | 31,825 [17,109-33,393] | 38,488 [21,155-40,265] | 30,099 [21,918-34,742] | 29,373 [21,541-31,920] | 5,909 [4,456-8,332] |
| onCrack (fresh authorization, default) | 116,372 [59,273-159,841] | 85,500 [37,724-168,391] | 172,158 [163,818-183,123] | 170,944 [158,910-171,993] | 3,287 [1,975-12,449] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 166,566 [154,260-172,728] | 177,967 [172,052-184,859] | 190,038 [171,423-194,090] | 171,032 [167,470-187,215] | 12,489 [11,126-14,426] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| Rails 0aa339d | 380,633 | 9,727 | - | - | 28.2 | 3.401 / 9.879 |
| Rust f9dca47 | 4,015,396 | 160,208 | - | - | 97.2 | 0.388 / 0.971 |
| C cd0cbe4 | 5,991,462 | 133,585 | - | - | 138.4 | 0.232 / 0.602 |
| F# port | 2,964,638 | 176,012 | - | - | 142.6 | 0.455 / 1.222 |
| onCrack (fresh authorization, default) | 13,333,206 | 166,386 | - | - | 243.2 | 0.106 / 0.566 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 17,183,541 | 340,841 | - | - | 253.4 | 0.089 / 0.219 |
| all | 43,868,876 | 986,759 | 0 | | 253.4 | |

| ratio (medians) | Room page | Messages page | Sidebar | Search | Post a message | geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 3.08x | 1.95x | 3.22x | 3.49x | 0.63x | **2.11x** |
| oncrack / c | 1.84x | 1.15x | 2.45x | 2.17x | 0.59x | **1.46x** |
| oncrack / fsharp | 3.66x | 2.22x | 5.72x | 5.82x | 0.56x | **2.73x** |
| oncrack / oncrack-cached | 0.70x | 0.48x | 0.91x | 1.00x | 0.26x | **0.60x** |
| oncrack-cached / rust | 4.40x | 4.05x | 3.55x | 3.49x | 2.38x | **3.50x** |
| oncrack-cached / c | 2.63x | 2.40x | 2.70x | 2.17x | 2.25x | **2.42x** |
| oncrack-cached / fsharp | 5.23x | 4.62x | 6.31x | 5.82x | 2.11x | **4.52x** |

| Implementation | Image id | Image label (revision) | Source HEAD (dirty?) |
|---|---|---|---|
| Rails 0aa339d | `sha256:a9a31e4b152d` | `-` | `0aa339d81e05` (clean) |
| Rust f9dca47 | `sha256:b0e047159ee2` | `-` | `f9dca47e592f` (clean) |
| C cd0cbe4 | `sha256:51001f452cc5` | `-` | `cd0cbe4b24bc` (clean) |
| F# port | `sha256:cccad24be9a1` | `` | `9954ad0b01e3` (clean) |
| onCrack (fresh authorization, default) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |

Harness `a05b344`; seed sha256 `34f665764593`; load generator sha256 `351a66af1ea1`; profile `read-and-post-v1`; started 2026-10-13T02:07:38Z.


180 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

