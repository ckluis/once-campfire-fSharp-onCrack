
Realistic workloads against the same-session baseline of bench/results/oncrack-r2-bench (medians; reads/s and posts/s apart)

| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| search_spread | 16 | reads | 24,109 | 17,802 | 826 | 18,942 | 8,468 | **1.27x** | **2.85x** | 148.4 | 203.8 |

Checks:
  responses: every one 2xx with 0 connection errors in 1 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
