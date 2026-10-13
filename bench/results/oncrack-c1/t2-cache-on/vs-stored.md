onCrack in bench/results/oncrack-c1/t2-cache-on against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 95,310 | 40,422 | **2.358x** | 28,623 | **3.330x** | 32.2 | 93.6 | 122.4 |
| messages page | 16 | 103,268 | 37,836 | **2.729x** | 30,063 | **3.435x** | 30.7 | 102.2 | 114.2 |
| sidebar | 16 | 110,523 | 37,555 | **2.943x** | 28,238 | **3.914x** | 27.3 | 101.8 | 123.2 |
| search | 16 | 71,472 | 34,070 | **2.098x** | 26,606 | **2.686x** | 31.4 | 107.3 | 123.9 |
| post a message | 16 | 8,735 | 8,905 | **0.981x** | 7,174 | **1.218x** | 354.5 | 353.0 | 385.6 |

Checks:
  note search c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 5 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
