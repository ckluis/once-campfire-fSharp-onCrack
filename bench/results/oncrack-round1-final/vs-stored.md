onCrack in bench/results/oncrack-round1-final against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 123,942 [123,291-124,434] | 40,422 | **3.066x** | 28,623 | **4.330x** | 30.1 [30-30] | 93.6 | 122.4 |
| room page | 1 | 13,428 [13,323-13,620] | 7,617 | **1.763x** | 6,481 | **2.072x** | 144.2 [142-146] | 208.7 | 142.1 |
| messages page | 16 | 123,252 [121,467-123,722] | 37,836 | **3.257x** | 30,063 | **4.100x** | 29.8 [30-30] | 102.2 | 114.2 |
| messages page | 1 | 13,623 [13,378-14,194] | 8,312 | **1.639x** | 6,822 | **1.997x** | 142.3 [137-143] | 199.3 | 139.2 |
| sidebar | 16 | 138,182 [134,033-139,091] | 37,555 | **3.679x** | 28,238 | **4.894x** | 26.7 [26-27] | 101.8 | 123.2 |
| sidebar | 1 | 14,987 [14,808-15,303] | 8,000 | **1.873x** | 6,196 | **2.419x** | 133.7 [133-135] | 181.0 | 149.0 |
| search | 16 | 136,032 [136,003-136,210] | 34,070 | **3.993x** | 26,606 | **5.113x** | 27.3 [27-27] | 107.3 | 123.9 |
| search | 1 | 15,700 [14,633-15,844] | 6,055 | **2.593x** | 5,646 | **2.781x** | 126.8 [126-136] | 315.1 | 158.3 |
| post a message | 16 | 13,215 [12,934-13,314] | 8,905 | **1.484x** | 7,174 | **1.842x** | 230.0 [230-236] | 353.0 | 385.6 |
| post a message | 1 | 3,395 [3,198-3,409] | 3,052 | **1.113x** | 2,779 | **1.222x** | 585.2 [581-608] | 629.1 | 403.7 |

Checks:
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note search c=1: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 72 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
