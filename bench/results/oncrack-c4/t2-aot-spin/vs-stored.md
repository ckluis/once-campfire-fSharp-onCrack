onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-c4/t2-aot-spin against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 106,507 | 40,422 | **2.635x** | 28,623 | **3.721x** | 35.3 | 93.6 | 122.4 |
| room page | 1 | 15,688 | 7,617 | **2.060x** | 6,481 | **2.421x** | 159.0 | 208.7 | 142.1 |
| messages page | 16 | 103,280 | 37,836 | **2.730x** | 30,063 | **3.435x** | 34.1 | 102.2 | 114.2 |
| messages page | 1 | 16,432 | 8,312 | **1.977x** | 6,822 | **2.409x** | 154.2 | 199.3 | 139.2 |
| sidebar | 16 | 120,134 | 37,555 | **3.199x** | 28,238 | **4.254x** | 30.6 | 101.8 | 123.2 |
| sidebar | 1 | 17,800 | 8,000 | **2.225x** | 6,196 | **2.873x** | 153.1 | 181.0 | 149.0 |
| search | 16 | 117,914 | 34,070 | **3.461x** | 26,606 | **4.432x** | 31.2 | 107.3 | 123.9 |
| search | 1 | 16,706 | 6,055 | **2.759x** | 5,646 | **2.959x** | 150.3 | 315.1 | 158.3 |
| post a message | 16 | 13,551 | 8,905 | **1.522x** | 7,174 | **1.889x** | 241.7 | 353.0 | 385.6 |
| post a message | 1 | 3,385 | 3,052 | **1.109x** | 2,779 | **1.218x** | 665.0 | 629.1 | 403.7 |

Checks:
  responses: every one 2xx with 0 connection errors in 10 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
