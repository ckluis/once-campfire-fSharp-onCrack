onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-climb/r5-fresh against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 166,316 [165,420-166,416] | 40,422 | **4.114x** | 28,623 | **5.811x** | 19.3 [19-19] | 93.6 | 122.4 |
| room page | 1 | 24,563 [24,083-24,840] | 7,617 | **3.225x** | 6,481 | **3.790x** | 21.1 [21-22] | 208.7 | 142.1 |
| messages page | 16 | 173,518 [162,848-175,227] | 37,836 | **4.586x** | 30,063 | **5.772x** | 18.1 [18-21] | 102.2 | 114.2 |
| messages page | 1 | 24,854 [21,908-25,164] | 8,312 | **2.990x** | 6,822 | **3.643x** | 20.6 [20-24] | 199.3 | 139.2 |
| sidebar | 16 | 187,738 [187,708-189,755] | 37,555 | **4.999x** | 28,238 | **6.648x** | 16.3 [16-16] | 101.8 | 123.2 |
| sidebar | 1 | 25,086 [24,281-25,622] | 8,000 | **3.136x** | 6,196 | **4.048x** | 19.8 [20-21] | 181.0 | 149.0 |
| search | 16 | 184,094 [183,187-184,278] | 34,070 | **5.403x** | 26,606 | **6.919x** | 16.8 [17-17] | 107.3 | 123.9 |
| search | 1 | 24,584 [24,010-25,241] | 6,055 | **4.060x** | 5,646 | **4.354x** | 20.7 [20-21] | 315.1 | 158.3 |
| post a message | 16 | 9,911 [9,004-11,270] | 8,905 | **1.113x** | 7,174 | **1.381x** | 213.8 [188-220] | 353.0 | 385.6 |
| post a message | 1 | 3,462 [3,143-3,545] | 3,052 | **1.134x** | 2,779 | **1.246x** | 269.7 [260-273] | 629.1 | 403.7 |

Checks:
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: host probe 1.286 after the window (noisy host)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
