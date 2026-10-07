onCrack in bench/results/oncrack-c2/t2-window200 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 10,946 | 8,905 | **1.229x** | 7,174 | **1.526x** | 251.3 | 353.0 | 385.6 |
| post a message | 1 | 1,870 | 3,052 | **0.613x** | 2,779 | **0.673x** | 839.4 | 629.1 | 403.7 |

Checks:
  responses: every one 2xx with 0 connection errors in 3 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
