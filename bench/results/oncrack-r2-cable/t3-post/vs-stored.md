onCrack in bench/results/oncrack-r2-cable/t3-post against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 10,057 | 8,905 | **1.129x** | 7,174 | **1.402x** | 231.8 | 353.0 | 385.6 |
| post a message | 1 | 3,340 | 3,052 | **1.094x** | 2,779 | **1.202x** | 592.1 | 629.1 | 403.7 |

Checks:
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 2 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
