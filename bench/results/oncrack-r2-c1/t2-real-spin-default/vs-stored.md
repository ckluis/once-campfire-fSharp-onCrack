
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,159 | 1,079 | 30 | 753 | 688 | **1.54x** | **1.68x** | 86.0 | 84.3 |
| mixed | 16 | reads | 41,250 | 43,283 | 219 | 24,232 | 18,597 | **1.70x** | **2.22x** | 86.0 | 84.3 |
| spread | 16 | reads | 91,663 | 28,547 | 589 | 29,902 | 25,655 | **3.07x** | **3.57x** | 38.7 | 134.1 |
| spread_mixed | 16 | posts | 664 | 337 | 6 | 393 | 319 | **1.69x** | **2.08x** | 326.0 | 284.3 |
| spread_mixed | 16 | reads | 11,136 | 13,229 | 265 | 13,584 | 13,155 | **0.82x** | **0.85x** | 326.0 | 284.3 |
| search_spread | 16 | reads | 14,017 | 17,802 | 826 | 18,942 | 8,468 | **0.74x** | **1.66x** | 270.3 | 203.8 |

Checks:
  note mixed c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
