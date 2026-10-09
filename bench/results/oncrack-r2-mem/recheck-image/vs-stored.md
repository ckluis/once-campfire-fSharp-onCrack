
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,381 | 1,079 | 30 | 753 | 688 | **1.83x** | **2.01x** | 76.8 | 84.3 |
| mixed | 16 | reads | 44,523 | 43,283 | 219 | 24,232 | 18,597 | **1.84x** | **2.39x** | 76.8 | 84.3 |
| spread | 16 | reads | 191,038 | 28,547 | 589 | 29,902 | 25,655 | **6.39x** | **7.45x** | 16.2 | 134.1 |
| spread_mixed | 16 | posts | 672 | 337 | 6 | 393 | 319 | **1.71x** | **2.10x** | 324.7 | 284.3 |
| spread_mixed | 16 | reads | 11,274 | 13,229 | 265 | 13,584 | 13,155 | **0.83x** | **0.86x** | 324.7 | 284.3 |
| search_spread | 16 | reads | 17,352 | 17,802 | 826 | 18,942 | 8,468 | **0.92x** | **2.05x** | 212.0 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
