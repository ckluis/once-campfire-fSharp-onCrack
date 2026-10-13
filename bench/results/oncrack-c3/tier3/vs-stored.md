onCrack in bench/results/oncrack-c3/tier3 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 124,328 [121,730-125,408] | 40,422 | **3.076x** | 28,623 | **4.344x** | 30.2 [30-31] | 93.6 | 122.4 |
| room page | 1 | 13,548 [13,391-14,140] | 7,617 | **1.779x** | 6,481 | **2.091x** | 143.1 [139-145] | 208.7 | 142.1 |
| messages page | 16 | 124,328 [123,737-125,240] | 37,836 | **3.286x** | 30,063 | **4.136x** | 29.8 [30-30] | 102.2 | 114.2 |
| messages page | 1 | 13,837 [13,695-14,025] | 8,312 | **1.665x** | 6,822 | **2.028x** | 142.2 [141-142] | 199.3 | 139.2 |
| sidebar | 16 | 138,274 [137,777-138,450] | 37,555 | **3.682x** | 28,238 | **4.897x** | 26.9 [27-27] | 101.8 | 123.2 |
| sidebar | 1 | 16,349 [16,150-16,362] | 8,000 | **2.044x** | 6,196 | **2.638x** | 122.9 [123-124] | 181.0 | 149.0 |
| search | 16 | 136,313 [135,560-136,920] | 34,070 | **4.001x** | 26,606 | **5.123x** | 27.0 [26-27] | 107.3 | 123.9 |
| search | 1 | 14,677 [14,535-14,818] | 6,055 | **2.424x** | 5,646 | **2.600x** | 136.0 [134-136] | 315.1 | 158.3 |
| post a message | 16 | 13,249 [12,811-13,281] | 8,905 | **1.488x** | 7,174 | **1.847x** | 231.2 [231-237] | 353.0 | 385.6 |
| post a message | 1 | 3,399 [3,355-3,430] | 3,052 | **1.114x** | 2,779 | **1.223x** | 581.1 [577-587] | 629.1 | 403.7 |

Checks:
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note messages_page c=1: warm-up did not settle (reached the maximum)
  note messages_page c=1: warm-up did not settle (reached the maximum)
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
