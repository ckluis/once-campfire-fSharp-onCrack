#!/usr/bin/env bash
# Unit R5.3: after the log/order session: ring and default profiles at 1,000 clients, then the batch and hold knobs at 2,000 and the memory
# attribution, inside colima, detached:  OUT=DIR tail.sh   ($OUT/tail.done at the end)
cd "$(dirname "${BASH_SOURCE[0]}")/../../../.."
OUT=${OUT:?}; export ONCRACK_MOUNT=${ONCRACK_MOUNT:-/var/tmp/campfire-r53}
mkdir -p "$OUT"; rm -f "$OUT/tail.done"
while pgrep -f "bench/cable/flip" > /dev/null; do sleep 5; done
step() { echo "$(date +%T) $1 start (load $(cat /proc/loadavg))" >> "$OUT/tail.log"; shift; "$@" ; echo "$(date +%T) done ($?)" >> "$OUT/tail.log"; }
export MOUNT=/var/tmp/campfire-r53
OUT=$OUT/perf2 step "perf ring/default 1000" bench/results/oncrack-r5-fanout/scripts/perf3.sh 'ring-1000|1000|CAMPFIRE_CABLE_LOG=ring' 'default-1000|1000|' 'ring-1000b|1000|CAMPFIRE_CABLE_LOG=ring' > /dev/null 2>&1
step "flip lever3 2000" bench/cable/flip --clients 2000 --reps 3 --secs 8 --arms 'b64@ b128@batch=128 h3000@hold=3000' --out "$OUT/flipB2000" > "$OUT/flipB2000.log" 2>&1
step "mem cable:2000" env SMAPS=1 bench/mem --mounted /var/tmp/campfire-r53 --label r53-cable2000 --out "$OUT/mem-cable2000.jsonl" idle:3 cable:2000 idle:5 > "$OUT/mem-cable2000.txt" 2>&1
touch "$OUT/tail.done"
