#!/usr/bin/env bash
# R2.5: the AOT build (AOT=1 bin/publish-mounted /var/tmp/campfire-r25-aot, 64a714d) mounted over the image, cold start and the classic memory suite.
set -uo pipefail
R=bench/results/oncrack-r2-mem
CLASSIC="idle:10 get:room:1:10 get:room:16:15 get:messages:16:10 get:sidebar:16:10 get:search:16:10 get:up:16:10 idle:5 post:1:15 post:16:30 post:64:20 idle:8 cable:100 idle:5 cable:500 idle:5 cable:1000 idle:5 upload:5 idle:10"
for i in 1 2; do
  echo "##### boot aot $i $(date +%T)"
  bench/boot --mounted /var/tmp/campfire-r25-aot --runs 7 --label "t3-boot-aot" --out $R/boot.jsonl 2>&1 | grep -E "^median"
done
echo "##### mem classic aot $(date +%T)"
bench/mem --mounted /var/tmp/campfire-r25-aot --label "t3-classic-aot" --out $R/mem-t3.jsonl $CLASSIC 2>&1 | grep -E "^(  |idle|get|post|cable|upload|whole|cold)"
echo "##### done"
