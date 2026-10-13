## normal-1 (read-and-post-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| Rails 0aa339d | 5,150 [5,012-5,293] | 5,029 [5,007-5,060] | 5,339 [5,156-5,436] | 4,990 [3,142-5,428] | 371 [318-380] |
| Rust f9dca47 | 48,365 [44,306-50,525] | 47,291 [46,514-47,362] | 49,950 [47,055-55,424] | 50,610 [50,137-56,556] | 5,944 [5,732-6,484] |
| C cd0cbe4 | 74,638 [63,653-75,643] | 76,860 [71,060-78,426] | 80,888 [79,070-82,479] | 81,024 [79,148-81,908] | 5,792 [5,791-5,806] |
| F# port | 34,637 [32,531-35,778] | 40,007 [31,106-42,208] | 37,744 [31,808-38,323] | 31,869 [30,324-32,536] | 8,849 [8,384-9,192] |
| onCrack (fresh authorization, default) | 132,086 [127,635-134,892] | 138,863 [131,227-139,167] | 138,646 [138,351-161,502] | 150,566 [138,070-158,686] | 12,488 [11,658-14,966] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 157,399 [156,113-172,818] | 172,034 [143,364-178,751] | 186,320 [185,689-194,138] | 180,918 [161,855-186,747] | 14,128 [13,369-14,587] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| Rails 0aa339d | 489,113 | 9,827 | - | - | 30.3 | 2.997 / 7.111 |
| Rust f9dca47 | 4,898,535 | 180,098 | - | - | 98.6 | 0.303 / 0.769 |
| C cd0cbe4 | 7,538,479 | 171,954 | - | - | 141.4 | 0.202 / 0.456 |
| F# port | 3,562,778 | 245,922 | - | - | 149.0 | 0.415 / 1.121 |
| onCrack (fresh authorization, default) | 13,831,837 | 348,366 | - | - | 234.3 | 0.109 / 0.314 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 16,947,432 | 373,812 | - | - | 261.6 | 0.094 / 0.251 |
| all | 47,268,174 | 1,329,979 | 0 | | 261.6 | |

| ratio (medians) | Room page | Messages page | Sidebar | Search | Post a message | geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 2.73x | 2.94x | 2.78x | 2.98x | 2.10x | **2.68x** |
| oncrack / c | 1.77x | 1.81x | 1.71x | 1.86x | 2.16x | **1.85x** |
| oncrack / fsharp | 3.81x | 3.47x | 3.67x | 4.72x | 1.41x | **3.18x** |
| oncrack / oncrack-cached | 0.84x | 0.81x | 0.74x | 0.83x | 0.88x | **0.82x** |
| oncrack-cached / rust | 3.25x | 3.64x | 3.73x | 3.57x | 2.38x | **3.27x** |
| oncrack-cached / c | 2.11x | 2.24x | 2.30x | 2.23x | 2.44x | **2.26x** |
| oncrack-cached / fsharp | 4.54x | 4.30x | 4.94x | 5.68x | 1.60x | **3.88x** |

| Implementation | Image id | Image label (revision) | Source HEAD (dirty?) |
|---|---|---|---|
| Rails 0aa339d | `sha256:13be265cfa59` | `-` | `0aa339d81e05` (clean) |
| Rust f9dca47 | `sha256:63d7de5e36bb` | `-` | `f9dca47e592f` (clean) |
| C cd0cbe4 | `sha256:cce0f35ccdc1` | `cd0cbe4b24bc` | `cd0cbe4b24bc` (clean) |
| F# port | `sha256:421f335c3ff8` | `2e6c08e24219` | `9954ad0b01e3` (clean) |
| onCrack (fresh authorization, default) | `sha256:69deaa8cdf60` | `191c468cf72a` | `191c468cf72a` (clean) |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | `sha256:69deaa8cdf60` | `191c468cf72a` | `191c468cf72a` (clean) |

Harness `a05b344`; seed sha256 `4381b911d1c5`; load generator sha256 `351a66af1ea1`; profile `read-and-post-v1`; started 2026-10-09T19:54:38Z.


180 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

## normal-2 (read-and-post-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| Rails 0aa339d | 3,448 [3,098-4,796] | 3,343 [2,191-4,518] | 3,912 [3,547-4,909] | 3,334 [2,360-3,788] | 310 [254-322] |
| Rust f9dca47 | 22,616 [22,315-46,139] | 19,024 [12,304-26,003] | 23,143 [19,601-29,617] | 27,328 [24,036-36,503] | 2,916 [2,290-3,620] |
| C cd0cbe4 | 36,305 [33,540-52,198] | 36,194 [29,140-49,389] | 36,245 [31,041-48,376] | 39,103 [30,426-54,626] | 2,651 [1,894-3,196] |
| F# port | 8,250 [6,660-10,163] | 14,817 [11,402-18,401] | 14,364 [11,153-16,065] | 13,158 [10,627-15,671] | 4,194 [3,100-4,276] |
| onCrack (fresh authorization, default) | 75,760 [52,285-76,074] | 83,782 [83,220-87,375] | 92,740 [90,646-104,903] | 86,772 [81,896-94,804] | 6,385 [4,385-7,339] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 83,258 [42,017-95,687] | 103,766 [98,510-109,703] | 93,687 [88,120-108,839] | 101,830 [94,078-105,297] | 3,762 [3,458-5,394] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| Rails 0aa339d | 353,353 | 7,965 | - | - | 26.5 | 4.119 / 14.255 |
| Rust f9dca47 | 2,540,054 | 89,391 | - | - | 98.4 | 0.617 / 1.588 |
| C cd0cbe4 | 3,875,275 | 76,121 | - | - | 136.5 | 0.409 / 1.012 |
| F# port | 1,298,791 | 106,142 | - | - | 95.0 | 1.513 / 9.919 |
| onCrack (fresh authorization, default) | 8,228,360 | 161,248 | - | - | 265.1 | 0.179 / 0.835 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 9,101,059 | 114,593 | - | - | 300.9 | 0.146 / 0.771 |
| all | 25,396,892 | 555,460 | 0 | | 300.9 | |

| ratio (medians) | Room page | Messages page | Sidebar | Search | Post a message | geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 3.35x | 4.40x | 4.01x | 3.18x | 2.19x | **3.33x** |
| oncrack / c | 2.09x | 2.31x | 2.56x | 2.22x | 2.41x | **2.31x** |
| oncrack / fsharp | 9.18x | 5.65x | 6.46x | 6.59x | 1.52x | **5.07x** |
| oncrack / oncrack-cached | 0.91x | 0.81x | 0.99x | 0.85x | 1.70x | **1.01x** |
| oncrack-cached / rust | 3.68x | 5.45x | 4.05x | 3.73x | 1.29x | **3.30x** |
| oncrack-cached / c | 2.29x | 2.87x | 2.58x | 2.60x | 1.42x | **2.29x** |
| oncrack-cached / fsharp | 10.09x | 7.00x | 6.52x | 7.74x | 0.90x | **5.02x** |

| Implementation | Image id | Image label (revision) | Source HEAD (dirty?) |
|---|---|---|---|
| Rails 0aa339d | `sha256:13be265cfa59` | `-` | `0aa339d81e05` (clean) |
| Rust f9dca47 | `sha256:63d7de5e36bb` | `-` | `f9dca47e592f` (clean) |
| C cd0cbe4 | `sha256:cce0f35ccdc1` | `cd0cbe4b24bc` | `cd0cbe4b24bc` (clean) |
| F# port | `sha256:421f335c3ff8` | `2e6c08e24219` | `9954ad0b01e3` (clean) |
| onCrack (fresh authorization, default) | `sha256:69deaa8cdf60` | `191c468cf72a` | `191c468cf72a` (clean) |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | `sha256:69deaa8cdf60` | `191c468cf72a` | `191c468cf72a` (clean) |

Harness `a05b344`; seed sha256 `4381b911d1c5`; load generator sha256 `351a66af1ea1`; profile `read-and-post-v1`; started 2026-10-09T23:55:35Z.


180 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

## mixed-1 (mixed-read-write-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| Rails 0aa339d | 2,130 [1,422-2,602] | 2,399 [2,265-2,952] | 3,593 [3,538-3,933] | 3,372 [3,369-3,607] |
| Rust f9dca47 | 39,010 [36,138-41,162] | 33,494 [32,884-37,119] | 44,946 [38,964-45,701] | 42,002 [41,185-44,818] |
| C cd0cbe4 | 59,072 [44,981-68,213] | 58,416 [54,012-66,050] | 62,299 [57,876-64,069] | 66,353 [46,980-70,754] |
| F# port | 27,768 [21,542-28,047] | 24,922 [24,129-33,744] | 25,057 [22,938-31,993] | 28,265 [23,414-30,594] |
| onCrack (fresh authorization, default) | 126,135 [95,860-130,410] | 143,794 [124,520-144,262] | 151,374 [138,029-152,031] | 144,453 [143,567-153,951] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 129,980 [114,850-157,060] | 171,391 [168,232-183,498] | 178,187 [176,900-180,975] | 178,609 [172,328-182,067] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| Rails 0aa339d | 282,605 | 1,179 | 957 | 9.8-10.0 | 26.8 | 4.511 / 68.351 |
| Rust f9dca47 | 3,819,847 | 1,200 | 960 | 10.0-10.0 | 97.3 | 0.358 / 1.019 |
| C cd0cbe4 | 5,753,235 | 1,199 | 959 | 9.9-10.0 | 132.1 | 0.234 / 0.675 |
| F# port | 2,579,614 | 1,198 | 958 | 9.9-10.0 | 128.3 | 0.512 / 1.482 |
| onCrack (fresh authorization, default) | 13,188,185 | 1,200 | 960 | 10.0-10.0 | 235.4 | 0.110 / 0.379 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 15,953,868 | 1,200 | 960 | 10.0-10.0 | 260.3 | 0.102 / 0.541 |
| all | 41,577,354 | 7,176 | 5,754 | | 260.3 | |

| ratio (medians) | Room page | Messages page | Sidebar | Search | geometric mean |
|---|---:|---:|---:|---:|---:|
| oncrack / rust | 3.23x | 4.29x | 3.37x | 3.44x | **3.56x** |
| oncrack / c | 2.14x | 2.46x | 2.43x | 2.18x | **2.30x** |
| oncrack / fsharp | 4.54x | 5.77x | 6.04x | 5.11x | **5.33x** |
| oncrack / oncrack-cached | 0.97x | 0.84x | 0.85x | 0.81x | **0.86x** |
| oncrack-cached / rust | 3.33x | 5.12x | 3.96x | 4.25x | **4.12x** |
| oncrack-cached / c | 2.20x | 2.93x | 2.86x | 2.69x | **2.66x** |
| oncrack-cached / fsharp | 4.68x | 6.88x | 7.11x | 6.32x | **6.17x** |

| Implementation | Image id | Image label (revision) | Source HEAD (dirty?) |
|---|---|---|---|
| Rails 0aa339d | `sha256:13be265cfa59` | `-` | `0aa339d81e05` (clean) |
| Rust f9dca47 | `sha256:63d7de5e36bb` | `-` | `f9dca47e592f` (clean) |
| C cd0cbe4 | `sha256:cce0f35ccdc1` | `cd0cbe4b24bc` | `cd0cbe4b24bc` (clean) |
| F# port | `sha256:421f335c3ff8` | `2e6c08e24219` | `9954ad0b01e3` (clean) |
| onCrack (fresh authorization, default) | `sha256:69deaa8cdf60` | `191c468cf72a` | `191c468cf72a` (clean) |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | `sha256:69deaa8cdf60` | `191c468cf72a` | `191c468cf72a` (clean) |

Harness `a05b344`; seed sha256 `4381b911d1c5`; load generator sha256 `351a66af1ea1`; profile `mixed-read-write-v1`; started 2026-10-09T20:21:57Z.


144 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

## mixed-2 (mixed-read-write-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| Rails 0aa339d | 1,614 [1,573-2,772] | 2,274 [2,056-3,628] | 2,715 [2,500-4,408] | 2,518 [2,316-2,655] |
| Rust f9dca47 | 43,723 [37,176-44,111] | 41,524 [38,895-41,826] | 44,722 [40,782-53,838] | 45,219 [42,084-53,540] |
| C cd0cbe4 | 69,784 [54,664-70,243] | 71,091 [64,934-71,568] | 78,752 [72,438-79,417] | 77,266 [68,234-78,659] |
| F# port | 23,897 [23,748-32,532] | 35,486 [22,808-40,009] | 31,357 [20,902-36,142] | 27,488 [25,855-31,550] |
| onCrack (fresh authorization, default) | 118,492 [115,975-132,852] | 139,791 [139,377-140,720] | 145,649 [134,538-146,603] | 140,724 [92,917-141,586] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 150,470 [118,436-152,740] | 158,116 [157,228-168,912] | 175,883 [171,762-175,966] | 172,411 [165,735-172,638] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| Rails 0aa339d | 249,417 | 1,182 | 956 | 9.7-10.0 | 22.8 | 5.279 / 103.871 |
| Rust f9dca47 | 4,219,952 | 1,200 | 960 | 10.0-10.0 | 95.2 | 0.318 / 0.949 |
| C cd0cbe4 | 6,856,876 | 1,200 | 960 | 10.0-10.0 | 134.9 | 0.206 / 0.498 |
| F# port | 2,814,551 | 1,197 | 957 | 9.8-10.0 | 140.3 | 0.576 / 1.776 |
| onCrack (fresh authorization, default) | 12,715,000 | 1,199 | 959 | 9.9-10.0 | 226.2 | 0.117 / 0.448 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 15,523,636 | 1,200 | 960 | 10.0-10.0 | 246.3 | 0.095 / 0.298 |
| all | 42,379,432 | 7,178 | 5,752 | | 246.3 | |

| ratio (medians) | Room page | Messages page | Sidebar | Search | geometric mean |
|---|---:|---:|---:|---:|---:|
| oncrack / rust | 2.71x | 3.37x | 3.26x | 3.11x | **3.10x** |
| oncrack / c | 1.70x | 1.97x | 1.85x | 1.82x | **1.83x** |
| oncrack / fsharp | 4.96x | 3.94x | 4.64x | 5.12x | **4.64x** |
| oncrack / oncrack-cached | 0.79x | 0.88x | 0.83x | 0.82x | **0.83x** |
| oncrack-cached / rust | 3.44x | 3.81x | 3.93x | 3.81x | **3.74x** |
| oncrack-cached / c | 2.16x | 2.22x | 2.23x | 2.23x | **2.21x** |
| oncrack-cached / fsharp | 6.30x | 4.46x | 5.61x | 6.27x | **5.61x** |

| Implementation | Image id | Image label (revision) | Source HEAD (dirty?) |
|---|---|---|---|
| Rails 0aa339d | `sha256:13be265cfa59` | `-` | `0aa339d81e05` (clean) |
| Rust f9dca47 | `sha256:63d7de5e36bb` | `-` | `f9dca47e592f` (clean) |
| C cd0cbe4 | `sha256:cce0f35ccdc1` | `cd0cbe4b24bc` | `cd0cbe4b24bc` (clean) |
| F# port | `sha256:421f335c3ff8` | `2e6c08e24219` | `9954ad0b01e3` (clean) |
| onCrack (fresh authorization, default) | `sha256:69deaa8cdf60` | `191c468cf72a` | `191c468cf72a` (clean) |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | `sha256:69deaa8cdf60` | `191c468cf72a` | `191c468cf72a` (clean) |

Harness `a05b344`; seed sha256 `4381b911d1c5`; load generator sha256 `351a66af1ea1`; profile `mixed-read-write-v1`; started 2026-10-09T20:48:25Z.


144 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

