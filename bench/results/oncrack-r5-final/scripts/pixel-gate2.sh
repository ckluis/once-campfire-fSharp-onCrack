#!/usr/bin/env bash
# Step 3 continued, inside colima, detached: the units pixel-gate.sh could not finish. B2 (auth/sign_in/error, which slice B's three attempts could not capture) and
# realtime/** again as three sub-slices I1-I3 (the whole slice I crashed the harness 50 cells in). Same guard as pixel-gate.sh. Exit status in pixels/gate2.exit.
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack
P=$R/bench/results/oncrack-r5-final/pixels
OUT=$R/parity/out/pixel-parity-r5-final
cd $R; rm -f $P/gate2.exit
export PIXEL_PARITY_IN_VM=1 PARITY_NET_DIR=/tmp/parity-net
free_gb() { echo $(( $(df -k /Users/clank | awk 'NR==2 {print $4}') / 1024 / 1024 )); }
trim() { docker image prune -f >/dev/null 2>&1; docker buildx prune -f --filter until=10m >/dev/null 2>&1; sudo fstrim /var/lib/docker >/dev/null 2>&1; sync; sudo fstrim -av >/dev/null 2>&1; }
say() { echo "$(date +%T) $*" | tee -a $P/status.txt; }
# Slim a finished unit's reports: the page and diff images of cells that matched are not needed once report.json says so (the room capture is kept).
slim() { find $OUT/$1 \( -name '*.png' -o -name '*.html' -o -name '*.txt' -o -name '*.yml' \) ! -path '*rooms/show/busy/last_page*' -delete 2>/dev/null; }
overall=0
unit() {
  local name=$1 out=$2; shift 2
  if [ "$(free_gb)" -lt 12 ]; then trim; fi
  if [ "$(free_gb)" -lt 12 ]; then say "STOP before $name: Mac free $(free_gb) GiB, under the 12 GiB floor"; echo 3 > $P/gate2.exit; exit 3; fi
  say "start $name (Mac free $(free_gb) GiB)"
  bin/pixel-parity "$@" --out $OUT/$out > $P/logs/$name.log 2>&1; local rc=$?
  find $R/parity -maxdepth 1 -name 'core*' -exec rm -f {} + 2>/dev/null
  [ $rc -eq 0 ] && slim $out
  say "end $name exit $rc (Mac free $(free_gb) GiB)"
  [ $rc -eq 0 ] || overall=1
  trim
}
unit default-B2 B2 --seeds default --only 'auth/sign_in/error'
unit default-I1 I1 --seeds default --only 'realtime/message_sent,realtime/attachment_sent,realtime/message_edited,realtime/message_deleted,realtime/boosted'
unit default-I2 I2 --seeds default --only 'realtime/boost_removed,realtime/typing/**,realtime/unread_in_sidebar,realtime/new_room_in_sidebar'
unit default-I3 I3 --seeds default --only 'realtime/removed_from_room,realtime/room_deleted_then_send,realtime/presence_read'
say "gate2 done, overall $overall"
echo $overall > $P/gate2.exit
