onCrack in bench/results/oncrack-r2-verifier/t3 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 175,720 [174,258-175,871] | 40,422 | **4.347x** | 28,623 | **6.139x** | 17.6 [18-18] | 93.6 | 122.4 |
| room page | 1 | 26,426 [25,541-26,783] | 7,617 | **3.470x** | 6,481 | **4.078x** | 18.3 [18-20] | 208.7 | 142.1 |
| messages page | 16 | 185,184 [184,660-186,353] | 37,836 | **4.894x** | 30,063 | **6.160x** | 16.2 [16-16] | 102.2 | 114.2 |
| messages page | 1 | 26,607 [26,042-27,008] | 8,312 | **3.201x** | 6,822 | **3.900x** | 18.2 [18-19] | 199.3 | 139.2 |
| sidebar | 16 | 196,907 [196,219-199,848] | 37,555 | **5.243x** | 28,238 | **6.973x** | 14.9 [15-15] | 101.8 | 123.2 |
| sidebar | 1 | 26,904 [26,666-27,069] | 8,000 | **3.363x** | 6,196 | **4.342x** | 17.5 [17-18] | 181.0 | 149.0 |
| search | 16 | 196,012 [193,879-196,439] | 34,070 | **5.753x** | 26,606 | **7.367x** | 15.0 [15-15] | 107.3 | 123.9 |
| search | 1 | 28,118 [27,824-28,203] | 6,055 | **4.644x** | 5,646 | **4.980x** | 16.9 [17-17] | 315.1 | 158.3 |
| post a message | 16 | 11,050 [10,562-11,344] | 8,905 | **1.241x** | 7,174 | **1.540x** | 174.5 [173-178] | 353.0 | 385.6 |
| post a message | 1 | 3,999 [3,345-5,130] | 3,052 | **1.310x** | 2,779 | **1.439x** | 246.0 [246-247] | 629.1 | 403.7 |

Checks:
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
