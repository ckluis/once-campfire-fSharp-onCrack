onCrack in bench/results/oncrack-r3-wal/t3-ceiling-2 against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 12,857 | 8,905 | **1.444x** | 7,174 | **1.792x** | 223.4 | 353.0 | 385.6 |

Checks:
  note post_message c=16: warm-up did not settle (reached the maximum)
  note post_message c=16: host probe 1.11 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 2 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
