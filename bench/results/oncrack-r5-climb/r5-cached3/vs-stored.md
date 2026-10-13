onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-climb/r5-cached3 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 172,150 [157,018-173,452] | 40,422 | **4.259x** | 28,623 | **6.014x** | 18.2 [18-19] | 93.6 | 122.4 |
| room page | 1 | 24,142 [22,851-24,538] | 7,617 | **3.170x** | 6,481 | **3.725x** | 20.9 [20-21] | 208.7 | 142.1 |
| messages page | 16 | 184,586 [169,720-185,233] | 37,836 | **4.879x** | 30,063 | **6.140x** | 16.5 [16-19] | 102.2 | 114.2 |
| messages page | 1 | 24,655 [23,466-25,510] | 8,312 | **2.966x** | 6,822 | **3.614x** | 20.3 [19-21] | 199.3 | 139.2 |
| sidebar | 16 | 194,379 [172,398-196,373] | 37,555 | **5.176x** | 28,238 | **6.884x** | 15.2 [15-19] | 101.8 | 123.2 |
| sidebar | 1 | 25,648 [15,467-25,671] | 8,000 | **3.206x** | 6,196 | **4.139x** | 19.1 [19-25] | 181.0 | 149.0 |
| search | 16 | 190,664 [146,798-190,942] | 34,070 | **5.596x** | 26,606 | **7.166x** | 15.7 [16-20] | 107.3 | 123.9 |
| search | 1 | 24,640 [23,725-27,246] | 6,055 | **4.069x** | 5,646 | **4.364x** | 19.6 [18-21] | 315.1 | 158.3 |
| post a message | 16 | 11,121 [10,316-14,024] | 8,905 | **1.249x** | 7,174 | **1.550x** | 205.5 [182-206] | 353.0 | 385.6 |
| post a message | 1 | 3,505 [3,150-5,047] | 3,052 | **1.149x** | 2,779 | **1.261x** | 258.2 [255-274] | 629.1 | 403.7 |

Checks:
  note messages_page c=1: host probe 1.119 after the window (noisy host)
  note messages_page c=1: host probe 1.132 after the window (noisy host)
  note messages_page c=16: host probe 1.107 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: host probe 1.111 after the window (noisy host)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note search c=1: host probe 1.101 after the window (noisy host)
  note search c=16: host probe 1.165 after the window (noisy host)
  note sidebar c=1: host probe 1.233 after the window (noisy host)
  note sidebar c=1: warm-up did not settle (reached the maximum)
  note sidebar c=16: host probe 1.113 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
