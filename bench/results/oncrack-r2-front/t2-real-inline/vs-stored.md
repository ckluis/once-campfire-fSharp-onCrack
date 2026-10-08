
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 16 | posts | 1,593 | 1,079 | 30 | 753 | 688 | **2.12x** | **2.32x** | 96.6 | 84.3 |
| mixed | 16 | reads | 36,190 | 43,283 | 219 | 24,232 | 18,597 | **1.49x** | **1.95x** | 96.6 | 84.3 |
| spread | 16 | reads | 90,764 | 28,547 | 589 | 29,902 | 25,655 | **3.04x** | **3.54x** | 38.5 | 134.1 |
| spread_mixed | 16 | posts | 631 | 337 | 6 | 393 | 319 | **1.60x** | **1.98x** | 300.7 | 284.3 |
| spread_mixed | 16 | reads | 12,194 | 13,229 | 265 | 13,584 | 13,155 | **0.90x** | **0.93x** | 300.7 | 284.3 |
| search_spread | 16 | reads | 15,384 | 17,802 | 826 | 18,942 | 8,468 | **0.81x** | **1.82x** | 241.8 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
