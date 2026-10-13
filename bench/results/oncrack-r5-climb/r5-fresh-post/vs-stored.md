onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-climb/r5-fresh-post against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 5,268 [1,759-8,179] | 8,905 | **0.592x** | 7,174 | **0.734x** | 519.3 [252-1,276] | 353.0 | 385.6 |
| post a message | 1 | 2,544 [1,585-3,395] | 3,052 | **0.834x** | 2,779 | **0.916x** | 405.5 [271-774] | 629.1 | 403.7 |

Checks:
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: host probe 1.223 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: host probe 1.72 after the window (noisy host)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: host probe 1.548 after the window (noisy host)
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 6 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
