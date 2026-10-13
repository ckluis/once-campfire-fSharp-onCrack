### Validation, every cable phase of the session

| app | phases | all clients subscribed | every posted message reached every client (paced and saturated) | failed connects | closed mid-run | window stalls |
|---|---|---|---|---|---|---|
| Rust f9dca47 | 16 | 16/16 | 16/16 | 0 | 0 | 0 |
| F# port | 16 | 16/16 | 16/16 | 0 | 0 | 0 |
| onCrack | 16 | 16/16 | 16/16 | 0 | 0 | 0 |

### Delivered messages per second (each message to every client), median of 3 and the reps in run order

| clients | Rust | F# port | **onCrack** | **onCrack / Rust** | **onCrack / port** | port / Rust | reps in run order (Rust / port / onCrack) |
|---|---|---|---|---|---|---|---|
| 100 | 4,155 [2,990-4,224] | 3,407 [2,975-3,617] | **6,859** [5,992-6,923] | **1.65x** | **2.01x** | 0.82x | 2,990,4,155,4,224 / 3,407,2,975,3,617 / 5,992,6,923,6,859 |
| 500 | 2,625 [2,564-2,758] | 995 [924-1,005] | **3,251** [3,149-3,287] | **1.24x** | **3.27x** | 0.38x | 2,758,2,625,2,564 / 924,995,1,005 / 3,149,3,287,3,251 |
| 1,000 | 1,706 [1,249-1,724] | 464 [322-469] | **1,995** [1,925-2,002] | **1.17x** | **4.30x** | 0.27x | 1,249,1,706,1,724 / 322,469,464 / 1,925,1,995,2,002 |
| 2,000 | 1,054 [789-1,054] | 211 [205-212] | **1,067** [970-1,069] | **1.01x** | **5.05x** | 0.20x | 789,1,054,1,054 / 205,211,212 / 970,1,067,1,069 |

### Server CPU per delivery and cores (the container's cpu.stat over the saturated phase, divided by messages x clients), the load generator's cores
(of 4), sends per delivery (send, sendmsg, write syscalls of the app over 3 s of the saturated phase / deliveries), the app's Pss with every client
subscribed and idle and saturated (MB), and the paced latency of a post to the last client / to a client (ms, p50 / p99). Medians of 3.

| clients | | Rust | F# port | onCrack | onCrack / Rust |
|---|---|---|---|---|---|
| 100 | server CPU us / delivery | 7.17 | 8.58 | 4.44 | 0.62x |
| 100 | server cores busy | 2.96 | 2.99 | 2.99 | 1.01x |
| 100 | load generator cores busy | 1.43 | 1.30 | 1.58 | 1.10x |
| 100 | load generator CPU us / delivery | 3.45 | 3.82 | 2.30 | 0.67x |
| 100 | sends / delivery | 0.622 | 0.641 | 0.330 | 0.53x |
| 100 | Pss idle (MB) | 39 | 111 | 113 | 2.92x |
| 100 | Pss saturated (MB) | 100 | 280 | 272 | 2.72x |
| 100 | paced post -> last client p50 / p99 | 3.3 / 4.6 | 5.0 / 15.5 | 5.2 / 15.2 | 1.55x |
| 100 | paced post -> a client p50 / p99 | 2.9 / 4.4 | 4.3 / 15.3 | 4.8 / 15.0 | 1.62x |
| 100 | saturated post -> last client p50 / p99 | 1.1 / 4.7 | 1.2 / 3.5 | 1.0 / 3.7 | 0.84x |
| 500 | server CPU us / delivery | 2.74 | 7.59 | 2.21 | 0.81x |
| 500 | server cores busy | 3.59 | 3.74 | 3.55 | 0.99x |
| 500 | load generator cores busy | 2.64 | 1.77 | 2.73 | 1.04x |
| 500 | load generator CPU us / delivery | 2.01 | 3.56 | 1.68 | 0.84x |
| 500 | sends / delivery | 0.214 | 0.441 | 0.157 | 0.73x |
| 500 | Pss idle (MB) | 103 | 280 | 272 | 2.64x |
| 500 | Pss saturated (MB) | 106 | 561 | 285 | 2.70x |
| 500 | paced post -> last client p50 / p99 | 6.3 / 9.4 | 7.5 / 11.5 | 6.1 / 11.7 | 0.96x |
| 500 | paced post -> a client p50 / p99 | 4.3 / 7.6 | 4.7 / 9.7 | 4.6 / 11.5 | 1.07x |
| 500 | saturated post -> last client p50 / p99 | 5.7 / 20.2 | 6.1 / 23.0 | 6.5 / 23.1 | 1.15x |
| 1,000 | server CPU us / delivery | 2.25 | 8.30 | 1.90 | 0.84x |
| 1,000 | server cores busy | 3.80 | 3.88 | 3.76 | 0.99x |
| 1,000 | load generator cores busy | 2.83 | 1.58 | 2.91 | 1.03x |
| 1,000 | load generator CPU us / delivery | 1.66 | 3.41 | 1.46 | 0.88x |
| 1,000 | sends / delivery | 0.102 | 0.364 | 0.102 | 1.00x |
| 1,000 | Pss idle (MB) | 112 | 553 | 282 | 2.52x |
| 1,000 | Pss saturated (MB) | 114 | 689 | 317 | 2.77x |
| 1,000 | paced post -> last client p50 / p99 | 10.6 / 13.4 | 12.9 / 20.1 | 9.1 / 12.5 | 0.86x |
| 1,000 | paced post -> a client p50 / p99 | 6.5 / 11.7 | 7.9 / 17.4 | 6.4 / 11.5 | 0.99x |
| 1,000 | saturated post -> last client p50 / p99 | 19.9 / 68.4 | 18.1 / 68.0 | 27.9 / 66.6 | 1.40x |
| 2,000 | server CPU us / delivery | 1.86 | 9.22 | 1.79 | 0.96x |
| 2,000 | server cores busy | 3.94 | 3.88 | 3.78 | 0.96x |
| 2,000 | load generator cores busy | 2.90 | 1.42 | 2.91 | 1.01x |
| 2,000 | load generator CPU us / delivery | 1.37 | 3.35 | 1.36 | 0.99x |
| 2,000 | sends / delivery | 0.043 | 0.312 | 0.079 | 1.81x |
| 2,000 | Pss idle (MB) | 125 | 724 | 311 | 2.48x |
| 2,000 | Pss saturated (MB) | 133 | 934 | 369 | 2.77x |
| 2,000 | paced post -> last client p50 / p99 | 14.9 / 23.1 | 19.7 / 28.2 | 15.1 / 19.3 | 1.01x |
| 2,000 | paced post -> a client p50 / p99 | 8.4 / 18.9 | 13.5 / 26.7 | 8.8 / 17.5 | 1.04x |
| 2,000 | saturated post -> last client p50 / p99 | 101.5 / 156.3 | 48.4 / 160.6 | 72.3 / 133.8 | 0.71x |
