
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,424 [1,410-1,430] | 1,079 | 30 | 753 | 688 | **1.89x** | **2.07x** | 103.9 | 84.3 |
| mixed | 16 | reads | 34,805 [34,752-34,876] | 43,283 | 219 | 24,232 | 18,597 | **1.44x** | **1.87x** | 103.9 | 84.3 |
| spread_mixed | 16 | posts | 753 [743-758] | 337 | 6 | 393 | 319 | **1.91x** | **2.36x** | 279.5 | 284.3 |
| spread_mixed | 16 | reads | 13,129 [12,940-13,141] | 13,229 | 265 | 13,584 | 13,155 | **0.97x** | **1.00x** | 279.5 | 284.3 |

Checks:
  responses: every one 2xx with 0 connection errors in 6 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
