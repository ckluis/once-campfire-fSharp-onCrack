#!/usr/bin/env bash
# run-climb4.sh: inside colima, detached. Third attempt at the two cached configs (attempts 1 and 2 ran while other projects loaded the host). Rule fixed before this ran: a cached row is logged from the one attempt with the fewest noisy-host flags in its vs-stored.md; every attempt stays in this directory.
# Same images, env and schedule as run-climb.sh. Stops under 12 GiB free on the Mac at the start of each step.
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack
D=$R/bench/results/oncrack-r5-climb
cd "$R"; rm -f "$D/.exit4"
step() { # name image extra routes
  name=$1 img=$2 extra=$3 routes=$4
  free=$(df -k /Users/clank | awk 'NR==2 {print $4}')
  echo "$(date +%T) $name start, mac free $((free/1024/1024)) GiB" >> "$D/progress.log"
  if [ "$free" -lt $((12*1024*1024)) ]; then echo "$(date +%T) under the floor, stopping" >> "$D/progress.log"; echo 3 > "$D/.exit4"; exit 3; fi
  rm -rf "$D/$name"
  ONCRACK_IMAGE=$img ONCRACK_EXTRA_ENV=$extra bench/quick --reps 3 ${routes:+--routes $routes} --out "$D/$name" > "$D/$name.log" 2>&1 < /dev/null
  echo $? > "$D/$name.rc"; echo "$(date +%T) $name exit $(cat $D/$name.rc)" >> "$D/progress.log"
  docker ps -q --filter name=bench-campfire | xargs -r docker rm -f > /dev/null 2>&1
  sudo sh -c 'sync; fstrim -av' > /dev/null 2>&1
}
step r5-cached3 campfire-oncrack:r5head CAMPFIRE_FRESH_AUTH=0
step r3-cached3 campfire-oncrack:r3final CAMPFIRE_FRESH_AUTH=0
echo 0 > "$D/.exit4"
