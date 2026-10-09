onCrack in bench/results/oncrack-r3-wal/tr-gate against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| post a message | 16 | 13,286 | 8,905 | **1.492x** | 7,174 | **1.852x** | 205.1 | 353.0 | 385.6 |

Checks:
  note post_message c=16: warm-up did not settle (fixed)
  note post_message c=64: warm-up did not settle (fixed)
  note post_message c=64: host probe 1.127 after the window (noisy host)
  responses: every one 2xx with 0 connection errors in 2 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
