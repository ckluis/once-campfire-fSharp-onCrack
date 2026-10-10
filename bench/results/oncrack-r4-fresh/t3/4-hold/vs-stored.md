onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r4-fresh/t3/4-hold against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 130,936 | 40,422 | **3.239x** | 28,623 | **4.575x** | 24.9 | 93.6 | 122.4 |
| room page | 1 | 19,723 | 7,617 | **2.589x** | 6,481 | **3.043x** | 26.5 | 208.7 | 142.1 |
| messages page | 16 | 139,118 | 37,836 | **3.677x** | 30,063 | **4.628x** | 23.3 | 102.2 | 114.2 |
| messages page | 1 | 20,254 | 8,312 | **2.437x** | 6,822 | **2.969x** | 25.6 | 199.3 | 139.2 |

Checks:
  note messages_page c=1: host probe 1.115 after the window (noisy host)
  note messages_page c=16: host probe 1.102 after the window (noisy host)
  note room_show c=1: warm-up did not settle (reached the maximum)
  note room_show c=1: host probe 1.102 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
