onCrack in bench/results/oncrack-fixes/t2-before against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 116,841 | 40,422 | **2.891x** | 28,623 | **4.082x** | 30.8 | 93.6 | 122.4 |
| room page | 1 | 14,007 | 7,617 | **1.839x** | 6,481 | **2.161x** | 138.1 | 208.7 | 142.1 |
| messages page | 16 | 121,809 | 37,836 | **3.219x** | 30,063 | **4.052x** | 29.6 | 102.2 | 114.2 |
| messages page | 1 | 13,374 | 8,312 | **1.609x** | 6,822 | **1.960x** | 146.1 | 199.3 | 139.2 |
| sidebar | 16 | 137,140 | 37,555 | **3.652x** | 28,238 | **4.857x** | 26.7 | 101.8 | 123.2 |
| sidebar | 1 | 14,627 | 8,000 | **1.828x** | 6,196 | **2.361x** | 136.3 | 181.0 | 149.0 |
| search | 16 | 135,895 | 34,070 | **3.989x** | 26,606 | **5.108x** | 27.3 | 107.3 | 123.9 |
| search | 1 | 14,420 | 6,055 | **2.381x** | 5,646 | **2.554x** | 138.0 | 315.1 | 158.3 |
| post a message | 16 | 13,026 | 8,905 | **1.463x** | 7,174 | **1.816x** | 234.6 | 353.0 | 385.6 |
| post a message | 1 | 3,178 | 3,052 | **1.041x** | 2,779 | **1.144x** | 606.6 | 629.1 | 403.7 |

Checks:
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note sidebar c=1: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 10 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
