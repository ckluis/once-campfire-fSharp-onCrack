onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r4-fresh/t3/1-hold against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 126,162 | 40,422 | **3.121x** | 28,623 | **4.408x** | 25.1 | 93.6 | 122.4 |
| room page | 1 | 15,279 | 7,617 | **2.006x** | 6,481 | **2.358x** | 31.9 | 208.7 | 142.1 |
| messages page | 16 | 156,207 | 37,836 | **4.128x** | 30,063 | **5.196x** | 20.3 | 102.2 | 114.2 |
| messages page | 1 | 17,977 | 8,312 | **2.163x** | 6,822 | **2.635x** | 27.4 | 199.3 | 139.2 |

Checks:
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note room_show c=1: warm-up did not settle (reached the maximum)
  note room_show c=1: host probe 1.264 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 4 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
