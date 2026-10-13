onCrack in bench/results/oncrack-c2/tier3 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 98,146 [95,932-99,701] | 40,422 | **2.428x** | 28,623 | **3.429x** | 31.8 [32-32] | 93.6 | 122.4 |
| room page | 1 | 11,821 [11,646-11,941] | 7,617 | **1.552x** | 6,481 | **1.824x** | 151.7 [151-154] | 208.7 | 142.1 |
| messages page | 16 | 101,732 [101,459-101,789] | 37,836 | **2.689x** | 30,063 | **3.384x** | 30.3 [30-31] | 102.2 | 114.2 |
| messages page | 1 | 12,527 [12,267-12,682] | 8,312 | **1.507x** | 6,822 | **1.836x** | 148.4 [147-151] | 199.3 | 139.2 |
| sidebar | 16 | 108,132 [74,972-109,109] | 37,555 | **2.879x** | 28,238 | **3.829x** | 27.2 [27-30] | 101.8 | 123.2 |
| sidebar | 1 | 13,491 [13,129-13,775] | 8,000 | **1.686x** | 6,196 | **2.177x** | 138.0 [136-139] | 181.0 | 149.0 |
| search | 16 | 74,061 [70,983-74,762] | 34,070 | **2.174x** | 26,606 | **2.784x** | 31.2 [31-31] | 107.3 | 123.9 |
| search | 1 | 12,595 [12,571-12,938] | 6,055 | **2.080x** | 5,646 | **2.231x** | 145.2 [144-148] | 315.1 | 158.3 |
| post a message | 16 | 12,953 [12,572-12,983] | 8,905 | **1.455x** | 7,174 | **1.806x** | 236.7 [235-238] | 353.0 | 385.6 |
| post a message | 1 | 3,123 [3,023-3,176] | 3,052 | **1.023x** | 2,779 | **1.124x** | 622.4 [609-622] | 629.1 | 403.7 |

Checks:
  note messages_page c=16: warm-up did not settle (reached the maximum)
  note room_show c=16: warm-up did not settle (reached the maximum)
  note sidebar c=16: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
