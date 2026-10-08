onCrack in bench/results/oncrack-r2-post/t2-gated against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 14,493 | 8,905 | **1.628x** | 7,174 | **2.020x** | 217.7 | 353.0 | 385.6 |
| post a message | 1 | 4,313 | 3,052 | **1.413x** | 2,779 | **1.552x** | 436.9 | 629.1 | 403.7 |

Checks:
  note post_message c=16: warm-up did not settle (fixed)
  note post_message c=64: warm-up did not settle (fixed)
  responses: every one 2xx with 0 connection errors in 3 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
