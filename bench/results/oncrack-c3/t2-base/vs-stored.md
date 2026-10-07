onCrack in bench/results/oncrack-c3/t2-base against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| search | 16 | 72,128 | 34,070 | **2.117x** | 26,606 | **2.711x** | 31.3 | 107.3 | 123.9 |
| search | 1 | 12,873 | 6,055 | **2.126x** | 5,646 | **2.280x** | 146.7 | 315.1 | 158.3 |

Checks:
  responses: every one 2xx with 0 connection errors in 2 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
