### Validation, every cable phase of the session

| app | phases | all clients subscribed | every posted message reached every client (paced and saturated) | failed connects | closed mid-run | window stalls |
|---|---|---|---|---|---|---|
| Rust f9dca47 | 16 | 16/16 | 16/16 | 0 | 0 | 0 |
| F# port | 16 | 16/16 | 16/16 | 0 | 0 | 0 |
| onCrack | 16 | 16/16 | 16/16 | 0 | 0 | 0 |

### Delivered messages per second (each message to every client), median of 3 and the reps in run order

| clients | Rust | F# port | **onCrack** | **onCrack / Rust** | **onCrack / port** | port / Rust | reps in run order (Rust / port / onCrack) |
|---|---|---|---|---|---|---|---|
| 100 | 3,256 [2,362-3,298] | 1,265 [825-2,127] | **4,124** [3,874-4,610] | **1.27x** | **3.26x** | 0.39x | 2,362,3,298,3,256 / 825,2,127,1,265 / 4,610,4,124,3,874 |
| 500 | 1,500 [1,196-2,166] | 191 [147-412] | **2,163** [1,093-2,173] | **1.44x** | **11.33x** | 0.13x | 1,196,2,166,1,500 / 147,191,412 / 2,173,1,093,2,163 |
| 1,000 | 1,212 [291-1,498] | 153 [146-354] | **550** [362-1,460] | **0.45x** | **3.58x** | 0.13x | 291,1,498,1,212 / 153,146,354 / 550,362,1,460 |
| 2,000 | 752 [484-841] | 47 [20-189] | **268** [36-756] | **0.36x** | **5.71x** | 0.06x | 484,752,841 / 47,20,189 / 36,268,756 |

### Server CPU per delivery and cores (the container's cpu.stat over the saturated phase, divided by messages x clients), the load generator's cores
(of 4), sends per delivery (send, sendmsg, write syscalls of the app over 3 s of the saturated phase / deliveries), the app's Pss with every client
subscribed and idle and saturated (MB), and the paced latency of a post to the last client / to a client (ms, p50 / p99). Medians of 3.

| clients | | Rust | F# port | onCrack | onCrack / Rust |
|---|---|---|---|---|---|
| 100 | server CPU us / delivery | 9.17 | 22.75 | 7.27 | 0.79x |
| 100 | server cores busy | 3.00 | 2.88 | 3.00 | 1.00x |
| 100 | load generator cores busy | 1.31 | 0.69 | 1.17 | 0.89x |
| 100 | load generator CPU us / delivery | 4.03 | 5.43 | 2.83 | 0.70x |
| 100 | sends / delivery | 0.630 | 0.628 | 0.364 | 0.58x |
| 100 | Pss idle (MB) | 39 | 111 | 114 | 2.93x |
| 100 | Pss saturated (MB) | 98 | 282 | 273 | 2.77x |
| 100 | paced post -> last client p50 / p99 | 1.3 / 2.0 | 2.4 / 10.4 | 2.4 / 9.5 | 1.86x |
| 100 | paced post -> a client p50 / p99 | 1.1 / 1.8 | 2.1 / 9.2 | 2.2 / 9.3 | 2.04x |
| 100 | saturated post -> last client p50 / p99 | 1.4 / 5.5 | 2.2 / 46.8 | 1.5 / 5.8 | 1.02x |
| 500 | server CPU us / delivery | 3.38 | 35.53 | 3.21 | 0.95x |
| 500 | server cores busy | 3.36 | 3.41 | 3.33 | 0.99x |
| 500 | load generator cores busy | 1.67 | 0.81 | 2.26 | 1.35x |
| 500 | load generator CPU us / delivery | 2.22 | 8.46 | 2.09 | 0.94x |
| 500 | sends / delivery | 0.189 | 0.755 | 0.172 | 0.91x |
| 500 | Pss idle (MB) | 102 | 284 | 272 | 2.65x |
| 500 | Pss saturated (MB) | 104 | 505 | 283 | 2.73x |
| 500 | paced post -> last client p50 / p99 | 2.5 / 7.9 | 3.3 / 11.9 | 2.8 / 21.6 | 1.09x |
| 500 | paced post -> a client p50 / p99 | 1.9 / 6.6 | 2.3 / 9.5 | 2.2 / 21.2 | 1.16x |
| 500 | saturated post -> last client p50 / p99 | 7.5 / 26.9 | 12.0 / 417.8 | 7.3 / 28.3 | 0.97x |
| 1,000 | server CPU us / delivery | 2.94 | 23.97 | 6.49 | 2.21x |
| 1,000 | server cores busy | 3.56 | 3.69 | 3.60 | 1.01x |
| 1,000 | load generator cores busy | 2.37 | 0.89 | 1.62 | 0.69x |
| 1,000 | load generator CPU us / delivery | 1.95 | 5.81 | 2.95 | 1.51x |
| 1,000 | sends / delivery | 0.095 | 0.682 | 0.110 | 1.16x |
| 1,000 | Pss idle (MB) | 110 | 513 | 280 | 2.54x |
| 1,000 | Pss saturated (MB) | 113 | 635 | 298 | 2.63x |
| 1,000 | paced post -> last client p50 / p99 | 6.0 / 8.9 | 14.6 / 146.3 | 6.1 / 30.7 | 1.02x |
| 1,000 | paced post -> a client p50 / p99 | 4.0 / 7.8 | 9.9 / 110.5 | 5.0 / 28.5 | 1.25x |
| 1,000 | saturated post -> last client p50 / p99 | 25.7 / 83.6 | 28.1 / 364.0 | 25.8 / 693.8 | 1.00x |
| 2,000 | server CPU us / delivery | 2.44 | 38.35 | 6.81 | 2.79x |
| 2,000 | server cores busy | 3.74 | 3.65 | 3.65 | 0.98x |
| 2,000 | load generator cores busy | 2.54 | 0.76 | 1.69 | 0.66x |
| 2,000 | load generator CPU us / delivery | 1.69 | 8.11 | 3.14 | 1.86x |
| 2,000 | sends / delivery | 0.088 | 0.429 | 0.091 | 1.02x |
| 2,000 | Pss idle (MB) | 126 | 634 | 303 | 2.41x |
| 2,000 | Pss saturated (MB) | 132 | 867 | 323 | 2.44x |
| 2,000 | paced post -> last client p50 / p99 | 8.4 / 24.1 | 17.5 / 166.3 | 29.8 / 1024.5 | 3.56x |
| 2,000 | paced post -> a client p50 / p99 | 5.3 / 23.0 | 11.3 / 119.2 | 20.3 / 842.2 | 3.80x |
| 2,000 | saturated post -> last client p50 / p99 | 127.7 / 350.0 | 94.0 / 939.5 | 119.6 / 1631.2 | 0.94x |
