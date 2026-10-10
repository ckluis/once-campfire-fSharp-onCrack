onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r4-fresh/t3/3-nohold against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 93,794 | 40,422 | **2.320x** | 28,623 | **3.277x** | 31.6 | 93.6 | 122.4 |
| room page | 1 | 17,815 | 7,617 | **2.339x** | 6,481 | **2.749x** | 28.1 | 208.7 | 142.1 |
| messages page | 16 | 123,380 | 37,836 | **3.261x** | 30,063 | **4.104x** | 25.9 | 102.2 | 114.2 |
| messages page | 1 | 19,407 | 8,312 | **2.335x** | 6,822 | **2.845x** | 27.1 | 199.3 | 139.2 |

Checks:
  note messages_page c=16: host probe 1.101 after the window (noisy host)
  note room_show c=1: warm-up did not settle (reached the maximum)
  note room_show c=1: host probe 1.281 after the window (noisy host)
  note room_show c=16: host probe 1.253 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
