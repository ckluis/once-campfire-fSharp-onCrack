#!/usr/bin/env bash
# R2.5 tier 3 driver (inside colima, from the repo root), second series: the two images alternate in one window.
# new = campfire-oncrack:app (64a714d), old = campfire-oncrack:r24 (R2.4's image, 4e12ec8).
set -uo pipefail
R=bench/results/oncrack-r2-mem
img() { case $1 in new) echo campfire-oncrack:app ;; old) echo campfire-oncrack:r24 ;; esac; }
for step in "old 1" "new 1" "old 2" "new 2"; do
  set -- $step
  echo "##### t3b real $step $(date +%T)"
  ONCRACK_IMAGE=$(img $1) bench/quick --real --reps 3 --only "oncrack:$2" --out "$R/t3b-real-$1" 2>&1 | grep -E "oncrack rep $2: (cold|mixed|spread|search)|responses|decoded" | cut -c1-250
done
CLASSIC="idle:10 get:room:1:10 get:room:16:15 get:messages:16:10 get:sidebar:16:10 get:search:16:10 get:up:16:10 idle:5 post:1:15 post:16:30 post:64:20 idle:8 cable:100 idle:5 cable:500 idle:5 cable:1000 idle:5 upload:5 idle:10"
REAL="idle:5 real:spread:30 idle:3 real:spread_mixed:30 idle:3 real:search_spread:30 idle:3 real:mixed:20 idle:3"
for which in new old; do
  echo "##### mem classic $which $(date +%T)"
  ONCRACK_IMAGE=$(img $which) bench/mem --label "t3-classic-$which" --out $R/mem-t3.jsonl $CLASSIC 2>&1 | grep -E "^(  |idle|get|post|cable|upload|whole|cold)"
  echo "##### mem real $which $(date +%T)"
  ONCRACK_IMAGE=$(img $which) bench/mem --seed crowd --label "t3-real-$which" --out $R/mem-t3.jsonl $REAL 2>&1 | grep -E "^(  |idle|real|whole|cold)"
done
for which in new old new old; do
  echo "##### boot $which $(date +%T)"
  ONCRACK_IMAGE=$(img $which) bench/boot --runs 7 --label "t3-boot-$which" --out $R/boot.jsonl 2>&1 | grep -E "^median"
done
echo "##### done $(date +%T)"
