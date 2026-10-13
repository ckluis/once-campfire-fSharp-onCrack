onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-climb/r3-fresh-post2 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 8,808 [8,291-11,993] | 8,905 | **0.989x** | 7,174 | **1.228x** | 187.4 [186-207] | 353.0 | 385.6 |
| post a message | 1 | 3,362 [3,328-4,928] | 3,052 | **1.102x** | 2,779 | **1.210x** | 272.4 [261-302] | 629.1 | 403.7 |

Checks:
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 6 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
