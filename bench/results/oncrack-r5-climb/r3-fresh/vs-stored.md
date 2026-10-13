onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-climb/r3-fresh against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 147,899 [141,822-149,480] | 40,422 | **3.659x** | 28,623 | **5.167x** | 21.2 [21-22] | 93.6 | 122.4 |
| room page | 1 | 23,707 [23,216-24,015] | 7,617 | **3.112x** | 6,481 | **3.658x** | 22.2 [22-23] | 208.7 | 142.1 |
| messages page | 16 | 154,724 [141,102-157,464] | 37,836 | **4.089x** | 30,063 | **5.147x** | 20.0 [20-23] | 102.2 | 114.2 |
| messages page | 1 | 24,114 [21,633-25,226] | 8,312 | **2.901x** | 6,822 | **3.535x** | 22.1 [21-24] | 199.3 | 139.2 |
| sidebar | 16 | 166,078 [159,651-167,657] | 37,555 | **4.422x** | 28,238 | **5.881x** | 18.2 [18-19] | 101.8 | 123.2 |
| sidebar | 1 | 24,920 [23,664-25,078] | 8,000 | **3.115x** | 6,196 | **4.022x** | 20.6 [20-22] | 181.0 | 149.0 |
| search | 16 | 161,081 [146,114-162,264] | 34,070 | **4.728x** | 26,606 | **6.054x** | 18.8 [18-23] | 107.3 | 123.9 |
| search | 1 | 24,664 [21,595-24,955] | 6,055 | **4.073x** | 5,646 | **4.368x** | 21.1 [21-24] | 315.1 | 158.3 |
| post a message | 16 | 11,463 [11,184-12,202] | 8,905 | **1.287x** | 7,174 | **1.598x** | 188.4 [186-189] | 353.0 | 385.6 |
| post a message | 1 | 3,645 [3,469-4,976] | 3,052 | **1.194x** | 2,779 | **1.312x** | 259.5 [257-282] | 629.1 | 403.7 |

Checks:
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note messages_page c=1: host probe 1.11 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note search c=1: warm-up did not settle (reached the maximum)
  note search c=1: host probe 1.11 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
