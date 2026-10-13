#!/usr/bin/env bash
# Unit R5.3: the hold follow-up and the Rust control, after tail.sh, inside colima, detached:  OUT=DIR AFTER=FILE final.sh   ($OUT/final.done at the end)
cd "$(dirname "${BASH_SOURCE[0]}")/../../../.."
OUT=${OUT:?}; export ONCRACK_MOUNT=${ONCRACK_MOUNT:-/var/tmp/campfire-r53}
mkdir -p "$OUT"; rm -f "$OUT/final.done"
while [ -n "${AFTER:-}" ] && [ ! -f "$AFTER" ]; do sleep 5; done
step() { echo "$(date +%T) $1 start (load $(cat /proc/loadavg))" >> "$OUT/final.log"; shift; "$@" ; echo "$(date +%T) done ($?)" >> "$OUT/final.log"; }
H='h1000@ h3000@hold=3000 h6000@hold=6000'
step "flip hold 2000" bench/cable/flip --clients 2000 --reps 4 --secs 8 --arms "$H" --out "$OUT/flipH2000" > "$OUT/flipH2000.log" 2>&1
step "flip hold 1000" bench/cable/flip --clients 1000 --reps 3 --secs 8 --arms "$H" --out "$OUT/flipH1000" > "$OUT/flipH1000.log" 2>&1
step "flip hold 100" bench/cable/flip --clients 100 --reps 3 --secs 8 --arms "h1000@ h3000@hold=3000" --out "$OUT/flipH100" > "$OUT/flipH100.log" 2>&1
OUT=$OUT/control step "control" bench/results/oncrack-r5-fanout/scripts/control.sh 2 > /dev/null 2>&1
touch "$OUT/final.done"
