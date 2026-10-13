## normal-1 (read-and-post-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| Rails 0aa339d | 4,579 [4,280-5,186] | 5,024 [4,854-5,145] | 5,444 [5,372-5,763] | 5,526 [5,512-5,579] | 395 [382-396] |
| Rust f9dca47 | 48,973 [32,882-49,549] | 43,331 [34,963-46,794] | 51,702 [41,726-54,988] | 54,885 [42,305-55,045] | 6,123 [5,434-6,390] |
| C cd0cbe4 | 76,094 [51,872-76,442] | 66,771 [40,567-76,923] | 78,122 [59,342-81,938] | 78,460 [53,526-79,099] | 5,677 [4,539-6,010] |
| F# port | 31,682 [30,831-35,941] | 36,494 [33,036-41,880] | 37,019 [30,249-37,668] | 33,453 [33,058-33,892] | 9,463 [9,265-9,487] |
| onCrack (fresh authorization, default) | 167,676 [149,435-168,503] | 168,596 [161,362-177,313] | 189,738 [154,308-190,346] | 183,124 [180,388-184,690] | 14,376 [13,628-15,129] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 166,155 [98,062-174,944] | 183,904 [159,042-184,866] | 192,825 [154,023-195,709] | 188,545 [170,109-189,907] | 14,493 [11,797-15,202] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| Rails 0aa339d | 507,753 | 10,913 | - | - | 28.6 | 3.255 / 9.215 |
| Rust f9dca47 | 4,601,172 | 176,430 | - | - | 97.4 | 0.300 / 0.742 |
| C cd0cbe4 | 6,687,372 | 160,468 | - | - | 139.4 | 0.200 / 0.425 |
| F# port | 3,547,764 | 261,596 | - | - | 144.7 | 0.438 / 1.355 |
| onCrack (fresh authorization, default) | 16,950,338 | 386,104 | - | - | 249.6 | 0.085 / 0.219 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 16,798,180 | 370,579 | - | - | 259.4 | 0.087 / 0.240 |
| all | 49,092,579 | 1,366,090 | 0 | | 259.4 | |

| ratio (medians) | Room page | Messages page | Sidebar | Search | Post a message | geometric mean |
|---|---:|---:|---:|---:|---:|---:|
| oncrack / rust | 3.42x | 3.89x | 3.67x | 3.34x | 2.35x | **3.29x** |
| oncrack / c | 2.20x | 2.52x | 2.43x | 2.33x | 2.53x | **2.40x** |
| oncrack / fsharp | 5.29x | 4.62x | 5.13x | 5.47x | 1.52x | **4.01x** |
| oncrack / oncrack-cached | 1.01x | 0.92x | 0.98x | 0.97x | 0.99x | **0.97x** |
| oncrack-cached / rust | 3.39x | 4.24x | 3.73x | 3.44x | 2.37x | **3.37x** |
| oncrack-cached / c | 2.18x | 2.75x | 2.47x | 2.40x | 2.55x | **2.47x** |
| oncrack-cached / fsharp | 5.24x | 5.04x | 5.21x | 5.64x | 1.53x | **4.12x** |

| Implementation | Image id | Image label (revision) | Source HEAD (dirty?) |
|---|---|---|---|
| Rails 0aa339d | `sha256:a9a31e4b152d` | `-` | `0aa339d81e05` (clean) |
| Rust f9dca47 | `sha256:b0e047159ee2` | `-` | `f9dca47e592f` (clean) |
| C cd0cbe4 | `sha256:51001f452cc5` | `-` | `cd0cbe4b24bc` (clean) |
| F# port | `sha256:cccad24be9a1` | `` | `9954ad0b01e3` (clean) |
| onCrack (fresh authorization, default) | `sha256:ecfb867a2f57` | `ea1f85b4b66e` | `993ddcee3259` (clean) |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | `sha256:ecfb867a2f57` | `ea1f85b4b66e` | `993ddcee3259` (clean) |

Harness `a05b344`; seed sha256 `f1dc1b9ad63a`; load generator sha256 `351a66af1ea1`; profile `read-and-post-v1`; started 2026-10-10T21:53:52Z.


180 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

## mixed-1 (mixed-read-write-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| Rails 0aa339d | 2,214 [1,876-2,888] | 3,507 [2,970-3,617] | 4,311 [3,564-4,403] | 4,224 [3,486-4,236] |
| Rust f9dca47 | 47,020 [38,200-47,638] | 44,604 [31,778-44,733] | 54,504 [40,336-55,286] | 54,269 [46,985-54,356] |
| C cd0cbe4 | 69,822 [64,250-72,658] | 50,904 [49,905-73,446] | 53,045 [52,368-82,646] | 77,184 [50,680-79,814] |
| F# port | 32,351 [26,871-32,536] | 40,336 [32,664-40,337] | 36,968 [24,618-37,044] | 29,210 [25,102-33,873] |
| onCrack (fresh authorization, default) | 155,206 [120,556-157,618] | 174,026 [150,959-176,784] | 165,376 [153,017-184,510] | 156,907 [138,786-176,144] |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 126,505 [121,212-146,277] | 138,648 [133,712-153,175] | 159,767 [145,237-179,487] | 142,387 [137,888-179,551] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| Rails 0aa339d | 331,564 | 1,196 | 958 | 9.8-10.0 | 24.1 | 4.139 / 67.903 |
| Rust f9dca47 | 4,478,011 | 1,200 | 960 | 10.0-10.0 | 94.5 | 0.299 / 0.800 |
| C cd0cbe4 | 6,214,366 | 1,198 | 958 | 9.9-10.0 | 132.9 | 0.204 / 0.529 |
| F# port | 3,135,597 | 1,200 | 960 | 10.0-10.0 | 139.8 | 0.440 / 1.251 |
| onCrack (fresh authorization, default) | 15,280,856 | 1,200 | 960 | 10.0-10.0 | 244.8 | 0.087 / 0.289 |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | 14,111,937 | 1,200 | 960 | 10.0-10.0 | 236.6 | 0.099 / 0.739 |
| all | 43,552,331 | 7,194 | 5,756 | | 244.8 | |

| ratio (medians) | Room page | Messages page | Sidebar | Search | geometric mean |
|---|---:|---:|---:|---:|---:|
| oncrack / rust | 3.30x | 3.90x | 3.03x | 2.89x | **3.26x** |
| oncrack / c | 2.22x | 3.42x | 3.12x | 2.03x | **2.63x** |
| oncrack / fsharp | 4.80x | 4.31x | 4.47x | 5.37x | **4.72x** |
| oncrack / oncrack-cached | 1.23x | 1.26x | 1.04x | 1.10x | **1.15x** |
| oncrack-cached / rust | 2.69x | 3.11x | 2.93x | 2.62x | **2.83x** |
| oncrack-cached / c | 1.81x | 2.72x | 3.01x | 1.84x | **2.29x** |
| oncrack-cached / fsharp | 3.91x | 3.44x | 4.32x | 4.87x | **4.10x** |

| Implementation | Image id | Image label (revision) | Source HEAD (dirty?) |
|---|---|---|---|
| Rails 0aa339d | `sha256:a9a31e4b152d` | `-` | `0aa339d81e05` (clean) |
| Rust f9dca47 | `sha256:b0e047159ee2` | `-` | `f9dca47e592f` (clean) |
| C cd0cbe4 | `sha256:51001f452cc5` | `-` | `cd0cbe4b24bc` (clean) |
| F# port | `sha256:cccad24be9a1` | `` | `9954ad0b01e3` (clean) |
| onCrack (fresh authorization, default) | `sha256:ecfb867a2f57` | `ea1f85b4b66e` | `993ddcee3259` (clean) |
| onCrack, cached decision (CAMPFIRE_FRESH_AUTH=0) | `sha256:ecfb867a2f57` | `ea1f85b4b66e` | `993ddcee3259` (clean) |

Harness `a05b344`; seed sha256 `f1dc1b9ad63a`; load generator sha256 `351a66af1ea1`; profile `mixed-read-write-v1`; started 2026-10-10T22:11:47Z.


144 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

