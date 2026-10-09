
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,355 | 1,079 | 30 | 753 | 688 | **1.80x** | **1.97x** | 79.7 | 84.3 |
| mixed | 16 | reads | 42,074 | 43,283 | 219 | 24,232 | 18,597 | **1.74x** | **2.26x** | 79.7 | 84.3 |
| spread | 16 | reads | 188,633 | 28,547 | 589 | 29,902 | 25,655 | **6.31x** | **7.35x** | 16.4 | 134.1 |
| spread_mixed | 16 | posts | 666 | 337 | 6 | 393 | 319 | **1.69x** | **2.09x** | 329.0 | 284.3 |
| spread_mixed | 16 | reads | 11,125 | 13,229 | 265 | 13,584 | 13,155 | **0.82x** | **0.85x** | 329.0 | 284.3 |
| search_spread | 16 | reads | 13,999 | 17,802 | 826 | 18,942 | 8,468 | **0.74x** | **1.65x** | 269.2 | 203.8 |

Checks:
  note mixed c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
