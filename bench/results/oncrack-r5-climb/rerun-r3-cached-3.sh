#!/usr/bin/env bash
# Inside colima, detached: r3-cached rep 3 again (the first attempt was stopped by hand at the 12 GiB floor, with another project's go test -race
# loading the host). Same image, env and schedule as run-climb.sh; the output joins r3-cached/ as oncrack-3.json.
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack
D=$R/bench/results/oncrack-r5-climb
cd "$R"; rm -f "$D/.exit2" "$D/r3-cached/oncrack-3.json"
ONCRACK_IMAGE=campfire-oncrack:r3final ONCRACK_EXTRA_ENV=CAMPFIRE_FRESH_AUTH=0 bench/quick --reps 3 --only oncrack:3 --out "$D/r3-cached" > "$D/r3-cached-rep3.log" 2>&1 < /dev/null
echo $? > "$D/r3-cached-rep3.rc"
echo "$(date +%T) r3-cached rep 3 exit $(cat $D/r3-cached-rep3.rc)" >> "$D/progress.log"
docker ps -q --filter name=bench-campfire | xargs -r docker rm -f > /dev/null 2>&1
echo 0 > "$D/.exit2"
