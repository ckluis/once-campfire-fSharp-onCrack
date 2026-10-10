onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r4-fresh/t3/6-nohold against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 117,232 | 40,422 | **2.900x** | 28,623 | **4.096x** | 27.7 | 93.6 | 122.4 |
| room page | 1 | 19,136 | 7,617 | **2.512x** | 6,481 | **2.953x** | 27.7 | 208.7 | 142.1 |
| messages page | 16 | 122,786 | 37,836 | **3.245x** | 30,063 | **4.084x** | 26.0 | 102.2 | 114.2 |
| messages page | 1 | 19,599 | 8,312 | **2.358x** | 6,822 | **2.873x** | 26.8 | 199.3 | 139.2 |

Checks:
  note messages_page c=16: host probe 1.117 after the window (noisy host)
  note room_show c=16: host probe 1.102 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
