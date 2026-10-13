onCrack in bench/results/oncrack-r2-c1/t2-solo1 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 1 | 26,070 | 7,617 | **3.423x** | 6,481 | **4.023x** | 19.1 | 208.7 | 142.1 |
| search | 1 | 27,573 | 6,055 | **4.554x** | 5,646 | **4.884x** | 17.4 | 315.1 | 158.3 |
| post a message | 1 | 4,925 | 3,052 | **1.614x** | 2,779 | **1.772x** | 346.0 | 629.1 | 403.7 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
