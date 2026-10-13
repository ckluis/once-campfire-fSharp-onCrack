Median requests/sec at 64 clients, 8 s per route, over the rounds that ran [rounds]; errors / invalid responses summed over them

| Implementation | Rounds | Room page | Messages page | Sidebar | Search | Errors / invalid |
|---|---:|---:|---:|---:|---:|---|
| Rails 0aa339d | 3 | 4,876 | 4,711 | 4,127 | 4,623 | 0 / 0 |
| Rust f9dca47 | 3 | 36,795 | 35,932 | 44,661 | 54,680 | 0 / 0 |
| C cd0cbe4 | 3 | 97,557 | 99,112 | 107,748 | 102,467 | 0 / 0 |
| onCrack before R4.5 | 3 | 165,545 | 220,230 | 216,686 | 207,246 | 0 / 0 |
| **onCrack, fresh (HEAD)** | 3 | 211,367 | 225,413 | 250,343 | 238,609 | 0 / 0 |
| onCrack, cached decision | 3 | 215,544 | 238,084 | 258,824 | 247,413 | 0 / 0 |

Median requests/sec at 256 clients, 8 s per route, over the rounds that ran [rounds]; errors / invalid responses summed over them

| Implementation | Rounds | Room page | Messages page | Sidebar | Search | Errors / invalid |
|---|---:|---:|---:|---:|---:|---|
| Rails 0aa339d | 3 | 5,087 | 4,498 | 4,928 | 5,269 | 0 / 0 |
| Rust f9dca47 | 3 | 35,985 | 35,420 | 56,294 | 48,064 | 0 / 0 |
| C cd0cbe4 | 3 | 89,202 | 96,323 | 109,829 | 104,824 | 0 / 195 |
| onCrack before R4.5 | 3 | 169,272 | 179,716 | 216,873 | 196,527 | 0 / 0 |
| **onCrack, fresh (HEAD)** | 3 | 196,107 | 218,411 | 257,084 | 242,023 | 0 / 0 |
| onCrack, cached decision | 3 | 199,882 | 233,804 | 269,079 | 247,644 | 0 / 0 |

