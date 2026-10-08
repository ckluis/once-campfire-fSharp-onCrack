
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,073 | 1,079 | 30 | 753 | 688 | **1.43x** | **1.56x** | 86.3 | 84.3 |
| mixed | 16 | reads | 41,333 | 43,283 | 219 | 24,232 | 18,597 | **1.71x** | **2.22x** | 86.3 | 84.3 |
| spread | 16 | reads | 127,399 | 28,547 | 589 | 29,902 | 25,655 | **4.26x** | **4.97x** | 28.7 | 134.1 |
| spread_mixed | 16 | posts | 339 | 337 | 6 | 393 | 319 | **0.86x** | **1.06x** | 290.7 | 284.3 |
| spread_mixed | 16 | reads | 12,946 | 13,229 | 265 | 13,584 | 13,155 | **0.95x** | **0.98x** | 290.7 | 284.3 |
| search_spread | 16 | reads | 25,340 | 17,802 | 826 | 18,942 | 8,468 | **1.34x** | **2.99x** | 148.4 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
