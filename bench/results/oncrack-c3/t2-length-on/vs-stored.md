onCrack in bench/results/oncrack-c3/t2-length-on against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 122,477 | 40,422 | **3.030x** | 28,623 | **4.279x** | 30.7 | 93.6 | 122.4 |
| room page | 1 | 13,179 | 7,617 | **1.730x** | 6,481 | **2.034x** | 147.3 | 208.7 | 142.1 |
| messages page | 16 | 122,358 | 37,836 | **3.234x** | 30,063 | **4.070x** | 29.9 | 102.2 | 114.2 |
| messages page | 1 | 13,420 | 8,312 | **1.615x** | 6,822 | **1.967x** | 145.3 | 199.3 | 139.2 |
| sidebar | 16 | 137,123 | 37,555 | **3.651x** | 28,238 | **4.856x** | 26.8 | 101.8 | 123.2 |
| sidebar | 1 | 15,674 | 8,000 | **1.959x** | 6,196 | **2.529x** | 127.4 | 181.0 | 149.0 |
| search | 16 | 136,805 | 34,070 | **4.015x** | 26,606 | **5.142x** | 27.3 | 107.3 | 123.9 |
| search | 1 | 14,071 | 6,055 | **2.324x** | 5,646 | **2.492x** | 139.6 | 315.1 | 158.3 |
| post a message | 16 | 13,049 | 8,905 | **1.465x** | 7,174 | **1.819x** | 233.5 | 353.0 | 385.6 |
| post a message | 1 | 3,100 | 3,052 | **1.016x** | 2,779 | **1.115x** | 614.3 | 629.1 | 403.7 |

Checks:
  note messages_page c=1: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 10 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
