onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-climb/r3-cached against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 152,856 [144,689-157,028] | 40,422 | **3.781x** | 28,623 | **5.340x** | 22.0 [21-24] | 93.6 | 122.4 |
| room page | 1 | 22,144 [3,253-24,375] | 7,617 | **2.907x** | 6,481 | **3.417x** | 22.6 [21-115] | 208.7 | 142.1 |
| messages page | 16 | 125,689 [110,322-180,418] | 37,836 | **3.322x** | 30,063 | **4.181x** | 23.2 [17-25] | 102.2 | 114.2 |
| messages page | 1 | 21,188 [6,528-22,422] | 8,312 | **2.549x** | 6,822 | **3.106x** | 23.2 [22-72] | 199.3 | 139.2 |
| sidebar | 16 | 159,952 [24,001-185,408] | 37,555 | **4.259x** | 28,238 | **5.664x** | 20.4 [16-69] | 101.8 | 123.2 |
| sidebar | 1 | 23,011 [3,905-27,785] | 8,000 | **2.876x** | 6,196 | **3.714x** | 21.1 [18-106] | 181.0 | 149.0 |
| search | 16 | 150,571 [131,973-163,353] | 34,070 | **4.420x** | 26,606 | **5.659x** | 21.4 [20-22] | 107.3 | 123.9 |
| search | 1 | 15,570 [2,956-16,470] | 6,055 | **2.571x** | 5,646 | **2.758x** | 31.8 [30-162] | 315.1 | 158.3 |
| post a message | 16 | 12,371 [8,011-12,846] | 8,905 | **1.389x** | 7,174 | **1.724x** | 210.5 [185-303] | 353.0 | 385.6 |
| post a message | 1 | 3,257 [962-4,414] | 3,052 | **1.067x** | 2,779 | **1.172x** | 360.4 [295-1,203] | 629.1 | 403.7 |

Checks:
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note messages_page c=1: host probe 1.192 after the window (noisy host)
  note messages_page c=16: host probe 1.185 after the window (noisy host)
  note messages_page c=16: warm-up did not settle (reached the maximum)
  note messages_page c=16: host probe 2.43 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: host probe 1.152 after the window (noisy host)
  note post_message c=1: host probe 1.109 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: host probe 1.144 after the window (noisy host)
  note post_message c=16: host probe 2.218 after the window (noisy host)
  note room_show c=1: warm-up did not settle (reached the maximum)
  note room_show c=1: warm-up did not settle (reached the maximum)
  note room_show c=1: host probe 1.668 after the window (noisy host)
  note room_show c=16: host probe 1.111 after the window (noisy host)
  note search c=1: warm-up did not settle (reached the maximum)
  note search c=1: host probe 1.148 after the window (noisy host)
  note search c=1: warm-up did not settle (reached the maximum)
  note search c=1: host probe 1.501 after the window (noisy host)
  note search c=1: warm-up did not settle (reached the maximum)
  note search c=16: warm-up did not settle (reached the maximum)
  note search c=16: host probe 1.116 after the window (noisy host)
  note search c=16: host probe 1.183 after the window (noisy host)
  note search c=16: warm-up did not settle (reached the maximum)
  note search c=16: host probe 1.102 after the window (noisy host)
  note sidebar c=1: warm-up did not settle (reached the maximum)
  note sidebar c=1: warm-up did not settle (reached the maximum)
  note sidebar c=1: host probe 1.406 after the window (noisy host)
  note sidebar c=16: warm-up did not settle (reached the maximum)
  note sidebar c=16: host probe 4.555 after the window (noisy host)
  note sidebar c=16: host probe 1.935 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
