
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,403 | 1,079 | 30 | 753 | 688 | **1.86x** | **2.04x** | 103.8 | 84.3 |
| mixed | 16 | reads | 34,791 | 43,283 | 219 | 24,232 | 18,597 | **1.44x** | **1.87x** | 103.8 | 84.3 |
| spread | 16 | reads | 32,754 | 28,547 | 589 | 29,902 | 25,655 | **1.10x** | **1.28x** | 115.7 | 134.1 |
| spread_mixed | 16 | posts | 744 | 337 | 6 | 393 | 319 | **1.89x** | **2.33x** | 281.0 | 284.3 |
| spread_mixed | 16 | reads | 12,910 | 13,229 | 265 | 13,584 | 13,155 | **0.95x** | **0.98x** | 281.0 | 284.3 |
| search_spread | 16 | reads | 15,792 | 17,802 | 826 | 18,942 | 8,468 | **0.83x** | **1.86x** | 232.2 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
