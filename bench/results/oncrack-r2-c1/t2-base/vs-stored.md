onCrack in bench/results/oncrack-r2-c1/t2-base against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 1 | 26,402 | 7,617 | **3.466x** | 6,481 | **4.074x** | 18.7 | 208.7 | 142.1 |
| post a message | 1 | 4,741 | 3,052 | **1.554x** | 2,779 | **1.706x** | 393.1 | 629.1 | 403.7 |

Checks:
  responses: every one 2xx with 0 connection errors in 5 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
