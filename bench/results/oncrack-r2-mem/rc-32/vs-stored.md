
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,363 | 1,079 | 30 | 753 | 688 | **1.81x** | **1.98x** | 77.1 | 84.3 |
| mixed | 16 | reads | 43,524 | 43,283 | 219 | 24,232 | 18,597 | **1.80x** | **2.34x** | 77.1 | 84.3 |
| spread | 16 | reads | 190,691 | 28,547 | 589 | 29,902 | 25,655 | **6.38x** | **7.43x** | 16.2 | 134.1 |
| spread_mixed | 16 | posts | 666 | 337 | 6 | 393 | 319 | **1.69x** | **2.09x** | 325.8 | 284.3 |
| spread_mixed | 16 | reads | 11,206 | 13,229 | 265 | 13,584 | 13,155 | **0.82x** | **0.85x** | 325.8 | 284.3 |
| search_spread | 16 | reads | 17,043 | 17,802 | 826 | 18,942 | 8,468 | **0.90x** | **2.01x** | 213.9 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
