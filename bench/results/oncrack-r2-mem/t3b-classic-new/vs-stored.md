onCrack in bench/results/oncrack-r2-mem/t3b-classic-new against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 176,902 [176,328-177,476] | 40,422 | **4.376x** | 28,623 | **6.180x** | 17.6 [18-18] | 93.6 | 122.4 |
| messages page | 16 | 185,005 [183,840-186,171] | 37,836 | **4.890x** | 30,063 | **6.154x** | 16.4 [16-17] | 102.2 | 114.2 |
| sidebar | 16 | 197,655 [197,516-197,793] | 37,555 | **5.263x** | 28,238 | **7.000x** | 14.9 [15-15] | 101.8 | 123.2 |
| search | 16 | 193,464 [193,394-193,533] | 34,070 | **5.679x** | 26,606 | **7.271x** | 15.4 [15-15] | 107.3 | 123.9 |
| post a message | 16 | 15,687 [15,608-15,765] | 8,905 | **1.762x** | 7,174 | **2.187x** | 177.8 [178-178] | 353.0 | 385.6 |

Checks:
  responses: every one 2xx with 0 connection errors in 10 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
