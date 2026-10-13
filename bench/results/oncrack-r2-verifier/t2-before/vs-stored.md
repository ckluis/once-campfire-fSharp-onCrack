onCrack in bench/results/oncrack-r2-verifier/t2-before against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 174,478 | 40,422 | **4.316x** | 28,623 | **6.096x** | 17.8 | 93.6 | 122.4 |
| room page | 1 | 26,097 | 7,617 | **3.426x** | 6,481 | **4.027x** | 19.1 | 208.7 | 142.1 |
| messages page | 16 | 183,259 | 37,836 | **4.843x** | 30,063 | **6.096x** | 16.5 | 102.2 | 114.2 |
| messages page | 1 | 26,684 | 8,312 | **3.210x** | 6,822 | **3.911x** | 18.5 | 199.3 | 139.2 |
| sidebar | 16 | 184,098 | 37,555 | **4.902x** | 28,238 | **6.520x** | 15.5 | 101.8 | 123.2 |
| sidebar | 1 | 27,121 | 8,000 | **3.390x** | 6,196 | **4.377x** | 17.6 | 181.0 | 149.0 |
| search | 16 | 194,487 | 34,070 | **5.709x** | 26,606 | **7.310x** | 15.1 | 107.3 | 123.9 |
| search | 1 | 27,452 | 6,055 | **4.534x** | 5,646 | **4.862x** | 17.6 | 315.1 | 158.3 |
| post a message | 16 | 12,653 | 8,905 | **1.421x** | 7,174 | **1.764x** | 177.0 | 353.0 | 385.6 |
| post a message | 1 | 3,851 | 3,052 | **1.262x** | 2,779 | **1.386x** | 254.2 | 629.1 | 403.7 |

Checks:
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 10 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
