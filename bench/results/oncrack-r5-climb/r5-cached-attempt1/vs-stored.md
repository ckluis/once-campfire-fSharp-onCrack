onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-climb/r5-cached against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 146,329 [98,121-168,785] | 40,422 | **3.620x** | 28,623 | **5.112x** | 22.6 [18-26] | 93.6 | 122.4 |
| room page | 1 | 22,687 [10,112-25,689] | 7,617 | **2.979x** | 6,481 | **3.501x** | 21.8 [20-42] | 208.7 | 142.1 |
| messages page | 16 | 164,452 [155,388-180,005] | 37,836 | **4.346x** | 30,063 | **5.470x** | 19.9 [17-22] | 102.2 | 114.2 |
| messages page | 1 | 22,318 [14,842-26,619] | 8,312 | **2.685x** | 6,822 | **3.271x** | 22.0 [18-32] | 199.3 | 139.2 |
| sidebar | 16 | 161,784 [161,021-177,104] | 37,555 | **4.308x** | 28,238 | **5.729x** | 19.6 [18-20] | 101.8 | 123.2 |
| sidebar | 1 | 23,886 [22,578-27,311] | 8,000 | **2.986x** | 6,196 | **3.855x** | 20.3 [18-21] | 181.0 | 149.0 |
| search | 16 | 147,371 [145,034-186,287] | 34,070 | **4.326x** | 26,606 | **5.539x** | 20.5 [16-22] | 107.3 | 123.9 |
| search | 1 | 24,679 [23,597-24,729] | 6,055 | **4.076x** | 5,646 | **4.371x** | 19.8 [19-21] | 315.1 | 158.3 |
| post a message | 16 | 10,529 [9,840-13,431] | 8,905 | **1.182x** | 7,174 | **1.468x** | 188.1 [186-223] | 353.0 | 385.6 |
| post a message | 1 | 2,270 [1,932-2,796] | 3,052 | **0.744x** | 2,779 | **0.817x** | 278.4 [260-648] | 629.1 | 403.7 |

Checks:
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note messages_page c=1: host probe 1.286 after the window (noisy host)
  note messages_page c=16: host probe 1.142 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: host probe 1.277 after the window (noisy host)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note room_show c=1: warm-up did not settle (reached the maximum)
  note room_show c=1: warm-up did not settle (reached the maximum)
  note room_show c=1: host probe 1.419 after the window (noisy host)
  note room_show c=16: warm-up did not settle (reached the maximum)
  note room_show c=16: warm-up did not settle (reached the maximum)
  note room_show c=16: host probe 1.318 after the window (noisy host)
  note search c=16: warm-up did not settle (reached the maximum)
  note search c=16: host probe 1.101 after the window (noisy host)
  note search c=16: warm-up did not settle (reached the maximum)
  note search c=16: host probe 1.311 after the window (noisy host)
  note sidebar c=16: warm-up did not settle (reached the maximum)
  note sidebar c=16: host probe 1.135 after the window (noisy host)
  note sidebar c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
