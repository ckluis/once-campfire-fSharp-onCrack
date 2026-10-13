onCrack in bench/results/oncrack-c3/t2-length-off against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 100,974 | 40,422 | **2.498x** | 28,623 | **3.528x** | 32.1 | 93.6 | 122.4 |
| room page | 1 | 11,790 | 7,617 | **1.548x** | 6,481 | **1.819x** | 153.3 | 208.7 | 142.1 |
| messages page | 16 | 102,770 | 37,836 | **2.716x** | 30,063 | **3.418x** | 30.9 | 102.2 | 114.2 |
| messages page | 1 | 11,898 | 8,312 | **1.432x** | 6,822 | **1.744x** | 156.0 | 199.3 | 139.2 |
| sidebar | 16 | 115,253 | 37,555 | **3.069x** | 28,238 | **4.082x** | 26.8 | 101.8 | 123.2 |
| sidebar | 1 | 12,970 | 8,000 | **1.621x** | 6,196 | **2.093x** | 143.9 | 181.0 | 149.0 |
| search | 16 | 72,058 | 34,070 | **2.115x** | 26,606 | **2.708x** | 31.4 | 107.3 | 123.9 |
| search | 1 | 12,785 | 6,055 | **2.111x** | 5,646 | **2.264x** | 146.4 | 315.1 | 158.3 |
| post a message | 16 | 11,819 | 8,905 | **1.327x** | 7,174 | **1.648x** | 257.6 | 353.0 | 385.6 |
| post a message | 1 | 3,112 | 3,052 | **1.020x** | 2,779 | **1.120x** | 619.9 | 629.1 | 403.7 |

Checks:
  note search c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 10 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
