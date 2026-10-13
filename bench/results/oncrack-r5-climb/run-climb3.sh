#!/usr/bin/env bash
# run-climb3.sh: inside colima, detached. A second post_message cross-check of the two fresh configs, r3 first this time (r5-fresh-post was disturbed by the host).
# go test -race and build jobs: r5-cached-attempt1 had 8 noisy-host flags, r3-cached-attempt1 was stopped at the disk floor and its reps read 683-22,593 req/s
# on room page c=1), then a post_message cross-check of the two fresh configs (their post rows moved against round 3 with the host flagged noisy).
# Same images, env and schedule as run-climb.sh. Stops under 12 GiB free on the Mac at the start of each step.
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack
D=$R/bench/results/oncrack-r5-climb
cd "$R"; rm -f "$D/.exit3"
step() { # name image extra routes
  name=$1 img=$2 extra=$3 routes=$4
  free=$(df -k /Users/clank | awk 'NR==2 {print $4}')
  echo "$(date +%T) $name start, mac free $((free/1024/1024)) GiB" >> "$D/progress.log"
  if [ "$free" -lt $((12*1024*1024)) ]; then echo "$(date +%T) under the floor, stopping" >> "$D/progress.log"; echo 3 > "$D/.exit3"; exit 3; fi
  rm -rf "$D/$name"
  ONCRACK_IMAGE=$img ONCRACK_EXTRA_ENV=$extra bench/quick --reps 3 ${routes:+--routes $routes} --out "$D/$name" > "$D/$name.log" 2>&1 < /dev/null
  echo $? > "$D/$name.rc"; echo "$(date +%T) $name exit $(cat $D/$name.rc)" >> "$D/progress.log"
  docker ps -q --filter name=bench-campfire | xargs -r docker rm -f > /dev/null 2>&1
  sudo sh -c 'sync; fstrim -av' > /dev/null 2>&1
}
step r3-fresh-post2 campfire-oncrack:r3final "" post_message
step r5-fresh-post2 campfire-oncrack:r5head "" post_message
echo 0 > "$D/.exit3"
