
### normal-1 (normal, 3 rounds, search order by app: {"oncrack": "id", "oncrack-prev": "created_at", "rust": "id", "c": "id", "fsharp": "created_at"})

| App | search req/s median [min-max] | timed responses validated | errors + invalid | p50 / p99 ms |
|---|---:|---:|---:|---|
| onCrack (this unit) | 160,502 [158,501-161,260] | 3,842,448 | 0 | 0.090 / 0.244 |
| onCrack before R3.3 (87c1ad1) | 160,709 [160,247-161,931] | 3,863,393 | 0 | 0.090 / 0.242 |
| Rust f9dca47 | 53,462 [45,929-56,114] | 1,244,157 | 0 | 0.272 / 0.722 |
| C cd0cbe4 | 80,622 [80,472-84,388] | 1,964,008 | 0 | 0.188 / 0.410 |
| F# port | 30,795 [29,062-30,973] | 726,748 | 0 | 0.473 / 1.384 |

onCrack / Rust f9dca47: 3.00x
onCrack / C cd0cbe4: 1.99x
onCrack / onCrack before R3.3 (87c1ad1): 1.00x
onCrack / F# port: 5.21x

### normal-2 (normal, 3 rounds, search order by app: {"oncrack": "id", "oncrack-prev": "created_at", "rust": "id", "c": "id", "fsharp": "created_at"})

| App | search req/s median [min-max] | timed responses validated | errors + invalid | p50 / p99 ms |
|---|---:|---:|---:|---|
| onCrack (this unit) | 161,476 [159,545-163,398] | 3,875,679 | 0 | 0.090 / 0.236 |
| onCrack before R3.3 (87c1ad1) | 160,098 [150,191-161,853] | 3,777,445 | 0 | 0.090 / 0.239 |
| Rust f9dca47 | 55,961 [55,856-56,172] | 1,344,002 | 0 | 0.262 / 0.666 |
| C cd0cbe4 | 83,101 [82,778-83,981] | 1,999,026 | 0 | 0.184 / 0.393 |
| F# port | 30,391 [30,020-31,038] | 731,670 | 0 | 0.479 / 1.384 |

onCrack / Rust f9dca47: 2.89x
onCrack / C cd0cbe4: 1.94x
onCrack / onCrack before R3.3 (87c1ad1): 1.01x
onCrack / F# port: 5.31x

### mixed (mixed, 3 rounds, search order by app: {"oncrack": "id", "oncrack-prev": "created_at", "rust": "id", "c": "id", "fsharp": "created_at"})

| App | search req/s median [min-max] | timed responses validated | errors + invalid | p50 / p99 ms |
|---|---:|---:|---:|---|
| onCrack (this unit) | 151,590 [150,188-152,011] | 3,630,535 | 0 | 0.089 / 0.314 |
|  writer audit |  |  acknowledged 300, all verified: True |  |  |
| onCrack before R3.3 (87c1ad1) | 148,284 [138,548-151,367] | 3,505,828 | 0 | 0.093 / 0.309 |
|  writer audit |  |  acknowledged 300, all verified: True |  |  |
| Rust f9dca47 | 54,898 [54,596-54,954] | 1,315,666 | 0 | 0.262 / 0.718 |
|  writer audit |  |  acknowledged 300, all verified: True |  |  |
| C cd0cbe4 | 79,824 [79,569-82,092] | 1,932,009 | 0 | 0.187 / 0.417 |
|  writer audit |  |  acknowledged 300, all verified: True |  |  |
| F# port | 28,399 [24,172-30,072] | 661,230 | 0 | 0.486 / 1.574 |
|  writer audit |  |  acknowledged 300, all verified: True |  |  |

onCrack / Rust f9dca47: 2.76x
onCrack / C cd0cbe4: 1.90x
onCrack / onCrack before R3.3 (87c1ad1): 1.02x
onCrack / F# port: 5.34x

### pooled over the sessions given, per profile

normal:
  onCrack (this unit)              160,881 [158,501-163,398]  n=6
  onCrack before R3.3 (87c1ad1)    160,478 [150,191-161,931]  n=6
  Rust f9dca47                     55,908 [45,929-56,172]  n=6
  C cd0cbe4                        82,940 [80,472-84,388]  n=6
  F# port                          30,593 [29,062-31,038]  n=6
  onCrack / Rust f9dca47             2.88x
  onCrack / C cd0cbe4                1.94x
  onCrack / onCrack before R3.3 (87c1ad1) 1.00x
  onCrack / F# port                  5.26x
mixed:
  onCrack (this unit)              151,590 [150,188-152,011]  n=3
  onCrack before R3.3 (87c1ad1)    148,284 [138,548-151,367]  n=3
  Rust f9dca47                     54,898 [54,596-54,954]  n=3
  C cd0cbe4                        79,824 [79,569-82,092]  n=3
  F# port                          28,399 [24,172-30,072]  n=3
  onCrack / Rust f9dca47             2.76x
  onCrack / C cd0cbe4                1.90x
  onCrack / onCrack before R3.3 (87c1ad1) 1.02x
  onCrack / F# port                  5.34x

### the search page's message ids, one distinct list per app and session set

  oncrack        1 distinct list(s), 13 ids
  oncrack-prev   1 distinct list(s), 13 ids
  rust           1 distinct list(s), 13 ids
  c              1 distinct list(s), 13 ids
  fsharp         1 distinct list(s), 13 ids
  oncrack        equals Rust's list: True
  oncrack-prev   equals Rust's list: False
  rust           equals Rust's list: True
  c              equals Rust's list: True
  fsharp         equals Rust's list: False
