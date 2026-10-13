## upstream-normal (read-and-post-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search | Post a message |
|---|---:|---:|---:|---:|---:|
| onCrack | 173,975 [173,803-174,889] | 182,064 [174,088-182,332] | 190,284 [189,321-192,205] | 186,369 [184,586-187,118] | 15,214 [15,012-15,396] |
| Rust f9dca47 | 50,006 [49,938-50,293] | 46,785 [46,730-47,255] | 55,116 [54,642-55,674] | 55,752 [54,803-55,852] | 6,549 [6,544-6,560] |
| C cd0cbe4 | 75,833 [75,283-75,877] | 76,804 [75,898-78,612] | 82,969 [81,437-83,172] | 80,600 [76,815-84,866] | 5,867 [5,648-5,872] |
| F# port | 35,882 [35,876-36,117] | 42,124 [41,978-42,453] | 38,008 [34,155-38,052] | 33,641 [31,013-33,983] | 9,472 [8,976-9,568] |
| Rails 0aa339d | 5,325 [5,316-5,371] | 5,414 [5,332-5,424] | 5,734 [5,522-5,982] | 5,841 [5,784-5,853] | 401 [399-409] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| onCrack | 17,895,090 | 407,821 | - | - | 255.4 | 0.082 / 0.213 |
| Rust f9dca47 | 5,140,478 | 192,540 | - | - | 101.7 | 0.296 / 0.700 |
| C cd0cbe4 | 7,725,125 | 171,787 | - | - | 140.7 | 0.202 / 0.422 |
| F# port | 3,770,879 | 260,137 | - | - | 149.5 | 0.402 / 1.057 |
| Rails 0aa339d | 545,111 | 11,234 | - | - | 30.3 | 2.881 / 6.751 |
| all | 35,076,683 | 1,043,519 | 0 | | 255.4 | |

150 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

## upstream-mixed (mixed-read-write-v1, 3 rounds, 8 s, c=16, server CPUs 0-3, client CPUs 4-7)

| Implementation | Room page | Messages page | Sidebar | Search |
|---|---:|---:|---:|---:|
| onCrack | 170,862 [169,773-170,888] | 180,240 [179,902-181,130] | 190,099 [182,136-191,484] | 184,827 [184,206-185,074] |
| Rust f9dca47 | 47,636 [47,488-47,918] | 44,472 [43,782-44,530] | 54,992 [54,837-55,131] | 52,884 [51,026-54,241] |
| C cd0cbe4 | 72,453 [71,830-73,058] | 74,442 [74,415-75,589] | 81,947 [81,521-82,832] | 79,534 [76,707-80,989] |
| F# port | 32,411 [32,337-33,614] | 41,592 [39,657-41,805] | 37,571 [36,719-37,769] | 34,389 [34,292-34,662] |
| Rails 0aa339d | 3,057 [2,973-3,069] | 3,921 [3,856-4,003] | 4,789 [4,759-4,805] | 4,700 [4,610-4,704] |

| Implementation | Timed responses validated | Acknowledged writes audited (incl. warm-up) | Timed writer posts | Writes/s per sample (min-max) | Peak generator CPU % | p50 / p99 ms, room page |
|---|---:|---:|---:|---|---:|---|
| onCrack | 17,366,552 | 1,200 | 960 | 10.0-10.0 | 257.0 | 0.081 / 0.235 |
| Rust f9dca47 | 4,791,911 | 1,200 | 960 | 10.0-10.0 | 98.8 | 0.298 / 0.765 |
| C cd0cbe4 | 7,403,065 | 1,200 | 960 | 10.0-10.0 | 135.6 | 0.200 / 0.437 |
| F# port | 3,494,887 | 1,200 | 960 | 10.0-10.0 | 143.4 | 0.435 / 1.271 |
| Rails 0aa339d | 395,403 | 1,185 | 960 | 9.9-10.0 | 26.1 | 3.357 / 57.151 |
| all | 33,451,818 | 5,985 | 4,800 | | 257.0 | |

120 raw samples reconciled against the per-app rows; errors + invalid responses across all of them: 0.

