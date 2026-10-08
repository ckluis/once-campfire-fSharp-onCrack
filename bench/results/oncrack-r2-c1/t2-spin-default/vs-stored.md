onCrack in bench/results/oncrack-r2-c1/t2-spin-default against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 14,922 | 8,905 | **1.676x** | 7,174 | **2.080x** | 184.3 | 353.0 | 385.6 |

Checks:
  note post_message c=16: warm-up did not settle (fixed)
  responses: every one 2xx with 0 connection errors in 2 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
