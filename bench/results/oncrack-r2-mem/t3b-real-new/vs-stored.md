
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,356 [1,334-1,378] | 1,079 | 30 | 753 | 688 | **1.80x** | **1.97x** | 78.2 | 84.3 |
| mixed | 16 | reads | 43,550 [43,336-43,763] | 43,283 | 219 | 24,232 | 18,597 | **1.80x** | **2.34x** | 78.2 | 84.3 |
| spread | 16 | reads | 189,909 [189,609-190,209] | 28,547 | 589 | 29,902 | 25,655 | **6.35x** | **7.40x** | 16.4 | 134.1 |
| spread_mixed | 16 | posts | 663 [660-665] | 337 | 6 | 393 | 319 | **1.68x** | **2.08x** | 331.5 | 284.3 |
| spread_mixed | 16 | reads | 11,030 [10,948-11,112] | 13,229 | 265 | 13,584 | 13,155 | **0.81x** | **0.84x** | 331.5 | 284.3 |
| search_spread | 16 | reads | 17,375 [17,356-17,394] | 17,802 | 826 | 18,942 | 8,468 | **0.92x** | **2.05x** | 212.0 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 8 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
