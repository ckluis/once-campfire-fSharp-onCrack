onCrack in bench/results/oncrack-c1/t2-cache-off against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 39,379 | 40,422 | **0.974x** | 28,623 | **1.376x** | 90.6 | 93.6 | 122.4 |
| messages page | 16 | 42,134 | 37,836 | **1.114x** | 30,063 | **1.402x** | 84.8 | 102.2 | 114.2 |
| sidebar | 16 | 38,162 | 37,555 | **1.016x** | 28,238 | **1.351x** | 94.6 | 101.8 | 123.2 |
| search | 16 | 33,729 | 34,070 | **0.990x** | 26,606 | **1.268x** | 108.3 | 107.3 | 123.9 |
| post a message | 16 | 8,626 | 8,905 | **0.969x** | 7,174 | **1.202x** | 364.0 | 353.0 | 385.6 |

Checks:
  responses: every one 2xx with 0 connection errors in 5 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
