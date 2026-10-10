onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r4-fresh/t3/2-nohold against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 130,583 | 40,422 | **3.230x** | 28,623 | **4.562x** | 24.3 | 93.6 | 122.4 |
| room page | 1 | 17,154 | 7,617 | **2.252x** | 6,481 | **2.647x** | 29.3 | 208.7 | 142.1 |
| messages page | 16 | 116,027 | 37,836 | **3.067x** | 30,063 | **3.859x** | 27.9 | 102.2 | 114.2 |
| messages page | 1 | 21,402 | 8,312 | **2.575x** | 6,822 | **3.137x** | 25.6 | 199.3 | 139.2 |

Checks:
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note messages_page c=16: host probe 1.103 after the window (noisy host)
  note room_show c=1: warm-up did not settle (reached the maximum)
  note room_show c=1: host probe 1.136 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
