onCrack in bench/results/oncrack-r2-verifier/t2-after against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 174,013 | 40,422 | **4.305x** | 28,623 | **6.079x** | 17.8 | 93.6 | 122.4 |
| room page | 1 | 25,976 | 7,617 | **3.410x** | 6,481 | **4.008x** | 19.4 | 208.7 | 142.1 |
| messages page | 16 | 185,907 | 37,836 | **4.913x** | 30,063 | **6.184x** | 16.3 | 102.2 | 114.2 |
| messages page | 1 | 26,792 | 8,312 | **3.223x** | 6,822 | **3.927x** | 18.6 | 199.3 | 139.2 |
| sidebar | 16 | 198,311 | 37,555 | **5.281x** | 28,238 | **7.023x** | 14.8 | 101.8 | 123.2 |
| sidebar | 1 | 27,421 | 8,000 | **3.428x** | 6,196 | **4.425x** | 17.5 | 181.0 | 149.0 |
| search | 16 | 192,499 | 34,070 | **5.650x** | 26,606 | **7.235x** | 15.3 | 107.3 | 123.9 |
| search | 1 | 27,278 | 6,055 | **4.505x** | 5,646 | **4.831x** | 17.8 | 315.1 | 158.3 |
| post a message | 16 | 12,439 | 8,905 | **1.397x** | 7,174 | **1.734x** | 179.1 | 353.0 | 385.6 |
| post a message | 1 | 5,019 | 3,052 | **1.645x** | 2,779 | **1.806x** | 253.8 | 629.1 | 403.7 |

Checks:
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 10 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
