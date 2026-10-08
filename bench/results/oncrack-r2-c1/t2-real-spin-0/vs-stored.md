
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,339 | 1,079 | 30 | 753 | 688 | **1.78x** | **1.95x** | 79.3 | 84.3 |
| mixed | 16 | reads | 42,072 | 43,283 | 219 | 24,232 | 18,597 | **1.74x** | **2.26x** | 79.3 | 84.3 |
| spread | 16 | reads | 88,632 | 28,547 | 589 | 29,902 | 25,655 | **2.96x** | **3.45x** | 39.6 | 134.1 |
| spread_mixed | 16 | posts | 675 | 337 | 6 | 393 | 319 | **1.72x** | **2.12x** | 319.0 | 284.3 |
| spread_mixed | 16 | reads | 11,411 | 13,229 | 265 | 13,584 | 13,155 | **0.84x** | **0.87x** | 319.0 | 284.3 |
| search_spread | 16 | reads | 15,411 | 17,802 | 826 | 18,942 | 8,468 | **0.81x** | **1.82x** | 238.9 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
