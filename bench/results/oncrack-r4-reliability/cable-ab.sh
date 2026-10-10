#!/usr/bin/env bash
# Unit R4.5's same-session switch A/B of the R4.1 cable suite (window 128, raw client, 1,000 and 2,000 clients), inside colima, on the rebuilt
# image (campfire-oncrack:app, no mount): R = the ring of rounds 1-4 (CAMPFIRE_CABLE_LOG=ring), L = the log with the old stream-at-a-time order
# (CAMPFIRE_CABLE_ORDER=stream), D = the shipped default (log, publish order, pressure on). Order R L D D L R so that host drift cancels
# (add more rounds with ORDER="..."). Results in cable-ab/N-X; `python3 ../oncrack-r4-fanout/table.py cable-ab/*` prints them.
set -uo pipefail
cd "$(dirname "$0")/../../.."
export ONCRACK_MOUNT=""
order=${ORDER:-"R L D D L R"}
i=0
for v in $order; do
  i=$((i+1))
  case $v in
    R) env="CAMPFIRE_CABLE_LOG=ring" ;;
    L) env="CAMPFIRE_CABLE_ORDER=stream" ;;
    D) env="CAMPFIRE_CABLE_PRESSURE=on" ;;
  esac
  bench/results/oncrack-r4-fanout/pair.sh "../../oncrack-r4-reliability/cable-ab/${PREFIX:-}$i-$v" "$env" "${CLIENTS:-1000 2000}"
done
echo AB DONE
