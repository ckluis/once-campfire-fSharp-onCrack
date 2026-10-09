
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,231 [1,224-1,238] | 1,079 | 30 | 753 | 688 | **1.64x** | **1.79x** | 81.2 | 84.3 |
| mixed | 16 | reads | 42,383 [42,325-42,440] | 43,283 | 219 | 24,232 | 18,597 | **1.75x** | **2.28x** | 81.2 | 84.3 |
| spread | 16 | reads | 188,361 [187,552-189,170] | 28,547 | 589 | 29,902 | 25,655 | **6.30x** | **7.34x** | 16.6 | 134.1 |
| spread_mixed | 16 | posts | 661 [661-661] | 337 | 6 | 393 | 319 | **1.68x** | **2.07x** | 331.4 | 284.3 |
| spread_mixed | 16 | reads | 11,017 [10,979-11,056] | 13,229 | 265 | 13,584 | 13,155 | **0.81x** | **0.84x** | 331.4 | 284.3 |
| search_spread | 16 | reads | 14,305 [14,276-14,334] | 17,802 | 826 | 18,942 | 8,468 | **0.76x** | **1.69x** | 263.4 | 203.8 |

Checks:
  note mixed c=16: warm-up did not settle (reached the maximum)
  note mixed c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 8 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
