onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-c0/tier3 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 38,994 [38,728-39,005] | 40,422 | **0.965x** | 28,623 | **1.362x** | 91.6 [92-92] | 93.6 | 122.4 |
| room page | 1 | 7,450 [7,440-7,468] | 7,617 | **0.978x** | 6,481 | **1.150x** | 210.6 [209-213] | 208.7 | 142.1 |
| messages page | 16 | 41,859 [41,372-42,306] | 37,836 | **1.106x** | 30,063 | **1.392x** | 84.9 [84-85] | 102.2 | 114.2 |
| messages page | 1 | 8,148 [8,028-8,161] | 8,312 | **0.980x** | 6,822 | **1.194x** | 202.6 [202-204] | 199.3 | 139.2 |
| sidebar | 16 | 37,894 [37,615-37,950] | 37,555 | **1.009x** | 28,238 | **1.342x** | 95.1 [95-96] | 101.8 | 123.2 |
| sidebar | 1 | 7,620 [7,602-7,662] | 8,000 | **0.953x** | 6,196 | **1.230x** | 189.6 [189-194] | 181.0 | 149.0 |
| search | 16 | 33,931 [33,857-33,994] | 34,070 | **0.996x** | 26,606 | **1.275x** | 107.5 [108-108] | 107.3 | 123.9 |
| search | 1 | 5,669 [5,652-5,803] | 6,055 | **0.936x** | 5,646 | **1.004x** | 328.3 [328-329] | 315.1 | 158.3 |
| post a message | 16 | 8,566 [8,492-8,803] | 8,905 | **0.962x** | 7,174 | **1.194x** | 359.9 [356-361] | 353.0 | 385.6 |
| post a message | 1 | 2,970 [2,885-2,971] | 3,052 | **0.973x** | 2,779 | **1.069x** | 641.9 [640-646] | 629.1 | 403.7 |

Checks:
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
