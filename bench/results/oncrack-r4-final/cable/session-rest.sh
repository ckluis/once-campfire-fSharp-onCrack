#!/usr/bin/env bash
# The rest of the cable session after the first writer was stopped during fsharp rep 3 (rust 1-3, fsharp 1-2, oncrack 1-2 are in t3/):
# fsharp rep 3, onCrack rep 3 (rep 3 runs in session.sh's order: rust, port, onCrack), then the sends pass. Run INSIDE colima, detached;
# the exit status goes to cable/session-rest.exit. guard.sh stops it under 12 GB free on the Mac.
cd "$(dirname "$0")/../../../.."
R=bench/results/oncrack-r4-final
P=$R/cable/part.sh
rm -f $R/cable/session-rest.exit
( for app in fsharp oncrack; do echo "== $app rep 3 $(date +%T) load $(cut -d' ' -f1-3 /proc/loadavg)"; $P $app 3; done
  for app in rust fsharp oncrack; do echo "== sends $app $(date +%T)"; $P $app 1 sends; done
  echo SESSION DONE ) &
pid=$!
taskset -c 4-7 $R/scripts/guard.sh $pid > /dev/null 2>&1 < /dev/null &
wait $pid; rc=$?
echo $rc > $R/cable/session-rest.exit
