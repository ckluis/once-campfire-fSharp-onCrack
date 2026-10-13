onCrack in bench/results/oncrack-r2-bench/controls/cache-off against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|

Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 772 | 1,069 | 30 | 753 | 688 | **1.03x** | **1.12x** | 148.1 | 87.9 |
| mixed | 16 | reads | 24,364 | 40,760 | 219 | 24,232 | 18,597 | **1.01x** | **1.31x** | 148.1 | 87.9 |
| spread | 16 | reads | 29,916 | 28,524 | 589 | 29,740 | 25,558 | **1.01x** | **1.17x** | 125.2 | 134.3 |
| spread_mixed | 16 | posts | 350 | 331 | 6 | 396 | 319 | **0.88x** | **1.10x** | 275.2 | 287.2 |
| spread_mixed | 16 | reads | 13,543 | 13,054 | 265 | 13,584 | 12,931 | **1.00x** | **1.05x** | 275.2 | 287.2 |
| search_spread | 16 | reads | 19,182 | 17,808 | 826 | 18,868 | 8,989 | **1.02x** | **2.13x** | 185.0 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
