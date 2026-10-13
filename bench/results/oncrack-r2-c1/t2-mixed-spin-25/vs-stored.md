
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,376 | 1,079 | 30 | 753 | 688 | **1.83x** | **2.00x** | 78.9 | 84.3 |
| mixed | 16 | reads | 43,875 | 43,283 | 219 | 24,232 | 18,597 | **1.81x** | **2.36x** | 78.9 | 84.3 |

Checks:
  note mixed c=16: warm-up did not settle (fixed)
  responses: every one 2xx with 0 connection errors in 1 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
