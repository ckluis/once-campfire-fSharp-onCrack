## upstream-normal-noisy (read-and-post-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| onCrack (fresh authorization, default) | 108,457 [51,762-119,221] | 124,868 [66,791-137,736] | 119,845 [103,207-147,420] | 98,937 [91,056-147,775] | 10,430 [8,212-14,343] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 149,467 [149,199-156,568] | 167,846 [155,706-169,254] | 173,255 [164,120-179,645] | 177,619 [155,285-178,575] | 12,308 [11,715-12,345] |
| Rust f9dca47 | 47,630 [46,677-48,687] | 45,040 [41,217-45,888] | 52,587 [39,602-52,665] | 38,365 [34,280-53,367] | 5,662 [4,626-6,234] |
| C cd0cbe4 | 52,282 [48,918-75,012] | 55,725 [38,125-72,883] | 62,778 [44,544-78,908] | 78,360 [48,861-79,048] | 5,505 [4,243-5,894] |
| F# port | 34,008 [19,629-36,410] | 29,381 [27,215-39,807] | 24,438 [21,906-34,345] | 31,555 [22,408-32,027] | 8,772 [5,404-9,198] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| onCrack (fresh authorization, default) | 10,805,407 | 289,969 | - | - | 223.2 | 0.122 / 0.778 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 16,105,152 | 319,669 | - | - | 257.0 | 0.098 / 0.278 |
| Rust f9dca47 | 4,500,650 | 158,454 | - | - | 97.6 | 0.309 / 0.767 |
| C cd0cbe4 | 6,009,503 | 153,584 | - | - | 135.7 | 0.262 / 0.822 |
| F# port | 3,012,644 | 217,617 | - | - | 146.4 | 0.421 / 1.139 |
| all | 40,433,356 | 1,139,293 | 0 | | 257.0 | |
| ratio (medians) | Room page | Messages page | Sidebar | Search | Post a message | geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 2.28x | 2.77x | 2.28x | 2.58x | 1.84x | **2.33x** |
| oncrack / c | 2.07x | 2.24x | 1.91x | 1.26x | 1.89x | **1.84x** |
| oncrack / fsharp | 3.19x | 4.25x | 4.90x | 3.14x | 1.19x | **3.01x** |
| oncrack / oncrack-cached | 0.73x | 0.74x | 0.69x | 0.56x | 0.85x | **0.71x** |
| oncrack-cached / rust | 3.14x | 3.73x | 3.29x | 4.63x | 2.17x | **3.29x** |
| oncrack-cached / c | 2.86x | 3.01x | 2.76x | 2.27x | 2.24x | **2.61x** |
| oncrack-cached / fsharp | 4.39x | 5.71x | 7.09x | 5.63x | 1.40x | **4.26x** |


150 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

## upstream-normal-2 (read-and-post-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| onCrack (fresh authorization, default) | 144,728 [125,654-148,801] | 154,984 [118,462-157,148] | 152,311 [129,468-166,097] | 161,056 [91,747-161,791] | 14,995 [11,170-15,004] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 124,730 [111,174-172,448] | 134,120 [126,258-181,998] | 146,037 [137,834-188,639] | 184,356 [123,730-187,004] | 15,125 [8,985-15,440] |
| Rust f9dca47 | 36,591 [30,656-49,753] | 33,217 [29,400-47,645] | 39,002 [38,980-54,049] | 41,325 [37,138-54,686] | 3,863 [3,495-6,431] |
| C cd0cbe4 | 69,824 [57,603-75,085] | 65,047 [56,875-79,186] | 68,367 [60,104-81,981] | 69,461 [58,718-82,686] | 4,315 [3,206-5,438] |
| F# port | 24,054 [19,549-25,593] | 24,891 [24,030-40,603] | 32,360 [21,211-37,270] | 30,484 [24,466-32,974] | 8,286 [5,061-9,306] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| onCrack (fresh authorization, default) | 14,028,554 | 362,834 | - | - | 226.4 | 0.098 / 0.269 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 14,864,491 | 357,503 | - | - | 252.3 | 0.102 / 0.730 |
| Rust f9dca47 | 4,050,344 | 138,608 | - | - | 97.8 | 0.384 / 1.220 |
| C cd0cbe4 | 6,703,771 | 129,559 | - | - | 137.6 | 0.216 / 0.489 |
| F# port | 2,881,487 | 209,714 | - | - | 142.5 | 0.556 / 2.075 |
| all | 42,528,647 | 1,198,218 | 0 | | 252.3 | |
| ratio (medians) | Room page | Messages page | Sidebar | Search | Post a message | geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 3.96x | 4.67x | 3.91x | 3.90x | 3.88x | **4.05x** |
| oncrack / c | 2.07x | 2.38x | 2.23x | 2.32x | 3.47x | **2.45x** |
| oncrack / fsharp | 6.02x | 6.23x | 4.71x | 5.28x | 1.81x | **4.42x** |
| oncrack / oncrack-cached | 1.16x | 1.16x | 1.04x | 0.87x | 0.99x | **1.04x** |
| oncrack-cached / rust | 3.41x | 4.04x | 3.74x | 4.46x | 3.92x | **3.90x** |
| oncrack-cached / c | 1.79x | 2.06x | 2.14x | 2.65x | 3.51x | **2.36x** |
| oncrack-cached / fsharp | 5.19x | 5.39x | 4.51x | 6.05x | 1.83x | **4.25x** |


150 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

## upstream-mixed (mixed-read-write-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| onCrack (fresh authorization, default) | 110,546 [42,262-126,396] | 105,063 [96,409-139,844] | 136,714 [129,864-145,655] | 133,647 [124,847-142,057] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 131,578 [121,495-136,060] | 144,926 [135,401-156,876] | 145,814 [111,708-167,782] | 163,500 [125,534-168,525] |
| Rust f9dca47 | 35,697 [28,981-41,236] | 28,990 [28,782-35,317] | 36,147 [27,639-43,539] | 42,816 [31,195-45,710] |
| C cd0cbe4 | 51,231 [41,158-59,396] | 60,618 [46,733-62,655] | 63,724 [60,243-67,542] | 61,864 [51,682-64,415] |
| F# port | 25,433 [12,372-26,460] | 32,413 [31,876-32,843] | 28,999 [22,720-30,208] | 28,854 [23,161-29,055] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| onCrack (fresh authorization, default) | 11,467,588 | 1,196 | 957 | 9.6-10.0 | 233.2 | 0.125 / 0.574 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 13,674,841 | 1,198 | 958 | 9.8-10.0 | 248.2 | 0.102 / 0.470 |
| Rust f9dca47 | 3,408,684 | 1,198 | 958 | 9.9-10.0 | 96.2 | 0.390 / 1.154 |
| C cd0cbe4 | 5,530,558 | 1,200 | 960 | 10.0-10.0 | 129.4 | 0.270 / 0.780 |
| F# port | 2,595,515 | 1,199 | 959 | 9.9-10.0 | 123.2 | 0.556 / 1.617 |
| all | 36,677,186 | 5,991 | 4,792 | | 248.2 | |
| ratio (medians) | Room page | Messages page | Sidebar | Search | geometric mean |
|---|---:|---:|---:|---:|---:|
| oncrack / rust | 3.10x | 3.62x | 3.78x | 3.12x | **3.39x** |
| oncrack / c | 2.16x | 1.73x | 2.15x | 2.16x | **2.04x** |
| oncrack / fsharp | 4.35x | 3.24x | 4.71x | 4.63x | **4.19x** |
| oncrack / oncrack-cached | 0.84x | 0.72x | 0.94x | 0.82x | **0.83x** |
| oncrack-cached / rust | 3.69x | 5.00x | 4.03x | 3.82x | **4.10x** |
| oncrack-cached / c | 2.57x | 2.39x | 2.29x | 2.64x | **2.47x** |
| oncrack-cached / fsharp | 5.17x | 4.47x | 5.03x | 5.67x | **5.07x** |


120 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

