#!/usr/bin/env bash
# R2.5 guard: the five classic workloads at c=16 on both images alternating (old = campfire-oncrack:r24, new = campfire-oncrack:app), and the
# upload latency of both (inside colima, from the repo root).
set -uo pipefail
R=bench/results/oncrack-r2-mem
img() { case $1 in new) echo campfire-oncrack:app ;; old) echo campfire-oncrack:r24 ;; esac; }
for step in "old 1" "new 1" "old 2" "new 2"; do
  set -- $step
  echo "##### guard classic $step $(date +%T)"
  ONCRACK_IMAGE=$(img $1) bench/quick --reps 3 --concs 16 --only "oncrack:$2" --out "$R/t3b-classic-$1" 2>&1 | grep -E "oncrack rep $2: (room_show|messages_page|sidebar|search|post_message)|responses|decoded" | cut -c1-210
done
for step in old new old new old new; do
  echo "##### upload $step"
  ONCRACK_IMAGE=$(img $step) bench/mem --label "upload-$step" idle:3 upload:15 idle:3 2>&1 | grep -E "upload median"
done
echo "##### done"
