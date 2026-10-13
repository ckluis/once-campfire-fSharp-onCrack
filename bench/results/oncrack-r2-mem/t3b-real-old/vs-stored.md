
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,373 [1,363-1,383] | 1,079 | 30 | 753 | 688 | **1.82x** | **2.00x** | 78.2 | 84.3 |
| mixed | 16 | reads | 43,050 [42,384-43,717] | 43,283 | 219 | 24,232 | 18,597 | **1.78x** | **2.31x** | 78.2 | 84.3 |
| spread | 16 | reads | 88,512 [88,433-88,592] | 28,547 | 589 | 29,902 | 25,655 | **2.96x** | **3.45x** | 38.8 | 134.1 |
| spread_mixed | 16 | posts | 644 [611-678] | 337 | 6 | 393 | 319 | **1.64x** | **2.02x** | 334.2 | 284.3 |
| spread_mixed | 16 | reads | 10,914 [10,412-11,416] | 13,229 | 265 | 13,584 | 13,155 | **0.80x** | **0.83x** | 334.2 | 284.3 |
| search_spread | 16 | reads | 16,968 [16,831-17,104] | 17,802 | 826 | 18,942 | 8,468 | **0.90x** | **2.00x** | 216.6 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 8 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
