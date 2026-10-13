
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,362 [1,352-1,373] | 1,079 | 30 | 753 | 688 | **1.81x** | **1.98x** | 78.3 | 84.3 |
| mixed | 16 | reads | 42,355 [42,220-42,491] | 43,283 | 219 | 24,232 | 18,597 | **1.75x** | **2.28x** | 78.3 | 84.3 |
| spread | 16 | reads | 88,628 [88,432-88,825] | 28,547 | 589 | 29,902 | 25,655 | **2.96x** | **3.45x** | 38.2 | 134.1 |
| spread_mixed | 16 | posts | 679 [668-690] | 337 | 6 | 393 | 319 | **1.73x** | **2.13x** | 319.5 | 284.3 |
| spread_mixed | 16 | reads | 11,387 [11,135-11,638] | 13,229 | 265 | 13,584 | 13,155 | **0.84x** | **0.87x** | 319.5 | 284.3 |
| search_spread | 16 | reads | 16,623 [16,209-17,037] | 17,802 | 826 | 18,942 | 8,468 | **0.88x** | **1.96x** | 222.3 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 8 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
