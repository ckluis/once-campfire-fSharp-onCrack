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

