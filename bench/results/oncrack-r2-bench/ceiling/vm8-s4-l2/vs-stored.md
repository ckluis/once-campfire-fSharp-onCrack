onCrack in bench/results/oncrack-r2-bench/ceiling/vm8-s4-l2 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 100,211 | 40,422 | **2.479x** | 28,623 | **3.501x** | 38.1 | 93.6 | 122.4 |
| sidebar | 16 | 115,700 | 37,555 | **3.081x** | 28,238 | **4.097x** | 32.6 | 101.8 | 123.2 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
