onCrack in bench/results/oncrack-r2-mem/t3b-classic-old against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 171,701 [167,684-175,719] | 40,422 | **4.248x** | 28,623 | **5.999x** | 18.0 [18-18] | 93.6 | 122.4 |
| messages page | 16 | 181,967 [180,785-183,149] | 37,836 | **4.809x** | 30,063 | **6.053x** | 16.6 [16-17] | 102.2 | 114.2 |
| sidebar | 16 | 196,183 [196,168-196,198] | 37,555 | **5.224x** | 28,238 | **6.948x** | 14.9 [15-15] | 101.8 | 123.2 |
| search | 16 | 191,411 [190,827-191,996] | 34,070 | **5.618x** | 26,606 | **7.194x** | 15.5 [16-16] | 107.3 | 123.9 |
| post a message | 16 | 12,968 [10,325-15,611] | 8,905 | **1.456x** | 7,174 | **1.808x** | 179.9 [180-180] | 353.0 | 385.6 |

Checks:
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 10 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
