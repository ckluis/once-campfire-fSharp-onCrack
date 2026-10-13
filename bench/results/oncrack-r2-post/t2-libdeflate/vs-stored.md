onCrack in bench/results/oncrack-r2-post/t2-libdeflate against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 11,552 | 8,905 | **1.297x** | 7,174 | **1.610x** | 214.6 | 353.0 | 385.6 |
| post a message | 1 | 4,342 | 3,052 | **1.423x** | 2,779 | **1.563x** | 432.0 | 629.1 | 403.7 |

Checks:
  note post_message c=64: warm-up did not settle (fixed)
  responses: every one 2xx with 0 connection errors in 3 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
