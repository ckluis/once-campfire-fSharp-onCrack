
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,381 | 1,079 | 30 | 753 | 688 | **1.83x** | **2.01x** | 93.0 | 84.3 |
| mixed | 16 | reads | 37,232 | 43,283 | 219 | 24,232 | 18,597 | **1.54x** | **2.00x** | 93.0 | 84.3 |
| spread | 16 | reads | 86,130 | 28,547 | 589 | 29,902 | 25,655 | **2.88x** | **3.36x** | 42.0 | 134.1 |
| spread_mixed | 16 | posts | 745 | 337 | 6 | 393 | 319 | **1.89x** | **2.34x** | 283.5 | 284.3 |
| spread_mixed | 16 | reads | 12,793 | 13,229 | 265 | 13,584 | 13,155 | **0.94x** | **0.97x** | 283.5 | 284.3 |
| search_spread | 16 | reads | 16,138 | 17,802 | 826 | 18,942 | 8,468 | **0.85x** | **1.91x** | 224.3 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
