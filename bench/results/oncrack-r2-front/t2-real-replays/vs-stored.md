
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,380 | 1,079 | 30 | 753 | 688 | **1.83x** | **2.01x** | 77.6 | 84.3 |
| mixed | 16 | reads | 45,807 | 43,283 | 219 | 24,232 | 18,597 | **1.89x** | **2.46x** | 77.6 | 84.3 |
| spread | 16 | reads | 94,497 | 28,547 | 589 | 29,902 | 25,655 | **3.16x** | **3.68x** | 38.2 | 134.1 |
| spread_mixed | 16 | posts | 671 | 337 | 6 | 393 | 319 | **1.71x** | **2.10x** | 323.7 | 284.3 |
| spread_mixed | 16 | reads | 11,291 | 13,229 | 265 | 13,584 | 13,155 | **0.83x** | **0.86x** | 323.7 | 284.3 |
| search_spread | 16 | reads | 16,732 | 17,802 | 826 | 18,942 | 8,468 | **0.88x** | **1.98x** | 222.8 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
