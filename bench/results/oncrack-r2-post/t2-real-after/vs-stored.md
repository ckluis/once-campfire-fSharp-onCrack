
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,361 | 1,079 | 30 | 753 | 688 | **1.81x** | **1.98x** | 105.8 | 84.3 |
| mixed | 16 | reads | 34,174 | 43,283 | 219 | 24,232 | 18,597 | **1.41x** | **1.84x** | 105.8 | 84.3 |
| spread_mixed | 16 | posts | 733 | 337 | 6 | 393 | 319 | **1.86x** | **2.30x** | 287.6 | 284.3 |
| spread_mixed | 16 | reads | 12,767 | 13,229 | 265 | 13,584 | 13,155 | **0.94x** | **0.97x** | 287.6 | 284.3 |

Checks:
  responses: every one 2xx with 0 connection errors in 2 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
