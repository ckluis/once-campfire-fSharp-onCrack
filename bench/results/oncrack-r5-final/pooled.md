### Normal profile

Median requests/sec of 9 rounds (3 sessions x 3) [min-max], 16 clients. Sessions: normal-1, normal-2, normal-3

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| **onCrack, fresh authorization (default)** | 153,660 [59,273-161,968] | 155,205 [37,724-172,988] | 169,116 [50,451-183,123] | 164,928 [60,920-174,672] | 8,726 [850-13,732] |
| onCrack, cached decision (opt-in) | 154,260 [55,229-172,728] | 172,052 [19,458-184,859] | 180,585 [76,324-194,090] | 170,166 [53,961-187,215] | 12,289 [5,856-14,426] |
| Rust f9dca47 | 30,806 [11,516-48,636] | 35,696 [4,663-44,434] | 40,532 [7,412-55,386] | 34,833 [4,203-55,382] | 5,001 [1,099-6,392] |
| C cd0cbe4 | 67,947 [54,914-74,480] | 73,880 [14,224-76,997] | 69,074 [27,233-77,639] | 59,600 [39,698-80,266] | 3,517 [1,092-5,648] |
| F# port | 17,109 [2,989-33,393] | 26,722 [10,928-40,265] | 22,901 [8,130-34,742] | 23,587 [2,419-31,920] | 5,909 [864-8,332] |
| Rails 0aa339d | 4,005 [1,329-4,852] | 3,628 [891-4,796] | 4,298 [1,218-5,405] | 4,866 [2,624-5,383] | 328 [36-378] |

| Ratio of medians | Room page | Messages page | Sidebar | Search | Post a message | Geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 4.99x | 4.35x | 4.17x | 4.73x | 1.74x | **3.76x** |
| oncrack / c | 2.26x | 2.10x | 2.45x | 2.77x | 2.48x | **2.40x** |
| oncrack / fsharp | 8.98x | 5.81x | 7.38x | 6.99x | 1.48x | **5.25x** |
| oncrack / rails | 38.37x | 42.78x | 39.35x | 33.89x | 26.63x | **35.74x** |
| oncrack / oncrack-cached | 1.00x | 0.90x | 0.94x | 0.97x | 0.71x | **0.90x** |
| oncrack-cached / rust | 5.01x | 4.82x | 4.46x | 4.89x | 2.46x | **4.19x** |
| oncrack-cached / c | 2.27x | 2.33x | 2.61x | 2.86x | 3.49x | **2.68x** |
| oncrack-cached / fsharp | 9.02x | 6.44x | 7.89x | 7.21x | 2.08x | **5.85x** |
| c / rust | 2.21x | 2.07x | 1.70x | 1.71x | 0.70x | **1.56x** |

### Mixed profile (16 readers plus a writer at 10 posts/s)

Median requests/sec of 9 rounds (3 sessions x 3) [min-max], 16 clients. Sessions: mixed-1, mixed-2, mixed-3

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| **onCrack, fresh authorization (default)** | 121,851 [9,787-163,603] | 134,121 [32,681-176,140] | 163,133 [17,142-184,082] | 105,540 [28,056-182,873] |
| onCrack, cached decision (opt-in) | 129,493 [43,741-164,818] | 158,977 [23,038-181,520] | 171,920 [50,321-189,230] | 164,552 [10,636-186,291] |
| Rust f9dca47 | 34,150 [14,806-39,364] | 30,271 [11,186-43,301] | 38,675 [7,052-51,364] | 35,179 [6,055-50,054] |
| C cd0cbe4 | 50,283 [5,003-70,330] | 49,452 [11,144-74,314] | 69,949 [9,753-79,393] | 62,188 [10,403-78,362] |
| F# port | 15,648 [927-32,067] | 21,913 [3,396-40,791] | 21,506 [2,592-36,949] | 18,071 [2,788-34,192] |
| Rails 0aa339d | 2,287 [68-2,805] | 1,134 [256-3,306] | 3,185 [653-3,636] | 3,367 [794-3,819] |

| Ratio of medians | Room page | Messages page | Sidebar | Search | Geometric mean |
|---|---:|---:|---:|---:|---:|
| oncrack / rust | 3.57x | 4.43x | 4.22x | 3.00x | **3.76x** |
| oncrack / c | 2.42x | 2.71x | 2.33x | 1.70x | **2.26x** |
| oncrack / fsharp | 7.79x | 6.12x | 7.59x | 5.84x | **6.78x** |
| oncrack / rails | 53.28x | 118.28x | 51.22x | 31.34x | **56.40x** |
| oncrack / oncrack-cached | 0.94x | 0.84x | 0.95x | 0.64x | **0.83x** |
| oncrack-cached / rust | 3.79x | 5.25x | 4.45x | 4.68x | **4.51x** |
| oncrack-cached / c | 2.58x | 3.21x | 2.46x | 2.65x | **2.71x** |
| oncrack-cached / fsharp | 8.28x | 7.26x | 7.99x | 9.11x | **8.13x** |
| c / rust | 1.47x | 1.63x | 1.81x | 1.77x | **1.67x** |

### Hand re-runs (review.py: 15 s warm-up, 10 s window, 16 clients, server CPU from the cgroup)

| App | phase | req/s per run | CPU us/request per run | median req/s | median CPU us/request |
|---|---|---|---|---:|---:|
| **onCrack, fresh authorization (default)** | room_show | 128,460, 165,256, 152,129, 40,624, 118,961, 159,997, 113,456 | 25.7, 19.3, 21.5, 48.4, 27.0, 20.2, 24.9 | 128,460 | 24.9 |
| **onCrack, fresh authorization (default)** | mixed | 107,464, 139,234, 152,843, 40,311, 19,056, 159,676, 161,662 | 29.4, 24.0, 21.4, 51.7, 90.6, 20.1, 19.7 | 139,234 | 24.0 |
| **onCrack, fresh authorization (default)** | post_message | 2,321, 15,403, 12,880, 14,317, 1,838, 15,395, 9,437 | 1011.7, 194.9, 240.7, 211.3, 1227.3, 194.5, 287.1 | 12,880 | 240.7 |
| onCrack, cached decision (opt-in) | room_show | 72,695, 172,174, 137,703, 65,424, 54,570, 131,435, 153,775 | 31.8, 18.1, 24.3, 32.5, 37.2, 23.6, 19.2 | 131,435 | 24.3 |
| onCrack, cached decision (opt-in) | mixed | 11,030, 153,401, 137,187, 16,882, 22,350, 155,080, 169,290 | 150.0, 20.8, 24.3, 104.6, 60.8, 21.3, 18.6 | 137,187 | 24.3 |
| onCrack, cached decision (opt-in) | post_message | 2,914, 15,489, 7,516, 2,564, 4,347, 13,712, 9,485 | 769.5, 191.6, 388.2, 902.8, 577.8, 217.2, 312.1 | 7,516 | 388.2 |
| Rust f9dca47 | room_show | 7,986, 38,480, 6,478, 31,431, 8,479, 38,514, 36,411 | 235.6, 74.7, 278.4, 94.5, 232.3, 75.6, 81.7 | 31,431 | 94.5 |
| Rust f9dca47 | mixed | 13,107, 7,164, 27,196, 20,703, 42,526, 35,544, 39,528 | 187.2, 303.5, 114.5, 139.8, 69.0, 83.2, 74.6 | 27,196 | 114.5 |
| Rust f9dca47 | post_message | 1,824, 5,250, 3,385, 1,796, 3,840, 5,252, 5,940 | 1319.3, 524.7, 875.2, 1330.4, 755.2, 542.4, 489.0 | 3,840 | 755.2 |
| C cd0cbe4 | room_show | 27,244, 33,217, 45,434, 62,584, 25,148, 60,990, 66,297 | 94.3, 76.4, 73.0, 49.7, 84.4, 54.1, 49.0 | 45,434 | 73.0 |
| C cd0cbe4 | mixed | 46,493, 70,191, 39,320, 57,531, 3,478, 67,025, 53,779 | 67.9, 46.6, 84.4, 56.0, 787.8, 49.5, 61.6 | 53,779 | 61.6 |
| C cd0cbe4 | post_message | 1,134, 4,084, 3,217, 4,589, 2,407, 5,344, 5,341 | 2261.0, 798.6, 1045.1, 711.4, 1268.8, 625.4, 630.7 | 4,084 | 798.6 |

| CPU per request, median over runs | room page | mixed reads | post |
|---|---:|---:|---:|
| rust / oncrack | 3.79x | 4.78x | 3.14x |
| c / oncrack | 2.93x | 2.57x | 3.32x |
| rust / oncrack-cached | 3.89x | 4.72x | 1.95x |
| c / oncrack-cached | 3.01x | 2.54x | 2.06x |
| oncrack / oncrack-cached | 1.03x | 0.99x | 0.62x |
