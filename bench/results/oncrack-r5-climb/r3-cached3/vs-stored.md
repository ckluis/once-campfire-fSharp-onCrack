onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-climb/r3-cached3 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 176,893 [176,267-177,291] | 40,422 | **4.376x** | 28,623 | **6.180x** | 17.5 [18-18] | 93.6 | 122.4 |
| room page | 1 | 25,732 [24,633-26,031] | 7,617 | **3.378x** | 6,481 | **3.970x** | 19.4 [19-20] | 208.7 | 142.1 |
| messages page | 16 | 185,303 [180,626-185,355] | 37,836 | **4.897x** | 30,063 | **6.164x** | 16.5 [16-17] | 102.2 | 114.2 |
| messages page | 1 | 25,126 [23,637-25,590] | 8,312 | **3.023x** | 6,822 | **3.683x** | 19.5 [19-21] | 199.3 | 139.2 |
| sidebar | 16 | 197,055 [178,814-197,798] | 37,555 | **5.247x** | 28,238 | **6.978x** | 15.0 [15-18] | 101.8 | 123.2 |
| sidebar | 1 | 25,572 [25,236-26,010] | 8,000 | **3.197x** | 6,196 | **4.127x** | 18.7 [19-19] | 181.0 | 149.0 |
| search | 16 | 191,404 [189,437-192,927] | 34,070 | **5.618x** | 26,606 | **7.194x** | 15.6 [16-16] | 107.3 | 123.9 |
| search | 1 | 24,542 [24,509-25,331] | 6,055 | **4.053x** | 5,646 | **4.347x** | 19.7 [19-20] | 315.1 | 158.3 |
| post a message | 16 | 8,057 [7,626-10,891] | 8,905 | **0.905x** | 7,174 | **1.123x** | 180.9 [181-199] | 353.0 | 385.6 |
| post a message | 1 | 3,533 [2,140-5,038] | 3,052 | **1.158x** | 2,779 | **1.271x** | 258.4 [251-298] | 629.1 | 403.7 |

Checks:
  note messages_page c=16: host probe 1.146 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: host probe 1.117 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note search c=1: warm-up did not settle (reached the maximum)
  note sidebar c=1: host probe 1.111 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
