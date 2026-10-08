onCrack in bench/results/oncrack-r2-c1/tier3 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 176,184 [175,435-178,554] | 40,422 | **4.359x** | 28,623 | **6.155x** | 17.4 [17-18] | 93.6 | 122.4 |
| room page | 1 | 26,590 [26,082-26,782] | 7,617 | **3.491x** | 6,481 | **4.103x** | 18.7 [18-19] | 208.7 | 142.1 |
| messages page | 16 | 182,906 [176,120-186,207] | 37,836 | **4.834x** | 30,063 | **6.084x** | 16.4 [16-17] | 102.2 | 114.2 |
| messages page | 1 | 27,186 [26,882-27,458] | 8,312 | **3.271x** | 6,822 | **3.985x** | 18.0 [18-18] | 199.3 | 139.2 |
| sidebar | 16 | 196,077 [195,625-199,372] | 37,555 | **5.221x** | 28,238 | **6.944x** | 15.0 [15-15] | 101.8 | 123.2 |
| sidebar | 1 | 27,784 [27,499-28,071] | 8,000 | **3.473x** | 6,196 | **4.484x** | 17.1 [17-17] | 181.0 | 149.0 |
| search | 16 | 194,734 [192,953-194,738] | 34,070 | **5.716x** | 26,606 | **7.319x** | 15.1 [15-15] | 107.3 | 123.9 |
| search | 1 | 27,351 [27,351-28,045] | 6,055 | **4.517x** | 5,646 | **4.844x** | 17.5 [17-18] | 315.1 | 158.3 |
| post a message | 16 | 12,782 [10,964-14,320] | 8,905 | **1.435x** | 7,174 | **1.782x** | 175.0 [174-175] | 353.0 | 385.6 |
| post a message | 1 | 5,172 [5,146-5,265] | 3,052 | **1.695x** | 2,779 | **1.861x** | 245.6 [240-247] | 629.1 | 403.7 |

Checks:
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
