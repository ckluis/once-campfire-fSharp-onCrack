
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,374 | 1,079 | 30 | 753 | 688 | **1.83x** | **2.00x** | 78.2 | 84.3 |
| mixed | 16 | reads | 42,825 | 43,283 | 219 | 24,232 | 18,597 | **1.77x** | **2.30x** | 78.2 | 84.3 |
| spread | 16 | reads | 190,070 | 28,547 | 589 | 29,902 | 25,655 | **6.36x** | **7.41x** | 16.4 | 134.1 |
| spread_mixed | 16 | posts | 679 | 337 | 6 | 393 | 319 | **1.73x** | **2.13x** | 317.9 | 284.3 |
| spread_mixed | 16 | reads | 11,467 | 13,229 | 265 | 13,584 | 13,155 | **0.84x** | **0.87x** | 317.9 | 284.3 |
| search_spread | 16 | reads | 15,778 | 17,802 | 826 | 18,942 | 8,468 | **0.83x** | **1.86x** | 234.6 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
