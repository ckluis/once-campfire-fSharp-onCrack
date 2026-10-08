
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,355 [1,345-1,386] | 1,079 | 30 | 753 | 688 | **1.80x** | **1.97x** | 77.4 | 84.3 |
| mixed | 16 | reads | 45,187 [45,073-46,009] | 43,283 | 219 | 24,232 | 18,597 | **1.86x** | **2.43x** | 77.4 | 84.3 |
| spread | 16 | reads | 93,619 [93,361-94,352] | 28,547 | 589 | 29,902 | 25,655 | **3.13x** | **3.65x** | 38.8 | 134.1 |
| spread_mixed | 16 | posts | 674 [670-682] | 337 | 6 | 393 | 319 | **1.71x** | **2.11x** | 321.7 | 284.3 |
| spread_mixed | 16 | reads | 11,322 [11,239-11,520] | 13,229 | 265 | 13,584 | 13,155 | **0.83x** | **0.86x** | 321.7 | 284.3 |
| search_spread | 16 | reads | 16,408 [15,984-16,769] | 17,802 | 826 | 18,942 | 8,468 | **0.87x** | **1.94x** | 225.3 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 12 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
