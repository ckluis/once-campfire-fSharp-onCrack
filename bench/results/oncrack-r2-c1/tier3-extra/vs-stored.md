onCrack in bench/results/oncrack-r2-c1/tier3-extra against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 15,559 | 8,905 | **1.747x** | 7,174 | **2.169x** | 177.8 | 353.0 | 385.6 |
| post a message | 1 | 5,201 | 3,052 | **1.704x** | 2,779 | **1.872x** | 246.8 | 629.1 | 403.7 |

Checks:
  responses: every one 2xx with 0 connection errors in 12 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
