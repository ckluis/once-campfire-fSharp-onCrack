onCrack in bench/results/oncrack-r2-bench/controls/cache-512mb against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|

Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| spread | 16 | reads | 127,399 | 28,524 | 589 | 29,740 | 25,558 | **4.28x** | **4.98x** | 28.7 | 134.3 |
| search_spread | 16 | reads | 25,340 | 17,808 | 826 | 18,868 | 8,989 | **1.34x** | **2.82x** | 148.4 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 2 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
