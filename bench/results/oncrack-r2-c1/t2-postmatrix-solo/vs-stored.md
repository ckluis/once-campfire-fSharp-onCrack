onCrack in bench/results/oncrack-r2-c1/t2-postmatrix-solo against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 15,373 | 8,905 | **1.726x** | 7,174 | **2.143x** | 185.8 | 353.0 | 385.6 |
| post a message | 1 | 5,082 | 3,052 | **1.665x** | 2,779 | **1.829x** | 345.2 | 629.1 | 403.7 |

Checks:
  note post_message c=2: warm-up did not settle (fixed)
  note post_message c=4: warm-up did not settle (fixed)
  responses: every one 2xx with 0 connection errors in 5 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
