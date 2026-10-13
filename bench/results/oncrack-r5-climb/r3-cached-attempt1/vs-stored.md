onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-climb/r3-cached against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 122,941 [10,609-155,775] | 40,422 | **3.041x** | 28,623 | **4.295x** | 24.1 [19-165] | 93.6 | 122.4 |
| room page | 1 | 6,777 [683-22,593] | 7,617 | **0.890x** | 6,481 | **1.046x** | 65.1 [22-568] | 208.7 | 142.1 |
| messages page | 16 | 154,179 [77,492-154,626] | 37,836 | **4.075x** | 30,063 | **5.129x** | 22.0 [22-31] | 102.2 | 114.2 |
| messages page | 1 | 18,415 [4,868-23,646] | 8,312 | **2.216x** | 6,822 | **2.699x** | 27.8 [21-102] | 199.3 | 139.2 |
| sidebar | 16 | 133,333 [121,358-170,948] | 37,555 | **3.550x** | 28,238 | **4.722x** | 20.4 [19-23] | 101.8 | 123.2 |
| sidebar | 1 | 25,333 [706-27,280] | 8,000 | **3.167x** | 6,196 | **4.088x** | 19.2 [18-594] | 181.0 | 149.0 |
| search | 16 | 166,477 [128,797-169,291] | 34,070 | **4.886x** | 26,606 | **6.257x** | 19.5 [19-23] | 107.3 | 123.9 |
| search | 1 | 3,328 [2,128-23,548] | 6,055 | **0.550x** | 5,646 | **0.590x** | 122.8 [21-204] | 315.1 | 158.3 |
| post a message | 16 | 6,011 [5,585-7,261] | 8,905 | **0.675x** | 7,174 | **0.838x** | 293.7 [259-497] | 353.0 | 385.6 |
| post a message | 1 | 1,627 [1,071-2,227] | 3,052 | **0.533x** | 2,779 | **0.585x** | 463.0 [373-1,073] | 629.1 | 403.7 |

Checks:
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note messages_page c=1: host probe 1.11 after the window (noisy host)
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note messages_page c=1: host probe 4.665 after the window (noisy host)
  note messages_page c=16: warm-up did not settle (reached the maximum)
  note messages_page c=16: host probe 1.164 after the window (noisy host)
  note messages_page c=16: host probe 1.107 after the window (noisy host)
  note messages_page c=16: warm-up did not settle (reached the maximum)
  note messages_page c=16: host probe 1.738 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: host probe 1.141 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: host probe 1.158 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: host probe 1.812 after the window (noisy host)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: host probe 1.126 after the window (noisy host)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: host probe 1.242 after the window (noisy host)
  note post_message c=16: host probe 1.792 after the window (noisy host)
  note room_show c=1: warm-up did not settle (reached the maximum)
  note room_show c=1: host probe 1.568 after the window (noisy host)
  note room_show c=1: warm-up did not settle (reached the maximum)
  note room_show c=1: host probe 8.215 after the window (noisy host)
  note room_show c=16: host probe 1.192 after the window (noisy host)
  note room_show c=16: warm-up did not settle (reached the maximum)
  note room_show c=16: host probe 2.034 after the window (noisy host)
  note search c=1: warm-up did not settle (reached the maximum)
  note search c=1: host probe 1.356 after the window (noisy host)
  note search c=1: warm-up did not settle (reached the maximum)
  note search c=1: warm-up did not settle (reached the maximum)
  note search c=1: host probe 3.254 after the window (noisy host)
  note search c=16: host probe 1.939 after the window (noisy host)
  note sidebar c=1: host probe 1.135 after the window (noisy host)
  note sidebar c=1: warm-up did not settle (reached the maximum)
  note sidebar c=1: host probe 1.954 after the window (noisy host)
  note sidebar c=16: host probe 1.242 after the window (noisy host)
  note sidebar c=16: warm-up did not settle (reached the maximum)
  note sidebar c=16: host probe 1.105 after the window (noisy host)
  note sidebar c=16: warm-up did not settle (reached the maximum)
  note sidebar c=16: host probe 1.606 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
