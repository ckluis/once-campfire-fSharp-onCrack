onCrack in bench/results/oncrack-r2-post/t2-before-a against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 13,176 | 8,905 | **1.480x** | 7,174 | **1.837x** | 232.1 | 353.0 | 385.6 |
| post a message | 1 | 3,281 | 3,052 | **1.075x** | 2,779 | **1.181x** | 597.1 | 629.1 | 403.7 |

Checks:
  responses: every one 2xx with 0 connection errors in 3 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
