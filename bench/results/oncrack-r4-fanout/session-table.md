### Validation, every cable phase of the session

| app | phases | all clients subscribed | every posted message reached every client (paced and saturated) | failed connects | closed mid-run | window stalls |
|---|---|---|---|---|---|---|
| Rust f9dca47 | 16 | 16/16 | 16/16 | 0 | 0 | 0 |
| F# port | 16 | 16/16 | 16/16 | 0 | 0 | 0 |
| onCrack | 16 | 16/16 | 16/16 | 0 | 0 | 0 |

### Delivered messages per second (each message to every client), median of 3 and the reps in run order

| clients | Rust | F# port | **onCrack** | **onCrack / Rust** | **onCrack / port** | port / Rust | reps in run order (Rust / port / onCrack) |
|---|---|---|---|---|---|---|---|
| 100 | 2,302 [2,134-2,314] | 1,747 [1,602-3,091] | **4,244** [4,217-6,799] | **1.84x** | **2.43x** | 0.76x | 2,314,2,134,2,302 / 1,747,3,091,1,602 / 6,799,4,217,4,244 |
| 500 | 1,512 [1,418-1,681] | 868 [512-988] | **2,038** [1,625-2,219] | **1.35x** | **2.35x** | 0.57x | 1,418,1,681,1,512 / 988,868,512 / 2,038,2,219,1,625 |
| 1,000 | 1,040 [952-1,154] | 363 [254-462] | **1,214** [948-1,298] | **1.17x** | **3.35x** | 0.35x | 952,1,154,1,040 / 462,363,254 / 1,298,1,214,948 |
| 2,000 | 546 [499-566] | 163 [128-211] | **623** [457-700] | **1.14x** | **3.82x** | 0.30x | 546,499,566 / 211,163,128 / 623,700,457 |

### Server CPU per delivery and cores (the container's cpu.stat over the saturated phase, divided by messages x clients), the load generator's cores
(of 4), sends per delivery (send, sendmsg, write syscalls of the app over 3 s of the saturated phase / deliveries), the app's Pss with every client
subscribed and idle and saturated (MB), and the paced latency of a post to the last client / to a client (ms, p50 / p99). Medians of 3.

| clients | | Rust | F# port | onCrack | onCrack / Rust |
|---|---|---|---|---|---|
| 100 | server CPU us / delivery | 13.94 | 19.07 | 7.43 | 0.53x |
| 100 | server cores busy | 3.14 | 3.32 | 3.19 | 1.02x |
| 100 | load generator cores busy | 1.27 | 1.10 | 1.39 | 1.09x |
| 100 | load generator CPU us / delivery | 5.53 | 6.31 | 3.27 | 0.59x |
| 100 | sends / delivery | 0.603 | 0.259 | 0.202 | 0.34x |
| 100 | Pss idle (MB) | 39 | 111 | 115 | 2.96x |
| 100 | Pss saturated (MB) | 97 | 275 | 264 | 2.72x |
| 100 | paced post -> last client p50 / p99 | 3.1 / 4.5 | 4.9 / 20.7 | 5.4 / 14.2 | 1.73x |
| 100 | paced post -> a client p50 / p99 | 2.8 / 4.2 | 4.5 / 20.5 | 4.9 / 14.0 | 1.79x |
| 100 | saturated post -> last client p50 / p99 | 2.1 / 6.6 | 2.3 / 6.9 | 1.4 / 5.4 | 0.66x |
| 500 | server CPU us / delivery | 4.99 | 8.63 | 3.32 | 0.67x |
| 500 | server cores busy | 3.59 | 3.77 | 3.69 | 1.03x |
| 500 | load generator cores busy | 2.17 | 1.64 | 2.22 | 1.02x |
| 500 | load generator CPU us / delivery | 2.87 | 3.78 | 2.17 | 0.76x |
| 500 | sends / delivery | 0.110 | 0.438 | 0.114 | 1.04x |
| 500 | Pss idle (MB) | 102 | 276 | 261 | 2.55x |
| 500 | Pss saturated (MB) | 106 | 505 | 275 | 2.59x |
| 500 | paced post -> last client p50 / p99 | 6.6 / 9.5 | 8.0 / 14.9 | 6.3 / 25.3 | 0.95x |
| 500 | paced post -> a client p50 / p99 | 4.5 / 7.9 | 5.7 / 14.5 | 4.9 / 24.6 | 1.09x |
| 500 | saturated post -> last client p50 / p99 | 8.8 / 39.1 | 6.8 / 21.8 | 10.1 / 44.7 | 1.15x |
| 1,000 | server CPU us / delivery | 3.77 | 10.65 | 3.14 | 0.83x |
| 1,000 | server cores busy | 3.89 | 3.86 | 3.77 | 0.97x |
| 1,000 | load generator cores busy | 2.29 | 1.41 | 2.62 | 1.14x |
| 1,000 | load generator CPU us / delivery | 2.20 | 3.88 | 2.15 | 0.98x |
| 1,000 | sends / delivery | 0.043 | 0.169 | 0.080 | 1.84x |
| 1,000 | Pss idle (MB) | 110 | 490 | 273 | 2.48x |
| 1,000 | Pss saturated (MB) | 114 | 658 | 296 | 2.60x |
| 1,000 | paced post -> last client p50 / p99 | 9.9 / 15.0 | 12.7 / 20.6 | 9.0 / 15.3 | 0.91x |
| 1,000 | paced post -> a client p50 / p99 | 5.6 / 12.6 | 7.6 / 16.8 | 6.0 / 13.1 | 1.07x |
| 1,000 | saturated post -> last client p50 / p99 | 73.7 / 178.9 | 20.2 / 79.9 | 41.2 / 119.2 | 0.56x |
| 2,000 | server CPU us / delivery | 3.59 | 11.97 | 3.04 | 0.85x |
| 2,000 | server cores busy | 3.89 | 3.88 | 3.81 | 0.98x |
| 2,000 | load generator cores busy | 2.35 | 1.22 | 2.62 | 1.12x |
| 2,000 | load generator CPU us / delivery | 2.15 | 3.73 | 2.11 | 0.98x |
| 2,000 | sends / delivery | 0.043 | 0.175 | 0.062 | 1.45x |
| 2,000 | Pss idle (MB) | 125 | 725 | 300 | 2.40x |
| 2,000 | Pss saturated (MB) | 132 | 945 | 350 | 2.65x |
| 2,000 | paced post -> last client p50 / p99 | 15.9 / 23.2 | 20.7 / 29.5 | 13.8 / 20.0 | 0.87x |
| 2,000 | paced post -> a client p50 / p99 | 7.7 / 19.4 | 13.7 / 27.0 | 7.7 / 18.0 | 0.99x |
| 2,000 | saturated post -> last client p50 / p99 | 195.1 / 481.3 | 61.0 / 224.3 | 109.1 / 386.0 | 0.56x |
