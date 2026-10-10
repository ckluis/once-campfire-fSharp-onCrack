| Session | Timed responses validated | Acknowledged writes audited | Errors + invalid | Raw samples | Peak generator CPU % |
|---|---:|---:|---:|---:|---:|
| normal-1 | 47,268,174 | 1,329,979 | 0 | 180 | 261.6 |
| normal-2 | 25,396,892 | 555,460 | 0 | 180 | 300.9 |
| mixed-1 | 41,577,354 | 7,176 | 0 | 144 | 260.3 |
| mixed-2 | 42,379,432 | 7,178 | 0 | 144 | 246.3 |
| **all four** | **156,621,852** | **1,899,793** | **0** | **648** | |

| Geometric mean of the medians | fresh/rust | fresh/c | fresh/port | cached/rust | cached/c | fresh/cached |
|---|---:|---:|---:|---:|---:|---:|
| normal-1 | 2.68x | 1.85x | 3.18x | 3.27x | 2.26x | 0.82x |
| normal-2 | 3.33x | 2.31x | 5.07x | 3.30x | 2.29x | 1.01x |
| mixed-1 | 3.56x | 2.30x | 5.33x | 4.12x | 2.66x | 0.86x |
| mixed-2 | 3.10x | 1.83x | 4.64x | 3.74x | 2.21x | 0.83x |

Hand re-runs (review.jsonl): 60 timed windows (every one valid: True), 60 warm-ups, 20 database audits (every one ok: True, rich-text rows equal acknowledged: True, search-index rows missing: 0), 5,030,671 acknowledged posts audited.
