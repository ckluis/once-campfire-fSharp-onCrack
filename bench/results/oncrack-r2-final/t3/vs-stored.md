onCrack in bench/results/oncrack-r2-final/t3 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 177,276 [174,732-178,994] | 40,422 | **4.386x** | 28,623 | **6.193x** | 17.4 [17-18] | 93.6 | 122.4 |
| room page | 1 | 26,215 [25,986-26,293] | 7,617 | **3.442x** | 6,481 | **4.045x** | 18.9 [19-19] | 208.7 | 142.1 |
| messages page | 16 | 185,538 [178,378-187,179] | 37,836 | **4.904x** | 30,063 | **6.172x** | 16.2 [16-17] | 102.2 | 114.2 |
| messages page | 1 | 26,199 [25,921-26,576] | 8,312 | **3.152x** | 6,822 | **3.840x** | 18.7 [18-19] | 199.3 | 139.2 |
| sidebar | 16 | 198,161 [198,115-198,627] | 37,555 | **5.277x** | 28,238 | **7.018x** | 14.7 [15-15] | 101.8 | 123.2 |
| sidebar | 1 | 26,821 [26,022-27,114] | 8,000 | **3.353x** | 6,196 | **4.328x** | 17.9 [18-18] | 181.0 | 149.0 |
| search | 16 | 192,737 [192,538-194,164] | 34,070 | **5.657x** | 26,606 | **7.244x** | 15.4 [15-15] | 107.3 | 123.9 |
| search | 1 | 27,765 [27,647-28,108] | 6,055 | **4.585x** | 5,646 | **4.918x** | 17.3 [17-17] | 315.1 | 158.3 |
| post a message | 16 | 11,292 [10,732-12,470] | 8,905 | **1.268x** | 7,174 | **1.574x** | 178.2 [175-180] | 353.0 | 385.6 |
| post a message | 1 | 5,112 [3,847-5,152] | 3,052 | **1.675x** | 2,779 | **1.839x** | 248.0 [247-250] | 629.1 | 403.7 |

Checks:
  note messages_page c=16: host probe 1.105 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
