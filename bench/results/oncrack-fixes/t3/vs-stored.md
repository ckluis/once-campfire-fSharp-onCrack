onCrack in bench/results/oncrack-fixes/t3 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 123,248 [119,669-124,976] | 40,422 | **3.049x** | 28,623 | **4.306x** | 30.4 [30-31] | 93.6 | 122.4 |
| room page | 1 | 13,342 [13,190-13,486] | 7,617 | **1.752x** | 6,481 | **2.059x** | 145.3 [145-147] | 208.7 | 142.1 |
| messages page | 16 | 123,156 [122,187-123,345] | 37,836 | **3.255x** | 30,063 | **4.097x** | 30.3 [30-31] | 102.2 | 114.2 |
| messages page | 1 | 13,496 [13,370-13,707] | 8,312 | **1.624x** | 6,822 | **1.978x** | 144.5 [144-147] | 199.3 | 139.2 |
| sidebar | 16 | 137,500 [136,387-137,709] | 37,555 | **3.661x** | 28,238 | **4.869x** | 26.9 [27-27] | 101.8 | 123.2 |
| sidebar | 1 | 15,840 [15,372-15,929] | 8,000 | **1.980x** | 6,196 | **2.556x** | 126.6 [126-127] | 181.0 | 149.0 |
| search | 16 | 135,425 [134,739-136,166] | 34,070 | **3.975x** | 26,606 | **5.090x** | 27.3 [27-28] | 107.3 | 123.9 |
| search | 1 | 14,669 [14,528-15,254] | 6,055 | **2.422x** | 5,646 | **2.598x** | 135.5 [134-137] | 315.1 | 158.3 |
| post a message | 16 | 12,991 [12,962-13,028] | 8,905 | **1.459x** | 7,174 | **1.811x** | 233.4 [233-236] | 353.0 | 385.6 |
| post a message | 1 | 3,374 [3,326-3,409] | 3,052 | **1.106x** | 2,779 | **1.214x** | 586.8 [584-593] | 629.1 | 403.7 |

Checks:
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note messages_page c=1: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
