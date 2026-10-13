## discarded-normal-1-all-routes (read-and-post-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search | Avatar | Static CSS | Health check | Post a message |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Rails 0aa339d | 3,059 [635-5,097] | 3,570 [2,869-3,933] | 3,786 [571-5,182] | 3,502 [3,346-3,565] | 47,834 [17,153-59,824] | 73,988 [49,265-87,165] | 4,672 [1,354-5,922] | 220 [200-223] |
| Rust f9dca47 | 36,285 [34,014-43,990] | 34,269 [30,401-42,851] | 34,554 [10,763-36,454] | 34,494 [30,134-36,237] | 90,674 [88,600-129,218] | 85,284 [46,450-132,077] | 74,526 [65,259-76,721] | 4,884 [3,470-6,038] |
| C cd0cbe4 | 32,907 [16,866-48,790] | 53,474 [43,800-66,182] | 53,173 [39,887-75,947] | 56,630 [48,585-77,075] | 34,719 [34,495-42,547] | 71,400 [63,174-75,642] | 101,643 [91,289-102,061] | 1,975 [1,208-3,691] |
| F# port | 33,904 [24,107-34,952] | 31,591 [29,622-41,272] | 25,791 [7,476-37,246] | 29,218 [28,022-33,299] | 162,998 [162,292-172,037] | 185,236 [126,671-194,886] | 92,267 [73,540-130,114] | 7,994 [6,439-8,978] |
| onCrack (fresh authorization, default) | 150,029 [135,744-152,670] | 156,883 [156,392-174,250] | 175,399 [167,212-186,208] | 178,566 [151,953-181,206] | 196,146 [184,279-196,569] | 215,855 [211,716-226,973] | 162,283 [147,968-185,030] | 9,541 [2,707-14,333] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 168,898 [117,908-172,379] | 150,579 [120,171-182,722] | 162,860 [54,474-193,471] | 180,045 [154,879-188,645] | 196,888 [163,597-198,492] | 219,987 [177,716-225,465] | 184,284 [170,700-186,563] | 14,895 [12,356-14,923] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| Rails 0aa339d | 3,096,611 | 5,909 | - | - | 131.0 | 4.643 / 16.271 |
| Rust f9dca47 | 9,662,582 | 141,776 | - | - | 157.4 | 0.393 / 1.087 |
| C cd0cbe4 | 9,900,624 | 71,236 | - | - | 160.9 | 0.287 / 3.201 |
| F# port | 13,440,842 | 212,916 | - | - | 305.3 | 0.420 / 1.197 |
| onCrack (fresh authorization, default) | 29,761,905 | 234,914 | - | - | 255.8 | 0.100 / 0.269 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 28,905,761 | 377,833 | - | - | 254.3 | 0.087 / 0.214 |
| all | 94,768,325 | 1,044,584 | 0 | | 305.3 | |

| ratio (medians) | Room page | Messages page | Sidebar | Search | Avatar | Static CSS | Health check | Post a message | geometric mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 4.13x | 4.58x | 5.08x | 5.18x | 2.16x | 2.53x | 2.18x | 1.95x | **3.22x** |
| oncrack / c | 4.56x | 2.93x | 3.30x | 3.15x | 5.65x | 3.02x | 1.60x | 4.83x | **3.41x** |
| oncrack / fsharp | 4.43x | 4.97x | 6.80x | 6.11x | 1.20x | 1.17x | 1.76x | 1.19x | **2.68x** |
| oncrack / oncrack-cached | 0.89x | 1.04x | 1.08x | 0.99x | 1.00x | 0.98x | 0.88x | 0.64x | **0.93x** |
| oncrack-cached / rust | 4.65x | 4.39x | 4.71x | 5.22x | 2.17x | 2.58x | 2.47x | 3.05x | **3.47x** |
| oncrack-cached / c | 5.13x | 2.82x | 3.06x | 3.18x | 5.67x | 3.08x | 1.81x | 7.54x | **3.68x** |
| oncrack-cached / fsharp | 4.98x | 4.77x | 6.31x | 6.16x | 1.21x | 1.19x | 2.00x | 1.86x | **2.89x** |

| Implementation | Image id | Image label (revision) | Source HEAD (dirty?) |
|---|---|---|---|
| Rails 0aa339d | `sha256:a9a31e4b152d` | `-` | `0aa339d81e05` (clean) |
| Rust f9dca47 | `sha256:b0e047159ee2` | `-` | `f9dca47e592f` (clean) |
| C cd0cbe4 | `sha256:51001f452cc5` | `-` | `cd0cbe4b24bc` (clean) |
| F# port | `sha256:cccad24be9a1` | `` | `9954ad0b01e3` (clean) |
| onCrack (fresh authorization, default) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | `sha256:bfcbb4633485` | `ee5a2e91795e` | `ee5a2e91795e` (clean) |

Harness `a05b344`; seed sha256 `34f665764593`; load generator sha256 `351a66af1ea1`; profile `read-and-post-v1`; started 2026-10-13T01:40:08Z.


288 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

