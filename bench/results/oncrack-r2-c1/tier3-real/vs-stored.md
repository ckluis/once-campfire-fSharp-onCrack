
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,377 [1,360-1,387] | 1,079 | 30 | 753 | 688 | **1.83x** | **2.00x** | 77.4 | 84.3 |
| mixed | 16 | reads | 43,029 [42,834-43,167] | 43,283 | 219 | 24,232 | 18,597 | **1.78x** | **2.31x** | 77.4 | 84.3 |
| spread | 16 | reads | 87,243 [85,057-89,165] | 28,547 | 589 | 29,902 | 25,655 | **2.92x** | **3.40x** | 39.0 | 134.1 |
| spread_mixed | 16 | posts | 683 [670-697] | 337 | 6 | 393 | 319 | **1.74x** | **2.14x** | 320.7 | 284.3 |
| spread_mixed | 16 | reads | 11,317 [11,061-11,590] | 13,229 | 265 | 13,584 | 13,155 | **0.83x** | **0.86x** | 320.7 | 284.3 |
| search_spread | 16 | reads | 16,695 [15,744-17,104] | 17,802 | 826 | 18,942 | 8,468 | **0.88x** | **1.97x** | 220.4 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 12 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
