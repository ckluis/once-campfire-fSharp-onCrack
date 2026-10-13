### Validation, every cable phase of the session

| app | phases | all clients subscribed | every posted message reached every client (paced and saturated) | failed connects | closed mid-run | window stalls |
|---|---|---|---|---|---|---|
| Rust f9dca47 | 16 | 16/16 | 16/16 | 0 | 0 | 0 |
| F# port | 16 | 16/16 | 16/16 | 0 | 0 | 0 |
| onCrack | 16 | 16/16 | 15/16 | 0 | 0 | 1 |

### Delivered messages per second (each message to every client), median of 3 and the reps in run order

| clients | Rust | F# port | **onCrack** | **onCrack / Rust** | **onCrack / port** | port / Rust | reps in run order (Rust / port / onCrack) |
|---|---|---|---|---|---|---|---|
| 100 | 3,610 [3,040-4,257] | 2,884 [2,337-3,289] | **5,726** [5,507-6,424] | **1.59x** | **1.99x** | 0.80x | 4,257,3,610,3,040 / 2,337,2,884,3,289 / 5,726,5,507,6,424 |
| 500 | 2,089 [1,748-2,451] | 780 [764-871] | **2,595** [2,316-2,983] | **1.24x** | **3.33x** | 0.37x | 2,451,2,089,1,748 / 871,780,764 / 2,316,2,595,2,983 |
| 1,000 | 1,293 [1,277-1,430] | 364 [340-464] | **1,500** [1,464-1,596] | **1.16x** | **4.12x** | 0.28x | 1,277,1,430,1,293 / 464,364,340 / 1,596,1,500,1,464 |
| 2,000 | 875 [769-886] | 144 [138-152] | **819** [686-875] | **0.94x** | **5.69x** | 0.16x | 886,875,769 / 152,138,144 / 686,819,875 |

### Server CPU per delivery and cores (the container's cpu.stat over the saturated phase, divided by messages x clients), the load generator's cores
(of 4), sends per delivery (send, sendmsg, write syscalls of the app over 3 s of the saturated phase / deliveries), the app's Pss with every client
subscribed and idle and saturated (MB), and the paced latency of a post to the last client / to a client (ms, p50 / p99). Medians of 3.

| clients | | Rust | F# port | onCrack | onCrack / Rust |
|---|---|---|---|---|---|
| 100 | server CPU us / delivery | 8.26 | 10.81 | 5.19 | 0.63x |
| 100 | server cores busy | 3.01 | 3.07 | 2.98 | 0.99x |
| 100 | load generator cores busy | 1.41 | 1.27 | 1.49 | 1.06x |
| 100 | load generator CPU us / delivery | 3.89 | 4.39 | 2.60 | 0.67x |
| 100 | sends / delivery | 0.592 | 0.636 | 0.328 | 0.55x |
| 100 | Pss idle (MB) | 39 | 111 | 114 | 2.94x |
| 100 | Pss saturated (MB) | 99 | 279 | 274 | 2.76x |
| 100 | paced post -> last client p50 / p99 | 1.6 / 2.7 | 2.9 / 20.4 | 3.3 / 13.0 | 2.10x |
| 100 | paced post -> a client p50 / p99 | 1.4 / 2.6 | 2.6 / 18.6 | 3.0 / 12.9 | 2.11x |
| 100 | saturated post -> last client p50 / p99 | 1.2 / 5.2 | 1.4 / 4.6 | 1.1 / 4.7 | 0.89x |
| 500 | server CPU us / delivery | 3.47 | 9.62 | 2.77 | 0.80x |
| 500 | server cores busy | 3.56 | 3.79 | 3.59 | 1.01x |
| 500 | load generator cores busy | 2.42 | 1.50 | 2.63 | 1.09x |
| 500 | load generator CPU us / delivery | 2.32 | 3.86 | 2.03 | 0.88x |
| 500 | sends / delivery | 0.188 | 0.431 | 0.159 | 0.84x |
| 500 | Pss idle (MB) | 103 | 279 | 271 | 2.63x |
| 500 | Pss saturated (MB) | 104 | 528 | 284 | 2.72x |
| 500 | paced post -> last client p50 / p99 | 3.4 / 5.5 | 3.9 / 8.2 | 3.3 / 5.2 | 0.97x |
| 500 | paced post -> a client p50 / p99 | 2.4 / 4.2 | 2.8 / 7.0 | 2.6 / 4.9 | 1.06x |
| 500 | saturated post -> last client p50 / p99 | 6.8 / 21.9 | 8.0 / 26.8 | 6.9 / 23.5 | 1.03x |
| 1,000 | server CPU us / delivery | 2.73 | 10.64 | 2.51 | 0.92x |
| 1,000 | server cores busy | 3.80 | 3.84 | 3.80 | 1.00x |
| 1,000 | load generator cores busy | 2.63 | 1.38 | 2.82 | 1.07x |
| 1,000 | load generator CPU us / delivery | 2.04 | 3.80 | 1.88 | 0.92x |
| 1,000 | sends / delivery | 0.080 | 0.383 | 0.105 | 1.31x |
| 1,000 | Pss idle (MB) | 111 | 528 | 281 | 2.53x |
| 1,000 | Pss saturated (MB) | 113 | 661 | 307 | 2.73x |
| 1,000 | paced post -> last client p50 / p99 | 5.5 / 7.5 | 7.3 / 10.8 | 5.2 / 14.8 | 0.93x |
| 1,000 | paced post -> a client p50 / p99 | 3.5 / 6.8 | 4.8 / 8.9 | 3.6 / 13.3 | 1.02x |
| 1,000 | saturated post -> last client p50 / p99 | 23.7 / 69.6 | 21.6 / 78.1 | 26.5 / 81.3 | 1.12x |
| 2,000 | server CPU us / delivery | 2.23 | 13.38 | 2.35 | 1.05x |
| 2,000 | server cores busy | 3.89 | 3.86 | 3.80 | 0.98x |
| 2,000 | load generator cores busy | 2.75 | 1.18 | 2.82 | 1.02x |
| 2,000 | load generator CPU us / delivery | 1.57 | 4.11 | 1.72 | 1.09x |
| 2,000 | sends / delivery | 0.042 | 0.357 | 0.104 | 2.50x |
| 2,000 | Pss idle (MB) | 125 | 730 | 302 | 2.42x |
| 2,000 | Pss saturated (MB) | 132 | 909 | 368 | 2.77x |
| 2,000 | paced post -> last client p50 / p99 | 9.1 / 12.8 | 13.9 / 27.4 | 7.7 / 25.9 | 0.85x |
| 2,000 | paced post -> a client p50 / p99 | 5.4 / 10.8 | 8.6 / 20.6 | 5.1 / 24.6 | 0.94x |
| 2,000 | saturated post -> last client p50 / p99 | 115.7 / 219.8 | 57.7 / 312.1 | 75.4 / 184.8 | 0.65x |
