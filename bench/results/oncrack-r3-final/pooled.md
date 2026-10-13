### Normal profile

Median requests/sec of 6 rounds (2 sessions x 3) [min-max], 16 clients. Sessions: normal-1, normal-2

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| **onCrack, fresh authorization (default)** | 101,854 [52,285-134,892] | 109,301 [83,220-139,167] | 121,627 [90,646-161,502] | 116,437 [81,896-158,686] | 9,498 [4,385-14,966] |
| onCrack, cached decision (opt-in) | 125,900 [42,017-172,818] | 126,534 [98,510-178,751] | 147,264 [88,120-194,138] | 133,576 [94,078-186,747] | 9,382 [3,458-14,587] |
| Rust f9dca47 | 45,222 [22,315-50,525] | 36,259 [12,304-47,362] | 38,336 [19,601-55,424] | 43,320 [24,036-56,556] | 4,676 [2,290-6,484] |
| C cd0cbe4 | 57,925 [33,540-75,643] | 60,225 [29,140-78,426] | 63,723 [31,041-82,479] | 66,887 [30,426-81,908] | 4,494 [1,894-5,806] |
| F# port | 21,347 [6,660-35,778] | 24,754 [11,402-42,208] | 23,936 [11,153-38,323] | 22,998 [10,627-32,536] | 6,330 [3,100-9,192] |
| Rails 0aa339d | 4,904 [3,098-5,293] | 4,762 [2,191-5,060] | 5,032 [3,547-5,436] | 3,561 [2,360-5,428] | 320 [254-380] |

| Ratio of medians | Room page | Messages page | Sidebar | Search | Post a message | Geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 2.25x | 3.01x | 3.17x | 2.69x | 2.03x | **2.59x** |
| oncrack / c | 1.76x | 1.81x | 1.91x | 1.74x | 2.11x | **1.86x** |
| oncrack / fsharp | 4.77x | 4.42x | 5.08x | 5.06x | 1.50x | **3.82x** |
| oncrack / rails | 20.77x | 22.95x | 24.17x | 32.70x | 29.67x | **25.68x** |
| oncrack / oncrack-cached | 0.81x | 0.86x | 0.83x | 0.87x | 1.01x | **0.87x** |
| oncrack-cached / rust | 2.78x | 3.49x | 3.84x | 3.08x | 2.01x | **2.97x** |
| oncrack-cached / c | 2.17x | 2.10x | 2.31x | 2.00x | 2.09x | **2.13x** |
| oncrack-cached / fsharp | 5.90x | 5.11x | 6.15x | 5.81x | 1.48x | **4.37x** |
| c / rust | 1.28x | 1.66x | 1.66x | 1.54x | 0.96x | **1.39x** |

### Mixed profile (16 readers plus a writer at 10 posts/s)

Median requests/sec of 6 rounds (2 sessions x 3) [min-max], 16 clients. Sessions: mixed-1, mixed-2

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| **onCrack, fresh authorization (default)** | 122,314 [95,860-132,852] | 140,255 [124,520-144,262] | 146,126 [134,538-152,031] | 142,576 [92,917-153,951] |
| onCrack, cached decision (opt-in) | 140,225 [114,850-157,060] | 168,572 [157,228-183,498] | 176,433 [171,762-180,975] | 172,525 [165,735-182,067] |
| Rust f9dca47 | 40,086 [36,138-44,111] | 38,007 [32,884-41,826] | 44,834 [38,964-53,838] | 43,451 [41,185-53,540] |
| C cd0cbe4 | 63,643 [44,981-70,243] | 65,492 [54,012-71,568] | 68,254 [57,876-79,417] | 69,494 [46,980-78,659] |
| F# port | 25,832 [21,542-32,532] | 29,333 [22,808-40,009] | 28,207 [20,902-36,142] | 27,876 [23,414-31,550] |
| Rails 0aa339d | 1,872 [1,422-2,772] | 2,337 [2,056-3,628] | 3,565 [2,500-4,408] | 3,012 [2,316-3,607] |

| Ratio of medians | Room page | Messages page | Sidebar | Search | Geometric mean |
|---|---:|---:|---:|---:|---:|
| oncrack / rust | 3.05x | 3.69x | 3.26x | 3.28x | **3.31x** |
| oncrack / c | 1.92x | 2.14x | 2.14x | 2.05x | **2.06x** |
| oncrack / fsharp | 4.73x | 4.78x | 5.18x | 5.11x | **4.95x** |
| oncrack / rails | 65.33x | 60.03x | 40.98x | 47.34x | **52.52x** |
| oncrack / oncrack-cached | 0.87x | 0.83x | 0.83x | 0.83x | **0.84x** |
| oncrack-cached / rust | 3.50x | 4.44x | 3.94x | 3.97x | **3.95x** |
| oncrack-cached / c | 2.20x | 2.57x | 2.58x | 2.48x | **2.46x** |
| oncrack-cached / fsharp | 5.43x | 5.75x | 6.25x | 6.19x | **5.89x** |
| c / rust | 1.59x | 1.72x | 1.52x | 1.60x | **1.61x** |

### Hand re-runs (review.py: 15 s warm-up, 10 s window, 16 clients, server CPU from the cgroup)

| App | phase | req/s per run | CPU us/request per run | median req/s | median CPU us/request |
|---|---|---|---|---:|---:|
| **onCrack, fresh authorization (default)** | room_show | 136,506, 149,479, 139,180, 117,827, 149,482 | 24.0, 20.5, 23.0, 26.9, 20.6 | 139,180 | 23.0 |
| **onCrack, fresh authorization (default)** | mixed | 144,816, 144,640, 144,445, 128,533, 149,018 | 21.7, 21.5, 21.9, 26.0, 20.7 | 144,640 | 21.7 |
| **onCrack, fresh authorization (default)** | post_message | 15,077, 15,044, 14,882, 11,672, 15,924 | 200.2, 200.2, 201.6, 260.5, 188.2 | 15,044 | 200.2 |
| onCrack, cached decision (opt-in) | room_show | 172,373, 164,987, 161,405, 150,594, 174,839 | 18.2, 19.5, 19.6, 22.2, 17.7 | 164,987 | 19.5 |
| onCrack, cached decision (opt-in) | mixed | 169,035, 169,147, 173,444, 154,291, 173,864 | 18.5, 18.2, 17.6, 21.3, 17.7 | 169,147 | 18.2 |
| onCrack, cached decision (opt-in) | post_message | 15,172, 12,700, 12,627, 13,619, 15,755 | 196.5, 235.5, 236.1, 217.8, 187.7 | 13,619 | 217.8 |
| Rust f9dca47 | room_show | 46,777, 50,618, 39,875, 39,112, 50,765 | 62.6, 56.3, 69.1, 74.0, 56.8 | 46,777 | 62.6 |
| Rust f9dca47 | mixed | 45,128, 46,716, 47,943, 38,569, 48,358 | 65.8, 62.3, 60.8, 76.1, 60.6 | 46,716 | 62.3 |
| Rust f9dca47 | post_message | 5,888, 6,371, 4,547, 5,317, 6,423 | 494.0, 459.6, 575.2, 546.2, 453.9 | 5,888 | 494.0 |
| C cd0cbe4 | room_show | 75,796, 77,041, 50,471, 67,195, 75,956 | 43.4, 41.9, 57.6, 49.4, 43.5 | 75,796 | 43.5 |
| C cd0cbe4 | mixed | 67,760, 71,662, 57,986, 61,661, 72,000 | 49.5, 46.5, 57.5, 54.0, 46.9 | 67,760 | 49.5 |
| C cd0cbe4 | post_message | 5,514, 4,886, 4,527, 3,656, 5,806 | 608.1, 672.7, 726.3, 887.7, 580.8 | 4,886 | 672.7 |

| CPU per request, median over runs | room page | mixed reads | post |
|---|---:|---:|---:|
| rust / oncrack | 2.72x | 2.87x | 2.47x |
| c / oncrack | 1.89x | 2.28x | 3.36x |
| rust / oncrack-cached | 3.21x | 3.43x | 2.27x |
| c / oncrack-cached | 2.23x | 2.72x | 3.09x |
| oncrack / oncrack-cached | 1.18x | 1.19x | 0.92x |
