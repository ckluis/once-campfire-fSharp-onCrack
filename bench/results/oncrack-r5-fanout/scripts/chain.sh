#!/usr/bin/env bash
# Unit R5.3: the in-container sessions, back to back, inside colima, detached:  OUT=DIR chain.sh   ($OUT/chain.done at the end, $OUT/chain.log)
cd "$(dirname "${BASH_SOURCE[0]}")/../../../.."
OUT=${OUT:?}; export ONCRACK_MOUNT=${ONCRACK_MOUNT:-/var/tmp/campfire-r53}
mkdir -p "$OUT"; rm -f "$OUT/chain.done"
step() { echo "$(date +%T) $1 start (load $(cat /proc/loadavg))" >> "$OUT/chain.log"; shift; "$@" ; echo "$(date +%T) done ($?)" >> "$OUT/chain.log"; }
AB='merge@ stream@order=stream ring@log=ring+order=stream'
L3='b64@ b128@batch=128 b32@batch=32 h3000@hold=3000 h0@hold=0'
step "flip log/order 1000" bench/cable/flip --clients 1000 --reps 6 --secs 8 --arms "$AB" --out "$OUT/flipA1000" > "$OUT/flipA1000.log" 2>&1
step "flip log/order 2000" bench/cable/flip --clients 2000 --reps 6 --secs 8 --arms "$AB" --out "$OUT/flipA2000" > "$OUT/flipA2000.log" 2>&1
step "flip lever3 1000" bench/cable/flip --clients 1000 --reps 5 --secs 8 --arms "$L3" --out "$OUT/flipB1000" > "$OUT/flipB1000.log" 2>&1
step "flip lever3 2000" bench/cable/flip --clients 2000 --reps 5 --secs 8 --arms "$L3" --out "$OUT/flipB2000" > "$OUT/flipB2000.log" 2>&1
touch "$OUT/chain.done"
