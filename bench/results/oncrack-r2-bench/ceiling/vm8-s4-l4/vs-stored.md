onCrack in bench/results/oncrack-r2-bench/ceiling/vm8-s4-l4 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 122,914 | 40,422 | **3.041x** | 28,623 | **4.294x** | 30.2 | 93.6 | 122.4 |
| sidebar | 16 | 138,080 | 37,555 | **3.677x** | 28,238 | **4.890x** | 26.9 | 101.8 | 123.2 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
