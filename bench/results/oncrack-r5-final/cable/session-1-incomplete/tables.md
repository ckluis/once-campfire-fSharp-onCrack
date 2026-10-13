### Validation, every cable phase of the session

| app | phases | all clients subscribed | every posted message reached every client (paced and saturated) | failed connects | closed mid-run | window stalls |
|---|---|---|---|---|---|---|
| Rust f9dca47 | 12 | 12/12 | 12/12 | 0 | 0 | 4 |
| F# port | 16 | 16/16 | 16/16 | 0 | 0 | 0 |
| onCrack | 16 | 16/16 | 16/16 | 0 | 0 | 0 |

### Delivered messages per second (each message to every client), median of 3 and the reps in run order

| clients | Rust | F# port | **onCrack** | **onCrack / Rust** | **onCrack / port** | port / Rust | reps in run order (Rust / port / onCrack) |
|---|---|---|---|---|---|---|---|
| 100 | 3,087 [2,444-3,730] | 1,818 [702-3,330] | **4,409** [4,019-6,066] | **1.43x** | **2.43x** | 0.59x | 3,730,2,444 / 3,330,702,1,818 / 6,066,4,409,4,019 |
| 500 | 1,442 [825-2,059] | 324 [226-808] | **1,589** [739-2,674] | **1.10x** | **4.90x** | 0.22x | 2,059,825 / 808,226,324 / 1,589,2,674,739 |
| 1,000 | 448 [100-796] | 198 [70-378] | **1,407** [226-1,709] | **3.14x** | **7.12x** | 0.44x | 796,100 / 378,198,70 / 1,407,1,709,226 |
| 2,000 | 338 [282-393] | 74 [72-207] | **826** [400-903] | **2.45x** | **11.13x** | 0.22x | 282,393 / 207,72,74 / 826,903,400 |

### Server CPU per delivery and cores (the container's cpu.stat over the saturated phase, divided by messages x clients), the load generator's cores
(of 4), sends per delivery (send, sendmsg, write syscalls of the app over 3 s of the saturated phase / deliveries), the app's Pss with every client
subscribed and idle and saturated (MB), and the paced latency of a post to the last client / to a client (ms, p50 / p99). Medians of 3.

| clients | | Rust | F# port | onCrack | onCrack / Rust |
|---|---|---|---|---|---|
| 100 | server CPU us / delivery | 9.92 | 15.74 | 5.70 | 0.57x |
| 100 | server cores busy | 2.97 | 2.77 | 3.01 | 1.01x |
| 100 | load generator cores busy | 1.24 | 0.91 | 1.19 | 0.96x |
| 100 | load generator CPU us / delivery | 4.01 | 4.99 | 2.70 | 0.67x |
| 100 | sends / delivery | 0.636 | 0.648 | 0.303 | 0.48x |
| 100 | Pss idle (MB) | 39 | 111 | 114 | 2.94x |
| 100 | Pss saturated (MB) | 99 | 279 | 275 | 2.78x |
| 100 | paced post -> last client p50 / p99 | 1.3 / 3.2 | 2.9 / 10.7 | 2.8 / 10.5 | 2.06x |
| 100 | paced post -> a client p50 / p99 | 1.1 / 3.1 | 2.6 / 10.4 | 2.6 / 10.4 | 2.32x |
| 100 | saturated post -> last client p50 / p99 | 1.5 / 4.8 | 2.0 / 10.4 | 1.2 / 5.0 | 0.81x |
| 500 | server CPU us / delivery | 5.73 | 21.63 | 4.25 | 0.74x |
| 500 | server cores busy | 3.43 | 3.56 | 3.39 | 0.99x |
| 500 | load generator cores busy | 1.87 | 0.90 | 1.99 | 1.06x |
| 500 | load generator CPU us / delivery | 2.59 | 5.53 | 2.50 | 0.97x |
| 500 | sends / delivery | 0.040 | 0.412 | 0.160 | 3.99x |
| 500 | Pss idle (MB) | 103 | 280 | 273 | 2.65x |
| 500 | Pss saturated (MB) | 105 | 530 | 284 | 2.71x |
| 500 | paced post -> last client p50 / p99 | 2.8 / 3.8 | 5.7 / 28.2 | 2.7 / 19.1 | 0.99x |
| 500 | paced post -> a client p50 / p99 | 1.9 / 3.3 | 4.5 / 15.8 | 2.3 / 18.7 | 1.24x |
| 500 | saturated post -> last client p50 / p99 | 8.5 / 71.0 | 11.6 / 174.8 | 7.2 / 71.1 | 0.84x |
| 1,000 | server CPU us / delivery | 18.20 | 18.09 | 2.67 | 0.15x |
| 1,000 | server cores busy | 3.33 | 3.59 | 3.75 | 1.13x |
| 1,000 | load generator cores busy | 1.53 | 0.92 | 2.67 | 1.74x |
| 1,000 | load generator CPU us / delivery | 3.42 | 4.67 | 1.90 | 0.56x |
| 1,000 | sends / delivery | 0.268 | 0.359 | 0.101 | 0.38x |
| 1,000 | Pss idle (MB) | 110 | 524 | 282 | 2.58x |
| 1,000 | Pss saturated (MB) | 112 | 684 | 311 | 2.77x |
| 1,000 | paced post -> last client p50 / p99 | 7.3 / 266.2 | 16.4 / 90.1 | 4.5 / 8.3 | 0.62x |
| 1,000 | paced post -> a client p50 / p99 | 5.4 / 263.7 | 9.3 / 74.9 | 3.3 / 7.9 | 0.60x |
| 1,000 | saturated post -> last client p50 / p99 | 75.4 / 3120.4 | 31.8 / 415.2 | 27.1 / 80.6 | 0.36x |
| 2,000 | server CPU us / delivery | 5.38 | 24.93 | 2.33 | 0.43x |
| 2,000 | server cores busy | 3.58 | 3.71 | 3.82 | 1.07x |
| 2,000 | load generator cores busy | 2.01 | 0.88 | 2.87 | 1.42x |
| 2,000 | load generator CPU us / delivery | 2.98 | 5.92 | 1.74 | 0.58x |
| 2,000 | sends / delivery | 0.089 | 0.317 | 0.095 | 1.07x |
| 2,000 | Pss idle (MB) | 126 | 725 | 328 | 2.62x |
| 2,000 | Pss saturated (MB) | 131 | 942 | 388 | 2.96x |
| 2,000 | paced post -> last client p50 / p99 | 22.2 / 367.5 | 17.1 / 146.9 | 6.6 / 71.2 | 0.30x |
| 2,000 | paced post -> a client p50 / p99 | 13.4 / 265.7 | 11.6 / 106.0 | 4.5 / 69.6 | 0.34x |
| 2,000 | saturated post -> last client p50 / p99 | 148.3 / 3597.3 | 88.2 / 787.5 | 73.2 / 165.6 | 0.49x |
