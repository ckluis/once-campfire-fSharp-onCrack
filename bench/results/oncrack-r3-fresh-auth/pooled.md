Pooled: median requests/sec of six rounds (two sessions x three) [min-max], 16 clients

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| onCrack, fresh authorization (default) | 122,438 [51,762-148,801] | 131,302 [66,791-157,148] | 138,444 [103,207-166,097] | 123,356 [91,056-161,791] | 12,756 [8,212-15,004] |
| onCrack, cached decision (opt-in) | 149,333 [111,174-172,448] | 161,776 [126,258-181,998] | 168,688 [137,834-188,639] | 178,097 [123,730-187,004] | 12,327 [8,985-15,440] |
| Rust f9dca47 | 47,154 [30,656-49,753] | 43,128 [29,400-47,645] | 46,094 [38,980-54,049] | 39,845 [34,280-54,686] | 5,144 [3,495-6,431] |
| C cd0cbe4 | 63,714 [48,918-75,085] | 60,961 [38,125-79,186] | 65,572 [44,544-81,981] | 73,910 [48,861-82,686] | 4,877 [3,206-5,894] |
| F# port | 24,824 [19,549-36,410] | 28,298 [24,030-40,603] | 28,399 [21,211-37,270] | 31,019 [22,408-32,974] | 8,529 [5,061-9,306] |

| ratio of pooled medians | Room page | Messages page | Sidebar | Search | Post a message | geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 2.60x | 3.04x | 3.00x | 3.10x | 2.48x | **2.83x** |
| oncrack / c | 1.92x | 2.15x | 2.11x | 1.67x | 2.62x | **2.07x** |
| oncrack / fsharp | 4.93x | 4.64x | 4.87x | 3.98x | 1.50x | **3.67x** |
| oncrack / oncrack-cached | 0.82x | 0.81x | 0.82x | 0.69x | 1.03x | **0.83x** |
| oncrack-cached / rust | 3.17x | 3.75x | 3.66x | 4.47x | 2.40x | **3.42x** |
| oncrack-cached / c | 2.34x | 2.65x | 2.57x | 2.41x | 2.53x | **2.50x** |
| oncrack-cached / fsharp | 6.02x | 5.72x | 5.94x | 5.74x | 1.45x | **4.42x** |

Hand re-runs (review.py, 15 s warm-up, 10 s window, server CPU from the cgroup): every window, then the medians

| App | phase | req/s per run | CPU us/request per run | median CPU us/request |
|---|---|---|---|---:|
| onCrack, fresh authorization (default) | room_show | 134,170, 129,470, 145,734, 102,815, 107,360 | 24.0, 25.1, 21.5, 28.6, 26.0 | 25.1 |
| onCrack, fresh authorization (default) | mixed | 147,494, 83,422 | 21.2, 32.9 | 27.0 |
| onCrack, cached decision (opt-in) | room_show | 169,145, 172,092, 175,932 | 18.8, 17.9, 17.4 | 17.9 |
| onCrack, cached decision (opt-in) | mixed | 175,672, 168,129 | 17.4, 18.1 | 17.7 |
| Rust f9dca47 | room_show | 45,835, 39,928, 46,378 | 62.1, 71.2, 61.9 | 62.1 |
| Rust f9dca47 | mixed | 47,978, 45,455 | 60.7, 64.1 | 62.4 |
| C cd0cbe4 | room_show | 68,622, 67,070, 75,620 | 48.1, 49.8, 43.5 | 48.1 |
| C cd0cbe4 | mixed | 71,622, 71,882 | 46.4, 46.4 | 46.4 |

| CPU per request, median over runs | room page | mixed reads |
|---|---:|---:|
| rust / oncrack | 2.47x | 2.31x |
| c / oncrack | 1.91x | 1.72x |
| rust / oncrack-cached | 3.46x | 3.52x |
| c / oncrack-cached | 2.68x | 2.61x |
| oncrack / oncrack-cached | 1.40x | 1.52x |
