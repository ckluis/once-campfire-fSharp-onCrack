| block | app | clients | containers | app environment (beyond the image's) | load generator | target phases | phases with a message not delivered to every client | other flagged (freeze, verify, error) | flagged for a database warning only | median msg/s |
|---|---|---|---|---|---|---|---|---|---|---|
| a-fresh500 | oncrack | 500 | fresh | server trace | - | 10 | 0 | 0 | 7 | 3034.6 |
| a-warm1000 | oncrack | 1000 | warm | server trace | - | 15 | 0 | 0 | 4 | 1905.3 |
| a-warm500 | oncrack | 500 | warm | server trace | - | 15 | 0 | 0 | 3 | 2820.9 |
| ab1-r4-image | oncrack | 500 | warm | - | (client trace 0) | 8 | 0 | 0 | 1 | 2802.9 |
| ab2-new-build | oncrack | 500 | warm | - | (client trace 0) | 8 | 0 | 0 | 0 | 3106.9 |
| ab3-r4-image | oncrack | 500 | warm | - | (client trace 0) | 8 | 3 | 0 | 0 | 2843.6 |
| ab4-new-build | oncrack | 500 | warm | - | (client trace 0) | 8 | 1 | 0 | 0 | 2888.6 |
| b-ring500 | oncrack | 500 | warm | CAMPFIRE_CABLE_LOG=ring server trace | - | 15 | 0 | 0 | 4 | 3115.6 |
| c-stream500 | oncrack | 500 | warm | CAMPFIRE_CABLE_ORDER=stream server trace | - | 15 | 0 | 0 | 0 | 3110.8 |
| c0-default-nostress | oncrack | 500 | fresh | CAMPFIRE_CABLE_VERIFY=1 | - | 12 | 0 | 0 | 12 | 2877.1 |
| c1-default-stress | oncrack | 500 | fresh | CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000 | - | 6 | 0 | 0 | 6 | 2412.3 |
| c2-ring-stress | oncrack | 500 | fresh | CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000 CAMPFIRE_CABLE_LOG=ring | - | 6 | 0 | 0 | 6 | 2101.1 |
| c3-orderstream-stress | oncrack | 500 | fresh | CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000 CAMPFIRE_CABLE_ORDER=stream | - | 6 | 0 | 0 | 6 | 1855.1 |
| c4-gatheroff-stress | oncrack | 500 | fresh | CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000 CAMPFIRE_CABLE_GATHER=off | - | 6 | 0 | 0 | 0 | 1447.7 |
| c5-directoff-stress | oncrack | 500 | fresh | CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000 CAMPFIRE_CABLE_DIRECT=off | - | 6 | 0 | 0 | 0 | 843.0 |
| d-port500 | fsharp | 500 | warm | - | - | 6 | 0 | 0 | 0 | 905.3 |
| d1-procmem-stress | oncrack | 500 | fresh | CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000 | - | 10 | 0 | 7 | 3 | 749.8 |
| d2-procmem-default | oncrack | 500 | fresh | - | - | 10 | 1 | 5 | 0 | 1260.6 |
| e-rust500 | rust | 500 | warm | - | - | 6 | 0 | 0 | 0 | 2708.3 |
| f-tail0-500 | oncrack | 500 | warm | server trace | --tail-window 0 | 10 | 0 | 0 | 0 | 2979.9 |
| g-fresh500b | oncrack | 500 | fresh | server trace | - | 10 | 0 | 0 | 0 | 3133.4 |
| g-warm500b | oncrack | 500 | warm | server trace | - | 20 | 0 | 2 | 1 | 2658.7 |
| i-notrace500 | oncrack | 500 | warm | - | - | 15 | 3 | 0 | 0 | 3032.0 |
| j-procmem-fresh500 | oncrack | 500 | fresh | server trace | - | 8 | 0 | 3 | 1 | 2844.9 |
| k1-default-notrace | oncrack | 500 | warm | - | - | 15 | 0 | 0 | 0 | 3119.6 |
| k2-gather-off | oncrack | 500 | warm | CAMPFIRE_CABLE_GATHER=off | - | 15 | 0 | 0 | 0 | 2767.5 |
| k3-direct-off | oncrack | 500 | warm | CAMPFIRE_CABLE_DIRECT=off | - | 15 | 0 | 0 | 0 | 2367.5 |
| m1-gc16mb | oncrack | 500 | warm | DOTNET_GCgen0MaxBudget=1000000 | - | 12 | 0 | 0 | 0 | 2848.6 |
| m2-gc4mb | oncrack | 500 | warm | DOTNET_GCgen0MaxBudget=400000 | - | 12 | 1 | 0 | 0 | 3016.1 |
| p1-port-stress | fsharp | 500 | fresh | DOTNET_GCgen0MaxBudget=400000 | - | 10 | 0 | 0 | 0 | 406.8 |
| r1-rust | rust | 500 | fresh | - | - | 10 | 0 | 0 | 0 | 994.4 |
| smoke | oncrack | 100 | warm | server trace | --trace-always 1 | 1 | 0 | 0 | 0 | 4972.6 |
| v1-verify-gc1mb | oncrack | 500 | warm | CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0size=0x100000 DOTNET_GCgen0MaxBudget=100000 | - | 12 | 0 | 0 | 1 | 2988.5 |
| v2-verify-gc4mb | oncrack | 500 | warm | CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000 | - | 12 | 0 | 0 | 2 | 2780.6 |
| v3-verify-default | oncrack | 500 | warm | CAMPFIRE_CABLE_VERIFY=1 | - | 12 | 1 | 0 | 2 | 2917.8 |
| w1-verify-gc1mb-gather-off | oncrack | 500 | warm | CAMPFIRE_CABLE_VERIFY=1 CAMPFIRE_CABLE_GATHER=off DOTNET_GCgen0size=0x100000 DOTNET_GCgen0MaxBudget=100000 | - | 12 | 0 | 0 | 1 | 2753.1 |
| y1-verify-gc4mb-tc-off | oncrack | 500 | warm | CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000 DOTNET_TieredCompilation=0 | - | 6 | 0 | 0 | 2 | 1934.1 |
| y2-verify-gc4mb-r2r-off | oncrack | 500 | fresh | CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000 DOTNET_ReadyToRun=0 | - | 6 | 0 | 0 | 6 | 2844.3 |
| y3-verify-gc4mb-fresh | oncrack | 500 | fresh | CAMPFIRE_CABLE_VERIFY=1 DOTNET_GCgen0MaxBudget=400000 | - | 6 | 1 | 0 | 5 | 2785.8 |

Total target phases: 395; with a message not delivered to every client: 11
