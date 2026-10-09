#!/usr/bin/env bash
# R2.5: Rust and the F# port through the same classic scenario as t3-all.sh's memory suite (inside colima, from the repo root).
set -uo pipefail
R=bench/results/oncrack-r2-mem
CLASSIC="idle:10 get:room:1:10 get:room:16:15 get:messages:16:10 get:sidebar:16:10 get:search:16:10 get:up:16:10 idle:5 post:1:15 post:16:30 post:64:20 idle:8 cable:100 idle:5 cable:500 idle:5 cable:1000 idle:5 upload:5 idle:10"
for app in rust fsharp; do
  echo "##### mem classic $app $(date +%T)"
  bench/mem --app $app --no-memlog --label "t3-classic-$app" --out $R/mem-t3.jsonl $CLASSIC 2>&1 | grep -E "^(  |idle|get|post|cable|upload|whole|cold)"
done
for app in rust fsharp; do
  echo "##### boot $app $(date +%T)"
  bench/boot --app $app --runs 7 --label "t3-boot-$app" --out $R/boot.jsonl 2>&1 | grep -E "^median"
done
echo "##### done"
