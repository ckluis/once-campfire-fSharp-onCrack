onCrack in bench/results/oncrack-r2-post/tier3-reads against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 124,996 | 40,422 | **3.092x** | 28,623 | **4.367x** | 30.1 | 93.6 | 122.4 |
| sidebar | 16 | 137,768 | 37,555 | **3.668x** | 28,238 | **4.879x** | 26.8 | 101.8 | 123.2 |

Checks:
  responses: every one 2xx with 0 connection errors in 2 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
