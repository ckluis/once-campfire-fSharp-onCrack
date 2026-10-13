
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,084 | 1,079 | 30 | 753 | 688 | **1.44x** | **1.58x** | 84.1 | 84.3 |
| mixed | 16 | reads | 43,473 | 43,283 | 219 | 24,232 | 18,597 | **1.79x** | **2.34x** | 84.1 | 84.3 |
| spread_mixed | 16 | posts | 343 | 337 | 6 | 393 | 319 | **0.87x** | **1.08x** | 279.9 | 284.3 |
| spread_mixed | 16 | reads | 13,395 | 13,229 | 265 | 13,584 | 13,155 | **0.99x** | **1.02x** | 279.9 | 284.3 |

Checks:
  responses: every one 2xx with 0 connection errors in 2 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
