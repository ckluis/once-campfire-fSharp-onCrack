onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-climb/r5-cached against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 98,740 [37,756-139,056] | 40,422 | **2.443x** | 28,623 | **3.450x** | 26.8 [25-45] | 93.6 | 122.4 |
| room page | 1 | 15,964 [14,611-23,366] | 7,617 | **2.096x** | 6,481 | **2.463x** | 30.2 [22-35] | 208.7 | 142.1 |
| messages page | 16 | 156,956 [126,638-160,063] | 37,836 | **4.148x** | 30,063 | **5.221x** | 21.4 [20-24] | 102.2 | 114.2 |
| messages page | 1 | 22,846 [22,743-24,516] | 8,312 | **2.749x** | 6,822 | **3.349x** | 21.8 [20-22] | 199.3 | 139.2 |
| sidebar | 16 | 176,224 [132,057-177,347] | 37,555 | **4.692x** | 28,238 | **6.241x** | 18.8 [17-22] | 101.8 | 123.2 |
| sidebar | 1 | 23,668 [3,280-30,859] | 8,000 | **2.959x** | 6,196 | **3.820x** | 19.7 [16-126] | 181.0 | 149.0 |
| search | 16 | 181,946 [157,925-190,599] | 34,070 | **5.340x** | 26,606 | **6.839x** | 17.0 [16-21] | 107.3 | 123.9 |
| search | 1 | 22,871 [7,250-22,972] | 6,055 | **3.777x** | 5,646 | **4.051x** | 21.4 [20-66] | 315.1 | 158.3 |
| post a message | 16 | 8,912 [7,089-11,928] | 8,905 | **1.001x** | 7,174 | **1.242x** | 212.5 [209-407] | 353.0 | 385.6 |
| post a message | 1 | 2,060 [499-2,309] | 3,052 | **0.675x** | 2,779 | **0.741x** | 435.1 [303-2,041] | 629.1 | 403.7 |

Checks:
  note messages_page c=1: host probe 1.101 after the window (noisy host)
  note messages_page c=1: host probe 1.104 after the window (noisy host)
  note messages_page c=16: host probe 2.094 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: host probe 2.981 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: host probe 1.106 after the window (noisy host)
  note post_message c=1: warm-up did not settle (reached the maximum)
  note post_message c=1: host probe 2.197 after the window (noisy host)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: host probe 1.216 after the window (noisy host)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: host probe 1.111 after the window (noisy host)
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: host probe 2.393 after the window (noisy host)
  note room_show c=1: warm-up did not settle (reached the maximum)
  note room_show c=1: host probe 2.805 after the window (noisy host)
  note room_show c=1: warm-up did not settle (reached the maximum)
  note room_show c=1: host probe 1.113 after the window (noisy host)
  note room_show c=1: warm-up did not settle (reached the maximum)
  note room_show c=16: host probe 1.658 after the window (noisy host)
  note room_show c=16: warm-up did not settle (reached the maximum)
  note room_show c=16: host probe 3.301 after the window (noisy host)
  note room_show c=16: warm-up did not settle (reached the maximum)
  note room_show c=16: host probe 1.109 after the window (noisy host)
  note search c=1: warm-up did not settle (reached the maximum)
  note search c=1: host probe 1.394 after the window (noisy host)
  note search c=1: warm-up did not settle (reached the maximum)
  note search c=1: host probe 1.106 after the window (noisy host)
  note search c=16: warm-up did not settle (reached the maximum)
  note sidebar c=1: warm-up did not settle (reached the maximum)
  note sidebar c=1: host probe 1.487 after the window (noisy host)
  note sidebar c=1: host probe 1.113 after the window (noisy host)
  note sidebar c=16: warm-up did not settle (reached the maximum)
  note sidebar c=16: host probe 1.128 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
