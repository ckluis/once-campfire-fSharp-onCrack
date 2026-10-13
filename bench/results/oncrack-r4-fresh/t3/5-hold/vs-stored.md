onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r4-fresh/t3/5-hold against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 127,344 | 40,422 | **3.150x** | 28,623 | **4.449x** | 25.7 | 93.6 | 122.4 |
| room page | 1 | 19,875 | 7,617 | **2.609x** | 6,481 | **3.067x** | 26.1 | 208.7 | 142.1 |
| messages page | 16 | 138,861 | 37,836 | **3.670x** | 30,063 | **4.619x** | 23.5 | 102.2 | 114.2 |
| messages page | 1 | 20,178 | 8,312 | **2.428x** | 6,822 | **2.958x** | 25.7 | 199.3 | 139.2 |

Checks:
  note messages_page c=16: host probe 1.111 after the window (noisy host)
  note room_show c=1: host probe 1.101 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
