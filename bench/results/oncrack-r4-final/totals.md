| Session | Timed responses validated | Acknowledged writes audited | Errors + invalid | Raw samples | Peak generator CPU % |
|---|---:|---:|---:|---:|---:|
| mixed-1 | 43,552,331 | 7,194 | 0 | 144 | 244.8 |
| normal-1 | 49,092,579 | 1,366,090 | 0 | 180 | 259.4 |
| **all** | **92,644,910** | **1,373,284** | **0** | **324** | |

| Geometric mean of the medians | fresh/rust | fresh/c | fresh/port | cached/rust | cached/c | fresh/cached |
|---|---:|---:|---:|---:|---:|---:|
| mixed-1 | 3.26x | 2.63x | 4.72x | 2.83x | 2.29x | 1.15x |
| normal-1 | 3.29x | 2.40x | 4.01x | 3.37x | 2.47x | 0.97x |

Hand re-runs (review.jsonl): 48 timed windows (every one valid: True), 48 warm-ups, 16 database audits (every one ok: True, rich-text rows equal acknowledged: True, search-index rows missing: 0), 3,084,803 acknowledged posts audited.
