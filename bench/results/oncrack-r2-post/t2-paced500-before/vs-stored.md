
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 500 | 1,079 | 30 | 753 | 688 | **0.66x** | **0.73x** | 42.9 | 84.3 |
| mixed | 16 | reads | 84,907 | 43,283 | 219 | 24,232 | 18,597 | **3.50x** | **4.57x** | 42.9 | 84.3 |

Checks:
  responses: every one 2xx with 0 connection errors in 1 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
