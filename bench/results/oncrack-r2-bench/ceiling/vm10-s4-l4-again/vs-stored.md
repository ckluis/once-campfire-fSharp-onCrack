onCrack in bench/results/oncrack-r2-bench/ceiling/vm10-s4-l4-again against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 135,454 | 40,422 | **3.351x** | 28,623 | **4.732x** | 27.3 | 93.6 | 122.4 |
| sidebar | 16 | 152,398 | 37,555 | **4.058x** | 28,238 | **5.397x** | 23.9 | 101.8 | 123.2 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
