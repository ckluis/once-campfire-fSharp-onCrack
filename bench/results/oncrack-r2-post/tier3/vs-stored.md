onCrack in bench/results/oncrack-r2-post/tier3 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 12,010 [10,030-12,163] | 8,905 | **1.349x** | 7,174 | **1.674x** | 185.2 [184-186] | 353.0 | 385.6 |
| post a message | 1 | 4,626 [4,565-4,684] | 3,052 | **1.516x** | 2,779 | **1.664x** | 390.8 [388-398] | 629.1 | 403.7 |

Checks:
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 9 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
