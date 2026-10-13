## mixed-1 (mixed-read-write-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| Rails 0aa339d | 2,380 [68-2,617] | 2,232 [1,134-2,909] | 3,185 [653-3,523] | 2,991 [1,175-3,384] |
| Rust f9dca47 | 38,393 [14,806-39,364] | 42,408 [34,477-43,301] | 41,989 [41,562-51,364] | 6,738 [6,055-41,738] |
| C cd0cbe4 | 69,475 [18,032-70,330] | 68,755 [33,810-74,314] | 77,567 [65,121-79,393] | 62,188 [61,602-68,957] |
| F# port | 23,397 [2,310-32,067] | 39,467 [30,808-40,791] | 35,579 [31,442-36,949] | 29,610 [11,774-34,192] |
| onCrack (fresh authorization, default) | 144,613 [122,856-163,603] | 172,298 [32,681-176,140] | 167,185 [163,133-184,082] | 177,321 [159,690-182,873] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 60,110 [53,465-164,818] | 176,616 [86,636-181,520] | 188,455 [188,307-189,230] | 183,503 [167,969-186,291] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| Rails 0aa339d | 211,852 | 1,042 | 830 | 1.6-10.0 | 23.1 | 4.215 / 61.503 |
| Rust f9dca47 | 3,218,038 | 1,192 | 952 | 9.5-10.0 | 92.2 | 0.365 / 1.111 |
| C cd0cbe4 | 5,998,713 | 1,196 | 956 | 9.8-10.0 | 133.7 | 0.207 / 0.487 |
| F# port | 2,787,431 | 1,194 | 954 | 9.5-10.0 | 142.2 | 0.513 / 2.519 |
| onCrack (fresh authorization, default) | 14,780,001 | 1,196 | 956 | 9.6-10.0 | 244.6 | 0.099 / 0.333 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 14,618,224 | 1,197 | 957 | 9.7-10.0 | 251.5 | 0.102 / 2.399 |
| all | 41,614,259 | 7,017 | 5,605 | | 251.5 | |

| ratio (medians) | Room page | Messages page | Sidebar | Search | geometric mean |
|---|---:|---:|---:|---:|---:|
| oncrack / rust | 3.77x | 4.06x | 3.98x | 26.32x | **6.33x** |
| oncrack / c | 2.08x | 2.51x | 2.16x | 2.85x | **2.38x** |
| oncrack / fsharp | 6.18x | 4.37x | 4.70x | 5.99x | **5.25x** |
| oncrack / oncrack-cached | 2.41x | 0.98x | 0.89x | 0.97x | **1.19x** |
| oncrack-cached / rust | 1.57x | 4.16x | 4.49x | 27.23x | **5.31x** |
| oncrack-cached / c | 0.87x | 2.57x | 2.43x | 2.95x | **2.00x** |
| oncrack-cached / fsharp | 2.57x | 4.48x | 5.30x | 6.20x | **4.41x** |

| Implementation | Image id | Image label (revision) | Source HEAD (dirty?) |
|---|---|---|---|
| Rails 0aa339d | `sha256:a9a31e4b152d` | `-` | `0aa339d81e05` (clean) |
| Rust f9dca47 | `sha256:b0e047159ee2` | `-` | `f9dca47e592f` (clean) |
| C cd0cbe4 | `sha256:51001f452cc5` | `-` | `cd0cbe4b24bc` (clean) |
| F# port | `sha256:cccad24be9a1` | `` | `9954ad0b01e3` (clean) |
| onCrack (fresh authorization, default) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |

Harness `a05b344`; seed sha256 `34f665764593`; load generator sha256 `351a66af1ea1`; profile `mixed-read-write-v1`; started 2026-10-13T02:28:19Z.


144 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

