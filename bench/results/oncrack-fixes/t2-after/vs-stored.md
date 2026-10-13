onCrack in bench/results/oncrack-fixes/t2-after against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 122,324 | 40,422 | **3.026x** | 28,623 | **4.274x** | 31.0 | 93.6 | 122.4 |
| room page | 1 | 13,279 | 7,617 | **1.743x** | 6,481 | **2.049x** | 147.0 | 208.7 | 142.1 |
| messages page | 16 | 120,312 | 37,836 | **3.180x** | 30,063 | **4.002x** | 30.9 | 102.2 | 114.2 |
| messages page | 1 | 13,657 | 8,312 | **1.643x** | 6,822 | **2.002x** | 144.8 | 199.3 | 139.2 |
| sidebar | 16 | 135,999 | 37,555 | **3.621x** | 28,238 | **4.816x** | 27.4 | 101.8 | 123.2 |
| sidebar | 1 | 15,803 | 8,000 | **1.975x** | 6,196 | **2.550x** | 128.1 | 181.0 | 149.0 |
| search | 16 | 136,804 | 34,070 | **4.015x** | 26,606 | **5.142x** | 27.2 | 107.3 | 123.9 |
| search | 1 | 13,993 | 6,055 | **2.311x** | 5,646 | **2.478x** | 139.7 | 315.1 | 158.3 |
| post a message | 16 | 12,829 | 8,905 | **1.441x** | 7,174 | **1.788x** | 236.5 | 353.0 | 385.6 |
| post a message | 1 | 3,276 | 3,052 | **1.073x** | 2,779 | **1.179x** | 599.7 | 629.1 | 403.7 |

Checks:
  note messages_page c=1: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 10 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
