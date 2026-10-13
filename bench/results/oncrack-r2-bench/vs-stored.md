
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,079 [1,069-1,093] | 1,079 | 30 | 753 | 688 | **1.43x** | **1.57x** | 84.3 | 84.3 |
| mixed | 16 | reads | 43,283 [40,760-43,423] | 43,283 | 219 | 24,232 | 18,597 | **1.79x** | **2.33x** | 84.3 | 84.3 |
| spread | 16 | reads | 28,547 [28,524-28,808] | 28,547 | 589 | 29,902 | 25,655 | **0.95x** | **1.11x** | 134.1 | 134.1 |
| spread_mixed | 16 | posts | 337 [331-338] | 337 | 6 | 393 | 319 | **0.86x** | **1.06x** | 284.3 | 284.3 |
| spread_mixed | 16 | reads | 13,229 [13,054-13,253] | 13,229 | 265 | 13,584 | 13,155 | **0.97x** | **1.01x** | 284.3 | 284.3 |
| search_spread | 16 | reads | 17,802 [17,388-17,808] | 17,802 | 826 | 18,942 | 8,468 | **0.94x** | **2.10x** | 203.8 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 12 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
