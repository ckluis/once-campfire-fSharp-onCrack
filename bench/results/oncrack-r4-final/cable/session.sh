#!/usr/bin/env bash
# R4 final cable session, inside colima: 3 reps in alternating order (rep 1: Rust, port, onCrack; rep 2 reversed; rep 3 as 1), then the
# sends pass (one rep each, perf-counted send syscalls).
set -uo pipefail
cd "$(dirname "$0")/../../../.."
P=bench/results/oncrack-r4-final/cable/part.sh
for rep in 1 2 3; do
  if [ $rep = 2 ]; then apps="oncrack fsharp rust"; else apps="rust fsharp oncrack"; fi
  for app in $apps; do
    echo "== $app rep $rep $(date +%T) load $(cut -d' ' -f1-3 /proc/loadavg)"
    $P "$app" "$rep"
  done
done
for app in rust fsharp oncrack; do echo "== sends $app $(date +%T)"; $P "$app" 1 sends; done
echo SESSION DONE
