#!/usr/bin/env bash
# Unit R4.2's tier 3 session, inside colima: 3 reps in bench/run's order (rep 1: Rust, port, onCrack; rep 2 reversed; rep 3 as 1), then the
# sends pass. Stops under 12 GB free on the Mac (df of the data volume is not visible here, so the VM's disk is watched instead).
set -uo pipefail
cd "$(dirname "$0")/../../.."
for rep in 1 2 3; do
  for app in rust fsharp oncrack; do
    echo "== $app rep $rep $(date +%T) load $(cut -d' ' -f1-3 /proc/loadavg)"
    bench/results/oncrack-r4-fanout/part.sh "$app" "$rep"
  done
done
for app in rust fsharp oncrack; do echo "== sends $app $(date +%T)"; bench/results/oncrack-r4-fanout/part.sh "$app" 1 sends; done
echo SESSION DONE
