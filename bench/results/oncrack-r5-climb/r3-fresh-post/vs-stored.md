onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-climb/r3-fresh-post against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 11,743 [10,566-12,895] | 8,905 | **1.319x** | 7,174 | **1.637x** | 184.9 [182-189] | 353.0 | 385.6 |
| post a message | 1 | 4,967 [4,958-4,996] | 3,052 | **1.628x** | 2,779 | **1.787x** | 258.1 [256-258] | 629.1 | 403.7 |

Checks:
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 6 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
