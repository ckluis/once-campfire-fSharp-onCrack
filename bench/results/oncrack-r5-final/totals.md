| Session | Timed responses validated | Acknowledged writes audited | Errors + invalid | Raw samples | Peak generator CPU % |
|---|---:|---:|---:|---:|---:|
| mixed-1 | 41,614,259 | 7,017 | 0 | 144 | 251.5 |
| mixed-2 | 31,779,395 | 7,034 | 0 | 144 | 246.0 |
| mixed-3 | 30,731,302 | 6,867 | 0 | 144 | 246.8 |
| normal-1 | 43,868,876 | 986,759 | 0 | 180 | 253.4 |
| normal-2 | 43,122,716 | 1,096,876 | 0 | 180 | 261.6 |
| normal-3 | 33,285,759 | 657,676 | 0 | 180 | 247.9 |
| **all** | **224,402,307** | **2,762,229** | **0** | **972** | |

| Geometric mean of the medians | fresh/rust | fresh/c | fresh/port | cached/rust | cached/c | fresh/cached |
|---|---:|---:|---:|---:|---:|---:|
| mixed-1 | 6.33x | 2.38x | 5.25x | 5.31x | 2.00x | 1.19x |
| mixed-2 | 3.12x | 1.48x | 4.76x | 5.44x | 2.58x | 0.57x |
| mixed-3 | 3.00x | 3.81x | 11.13x | 4.10x | 5.22x | 0.73x |
| normal-1 | 2.11x | 1.46x | 2.73x | 3.50x | 2.42x | 0.60x |
| normal-2 | 3.28x | 2.99x | 5.23x | 3.31x | 3.02x | 0.99x |
| normal-3 | 4.74x | 1.41x | 6.72x | 7.49x | 2.23x | 0.63x |
