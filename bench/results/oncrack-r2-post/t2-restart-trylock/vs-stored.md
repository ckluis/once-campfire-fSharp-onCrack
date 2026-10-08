onCrack in bench/results/oncrack-r2-post/t2-restart-trylock against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 13,749 | 8,905 | **1.544x** | 7,174 | **1.917x** | 180.7 | 353.0 | 385.6 |
| post a message | 1 | 4,774 | 3,052 | **1.564x** | 2,779 | **1.718x** | 378.6 | 629.1 | 403.7 |

Checks:
  responses: every one 2xx with 0 connection errors in 3 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
