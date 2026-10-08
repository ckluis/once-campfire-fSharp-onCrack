
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,381 | 1,079 | 30 | 753 | 688 | **1.83x** | **2.01x** | 77.6 | 84.3 |
| mixed | 16 | reads | 44,371 | 43,283 | 219 | 24,232 | 18,597 | **1.83x** | **2.39x** | 77.6 | 84.3 |

Checks:
  responses: every one 2xx with 0 connection errors in 1 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
