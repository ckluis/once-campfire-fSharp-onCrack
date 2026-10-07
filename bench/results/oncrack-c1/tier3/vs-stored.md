onCrack in bench/results/oncrack-c1/tier3 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 102,722 [101,975-102,898] | 40,422 | **2.541x** | 28,623 | **3.589x** | 32.4 [32-33] | 93.6 | 122.4 |
| room page | 1 | 12,004 [11,776-12,058] | 7,617 | **1.576x** | 6,481 | **1.852x** | 151.1 [150-152] | 208.7 | 142.1 |
| messages page | 16 | 101,682 [94,641-106,328] | 37,836 | **2.687x** | 30,063 | **3.382x** | 29.8 [30-31] | 102.2 | 114.2 |
| messages page | 1 | 12,032 [11,812-12,249] | 8,312 | **1.448x** | 6,822 | **1.764x** | 153.6 [151-154] | 199.3 | 139.2 |
| sidebar | 16 | 112,827 [106,386-117,590] | 37,555 | **3.004x** | 28,238 | **3.996x** | 26.6 [26-27] | 101.8 | 123.2 |
| sidebar | 1 | 13,600 [13,459-13,666] | 8,000 | **1.700x** | 6,196 | **2.195x** | 137.7 [137-139] | 181.0 | 149.0 |
| search | 16 | 72,311 [71,202-73,672] | 34,070 | **2.122x** | 26,606 | **2.718x** | 31.1 [31-32] | 107.3 | 123.9 |
| search | 1 | 12,885 [12,798-12,929] | 6,055 | **2.128x** | 5,646 | **2.282x** | 144.7 [144-146] | 315.1 | 158.3 |
| post a message | 16 | 8,631 [8,284-8,761] | 8,905 | **0.969x** | 7,174 | **1.203x** | 357.3 [353-363] | 353.0 | 385.6 |
| post a message | 1 | 3,026 [2,994-3,042] | 3,052 | **0.991x** | 2,779 | **1.089x** | 635.3 [631-639] | 629.1 | 403.7 |

Checks:
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note messages_page c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
