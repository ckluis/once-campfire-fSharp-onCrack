onCrack in /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-c4/tier3-aot against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)

| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |
|---|---|---|---|---|---|---|---|---|---|
| room page | 16 | 108,635 [107,254-108,662] | 40,422 | **2.688x** | 28,623 | **3.795x** | 35.1 [35-35] | 93.6 | 122.4 |
| room page | 1 | 15,957 [15,834-16,013] | 7,617 | **2.095x** | 6,481 | **2.462x** | 160.9 [161-164] | 208.7 | 142.1 |
| messages page | 16 | 107,256 [107,084-107,612] | 37,836 | **2.835x** | 30,063 | **3.568x** | 34.1 [34-34] | 102.2 | 114.2 |
| messages page | 1 | 16,655 [16,592-16,691] | 8,312 | **2.004x** | 6,822 | **2.441x** | 155.1 [155-159] | 199.3 | 139.2 |
| sidebar | 16 | 121,674 [119,580-121,763] | 37,555 | **3.240x** | 28,238 | **4.309x** | 30.6 [30-31] | 101.8 | 123.2 |
| sidebar | 1 | 18,008 [17,936-18,057] | 8,000 | **2.251x** | 6,196 | **2.906x** | 147.2 [145-151] | 181.0 | 149.0 |
| search | 16 | 120,224 [119,953-120,584] | 34,070 | **3.529x** | 26,606 | **4.519x** | 31.0 [31-31] | 107.3 | 123.9 |
| search | 1 | 17,184 [16,980-17,296] | 6,055 | **2.838x** | 5,646 | **3.044x** | 154.1 [153-154] | 315.1 | 158.3 |
| post a message | 16 | 13,614 [13,614-13,704] | 8,905 | **1.529x** | 7,174 | **1.898x** | 239.4 [239-240] | 353.0 | 385.6 |
| post a message | 1 | 3,513 [3,441-3,565] | 3,052 | **1.151x** | 2,779 | **1.264x** | 657.2 [649-661] | 629.1 | 403.7 |

Checks:
  responses: every one 2xx with 0 connection errors in 30 runs
  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase
