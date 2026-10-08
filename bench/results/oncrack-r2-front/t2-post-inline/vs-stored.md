onCrack in bench/results/oncrack-r2-front/t2-post-inline against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 9,898 | 8,905 | **1.112x** | 7,174 | **1.380x** | 190.2 | 353.0 | 385.6 |
| post a message | 1 | 4,970 | 3,052 | **1.629x** | 2,779 | **1.788x** | 344.0 | 629.1 | 403.7 |

Checks:
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 3 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
