onCrack in bench/results/oncrack-r2-front/tier3 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 174,412 [174,354-175,796] | 40,422 | **4.315x** | 28,623 | **6.093x** | 17.7 [18-18] | 93.6 | 122.4 |
| room page | 1 | 26,080 [25,852-26,151] | 7,617 | **3.424x** | 6,481 | **4.024x** | 19.3 [19-19] | 208.7 | 142.1 |
| messages page | 16 | 184,722 [184,139-184,868] | 37,836 | **4.882x** | 30,063 | **6.145x** | 16.4 [16-16] | 102.2 | 114.2 |
| messages page | 1 | 25,963 [25,544-26,142] | 8,312 | **3.124x** | 6,822 | **3.806x** | 18.9 [19-19] | 199.3 | 139.2 |
| sidebar | 16 | 197,204 [197,201-197,598] | 37,555 | **5.251x** | 28,238 | **6.984x** | 14.8 [15-15] | 101.8 | 123.2 |
| sidebar | 1 | 26,723 [26,418-26,750] | 8,000 | **3.340x** | 6,196 | **4.313x** | 18.1 [18-18] | 181.0 | 149.0 |
| search | 16 | 192,332 [192,252-193,711] | 34,070 | **5.645x** | 26,606 | **7.229x** | 15.3 [15-15] | 107.3 | 123.9 |
| search | 1 | 27,500 [27,254-27,555] | 6,055 | **4.541x** | 5,646 | **4.871x** | 17.5 [18-18] | 315.1 | 158.3 |
| post a message | 16 | 10,664 [10,362-12,293] | 8,905 | **1.197x** | 7,174 | **1.486x** | 186.2 [185-186] | 353.0 | 385.6 |
| post a message | 1 | 4,876 [4,127-4,951] | 3,052 | **1.598x** | 2,779 | **1.754x** | 391.6 [389-392] | 629.1 | 403.7 |

Checks:
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
