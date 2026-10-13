### Normal profile

Median requests/sec of 3 rounds (1 session x 3) [min-max], 16 clients. Sessions: normal-1

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| **onCrack, fresh authorization (default)** | 167,676 [149,435-168,503] | 168,596 [161,362-177,313] | 189,738 [154,308-190,346] | 183,124 [180,388-184,690] | 14,376 [13,628-15,129] |
| onCrack, cached decision (opt-in) | 166,155 [98,062-174,944] | 183,904 [159,042-184,866] | 192,825 [154,023-195,709] | 188,545 [170,109-189,907] | 14,493 [11,797-15,202] |
| Rust f9dca47 | 48,973 [32,882-49,549] | 43,331 [34,963-46,794] | 51,702 [41,726-54,988] | 54,885 [42,305-55,045] | 6,123 [5,434-6,390] |
| C cd0cbe4 | 76,094 [51,872-76,442] | 66,771 [40,567-76,923] | 78,122 [59,342-81,938] | 78,460 [53,526-79,099] | 5,677 [4,539-6,010] |
| F# port | 31,682 [30,831-35,941] | 36,494 [33,036-41,880] | 37,019 [30,249-37,668] | 33,453 [33,058-33,892] | 9,463 [9,265-9,487] |
| Rails 0aa339d | 4,579 [4,280-5,186] | 5,024 [4,854-5,145] | 5,444 [5,372-5,763] | 5,526 [5,512-5,579] | 395 [382-396] |

| Ratio of medians | Room page | Messages page | Sidebar | Search | Post a message | Geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 3.42x | 3.89x | 3.67x | 3.34x | 2.35x | **3.29x** |
| oncrack / c | 2.20x | 2.52x | 2.43x | 2.33x | 2.53x | **2.40x** |
| oncrack / fsharp | 5.29x | 4.62x | 5.13x | 5.47x | 1.52x | **4.01x** |
| oncrack / rails | 36.62x | 33.56x | 34.85x | 33.14x | 36.41x | **34.88x** |
| oncrack / oncrack-cached | 1.01x | 0.92x | 0.98x | 0.97x | 0.99x | **0.97x** |
| oncrack-cached / rust | 3.39x | 4.24x | 3.73x | 3.44x | 2.37x | **3.37x** |
| oncrack-cached / c | 2.18x | 2.75x | 2.47x | 2.40x | 2.55x | **2.47x** |
| oncrack-cached / fsharp | 5.24x | 5.04x | 5.21x | 5.64x | 1.53x | **4.12x** |
| c / rust | 1.55x | 1.54x | 1.51x | 1.43x | 0.93x | **1.37x** |

### Mixed profile (16 readers plus a writer at 10 posts/s)

Median requests/sec of 3 rounds (1 session x 3) [min-max], 16 clients. Sessions: mixed-1

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| **onCrack, fresh authorization (default)** | 155,206 [120,556-157,618] | 174,026 [150,959-176,784] | 165,376 [153,017-184,510] | 156,907 [138,786-176,144] |
| onCrack, cached decision (opt-in) | 126,505 [121,212-146,277] | 138,648 [133,712-153,175] | 159,767 [145,237-179,487] | 142,387 [137,888-179,551] |
| Rust f9dca47 | 47,020 [38,200-47,638] | 44,604 [31,778-44,733] | 54,504 [40,336-55,286] | 54,269 [46,985-54,356] |
| C cd0cbe4 | 69,822 [64,250-72,658] | 50,904 [49,905-73,446] | 53,045 [52,368-82,646] | 77,184 [50,680-79,814] |
| F# port | 32,351 [26,871-32,536] | 40,336 [32,664-40,337] | 36,968 [24,618-37,044] | 29,210 [25,102-33,873] |
| Rails 0aa339d | 2,214 [1,876-2,888] | 3,507 [2,970-3,617] | 4,311 [3,564-4,403] | 4,224 [3,486-4,236] |

| Ratio of medians | Room page | Messages page | Sidebar | Search | Geometric mean |
|---|---:|---:|---:|---:|---:|
| oncrack / rust | 3.30x | 3.90x | 3.03x | 2.89x | **3.26x** |
| oncrack / c | 2.22x | 3.42x | 3.12x | 2.03x | **2.63x** |
| oncrack / fsharp | 4.80x | 4.31x | 4.47x | 5.37x | **4.72x** |
| oncrack / rails | 70.09x | 49.63x | 38.36x | 37.15x | **47.18x** |
| oncrack / oncrack-cached | 1.23x | 1.26x | 1.04x | 1.10x | **1.15x** |
| oncrack-cached / rust | 2.69x | 3.11x | 2.93x | 2.62x | **2.83x** |
| oncrack-cached / c | 1.81x | 2.72x | 3.01x | 1.84x | **2.29x** |
| oncrack-cached / fsharp | 3.91x | 3.44x | 4.32x | 4.87x | **4.10x** |
| c / rust | 1.48x | 1.14x | 0.97x | 1.42x | **1.24x** |

### Hand re-runs (review.py: 15 s warm-up, 10 s window, 16 clients, server CPU from the cgroup)

| App | phase | req/s per run | CPU us/request per run | median req/s | median CPU us/request |
|---|---|---|---|---:|---:|
| **onCrack, fresh authorization (default)** | room_show | 164,526, 114,532, 98,837, 134,034 | 19.4, 25.4, 27.4, 24.1 | 124,283 | 24.8 |
| **onCrack, fresh authorization (default)** | mixed | 131,842, 85,784, 130,195, 148,794 | 25.8, 30.8, 23.2, 23.2 | 131,019 | 24.5 |
| **onCrack, fresh authorization (default)** | post_message | 10,547, 7,798, 6,820, 12,979 | 290.9, 359.4, 401.4, 234.5 | 9,173 | 325.1 |
| onCrack, cached decision (opt-in) | room_show | 163,943, 124,387, 101,789, 134,831 | 19.4, 22.6, 26.9, 23.5 | 129,609 | 23.0 |
| onCrack, cached decision (opt-in) | mixed | 162,679, 127,425, 134,292, 124,034 | 19.5, 22.1, 23.5, 24.1 | 130,858 | 22.8 |
| onCrack, cached decision (opt-in) | post_message | 13,634, 15,370, 7,199, 8,320 | 217.6, 192.1, 397.9, 349.0 | 10,977 | 283.3 |
| Rust f9dca47 | room_show | 47,882, 33,308, 32,584, 36,159 | 60.3, 80.0, 92.6, 81.2 | 34,734 | 80.6 |
| Rust f9dca47 | mixed | 40,518, 32,730, 30,776, 46,156 | 71.5, 81.9, 95.5, 63.2 | 36,624 | 76.7 |
| Rust f9dca47 | post_message | 4,655, 4,389, 3,800, 5,388 | 609.9, 607.8, 778.2, 539.3 | 4,522 | 608.8 |
| C cd0cbe4 | room_show | 61,845, 64,015, 62,572, 60,099 | 48.2, 48.7, 51.5, 54.0 | 62,208 | 50.1 |
| C cd0cbe4 | mixed | 58,638, 71,074, 64,139, 18,217 | 53.3, 45.4, 49.8, 154.0 | 61,389 | 51.6 |
| C cd0cbe4 | post_message | 4,382, 4,590, 5,187, 4,507 | 719.2, 695.7, 641.3, 735.3 | 4,548 | 707.4 |

| CPU per request, median over runs | room page | mixed reads | post |
|---|---:|---:|---:|
| rust / oncrack | 3.25x | 3.13x | 1.87x |
| c / oncrack | 2.02x | 2.11x | 2.18x |
| rust / oncrack-cached | 3.50x | 3.36x | 2.15x |
| c / oncrack-cached | 2.18x | 2.26x | 2.50x |
| oncrack / oncrack-cached | 1.08x | 1.07x | 1.15x |
