#!/usr/bin/env bash
# Unit R4.2's same-session switch A/B on the rebuilt image (no mount), inside colima: onCrack at 100/500/1,000/2,000 clients with
# CAMPFIRE_CABLE_GATHER off and on, ABBAAB so that host drift cancels. Results in ab-image/NAME-{off,on}.
set -uo pipefail
cd "$(dirname "$0")/../../.."
export ONCRACK_MOUNT=""
i=0
for g in off on on off off on; do
  i=$((i+1))
  bench/results/oncrack-r4-fanout/pair.sh "../ab-image/$i-$g" "CAMPFIRE_CABLE_GATHER=$g" "100 500 1000 2000"
done
echo AB DONE
