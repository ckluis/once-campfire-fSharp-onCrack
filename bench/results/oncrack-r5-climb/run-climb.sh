#!/usr/bin/env bash
# run-climb.sh: runs INSIDE colima, detached (nohup). Round 5 climb log: the project suite (bench/quick, tier 3, 3 reps, the five
# workloads at c=1 and c=16) on the round 3 final image (37c5988) and the round 5 HEAD image, each fresh (the default) and cached
# (CAMPFIRE_FRESH_AUTH=0). Output in bench/results/oncrack-r5-climb/<config>/; exit code in .exit (and per-config .rc files).
# Order alternates the images so host drift lands on both. Before each config it reads the Mac's free space and stops under 12 GiB.
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack
D=$R/bench/results/oncrack-r5-climb
cd "$R"
rm -f "$D/.exit"
for cfg in r5-fresh r3-fresh r5-cached r3-cached; do
  img=campfire-oncrack:r5head; [ "${cfg%%-*}" = r3 ] && img=campfire-oncrack:r3final
  extra=""; [ "${cfg##*-}" = cached ] && extra="CAMPFIRE_FRESH_AUTH=0"
  free=$(df -k /Users/clank | awk 'NR==2 {print $4}')
  echo "$(date +%T) $cfg start, mac free $((free/1024/1024)) GiB" >> "$D/progress.log"
  if [ "$free" -lt $((12*1024*1024)) ]; then echo "$(date +%T) under the floor, stopping" >> "$D/progress.log"; echo 3 > "$D/.exit"; exit 3; fi
  [ -s "$D/$cfg/oncrack-3.json" ] && { echo "$(date +%T) $cfg already done" >> "$D/progress.log"; continue; }
  rm -rf "$D/$cfg"
  ONCRACK_IMAGE=$img ONCRACK_EXTRA_ENV=$extra bench/quick --reps 3 --out "$D/$cfg" > "$D/$cfg.log" 2>&1 < /dev/null
  rc=$?
  echo $rc > "$D/$cfg.rc"
  echo "$(date +%T) $cfg exit $rc" >> "$D/progress.log"
  docker ps -q --filter name=cf- | xargs -r docker rm -f > /dev/null 2>&1
  sudo fstrim /var/lib/docker > /dev/null 2>&1
done
echo 0 > "$D/.exit"
