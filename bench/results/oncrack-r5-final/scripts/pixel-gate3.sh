#!/usr/bin/env bash
# Step 3 continued, inside colima, detached: realtime/** as sub-slices I1-I3 again, now with a watchdog. pixel-gate2.sh's I1 sat 40 minutes at 25 of 40 cells with the VM idle
# (a harness hang; its first whole-slice attempt crashed with 'Response has been disposed'). Each unit gets TMO seconds (default 1500; the whole slice took 1130 s in the
# attempt that crashed); on a timeout its processes and containers are killed and it is tried again, up to 3 times. Exit status in pixels/gate3.exit.
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack
P=$R/bench/results/oncrack-r5-final/pixels
OUT=$R/parity/out/pixel-parity-r5-final
TMO=${TMO:-1500}
cd $R; rm -f $P/gate3.exit
export PIXEL_PARITY_IN_VM=1 PARITY_NET_DIR=/tmp/parity-net
free_gb() { echo $(( $(df -k /Users/clank | awk 'NR==2 {print $4}') / 1024 / 1024 )); }
trim() { docker image prune -f >/dev/null 2>&1; docker builder prune -af >/dev/null 2>&1; sudo fstrim /var/lib/docker >/dev/null 2>&1; sync; sudo fstrim -av >/dev/null 2>&1; }
say() { echo "$(date +%T) $*" | tee -a $P/status.txt; }
slim() { find $OUT/$1 \( -name '*.png' -o -name '*.html' -o -name '*.txt' -o -name '*.yml' \) ! -path '*rooms/show/busy/last_page*' -delete 2>/dev/null; }
overall=0
unit() {   # unit NAME OUTDIR ARGS...
  local name=$1 out=$2; shift 2
  local try rc
  for try in 1 2 3; do
    if [ "$(free_gb)" -lt 12 ]; then trim; fi
    if [ "$(free_gb)" -lt 12 ]; then say "STOP before $name: Mac free $(free_gb) GiB, under the 12 GiB floor"; echo 3 > $P/gate3.exit; exit 3; fi
    rm -rf $OUT/$out; say "start $name try $try (Mac free $(free_gb) GiB)"
    timeout -k 20 $TMO bin/pixel-parity "$@" --out $OUT/$out > $P/logs/$name-try$try.log 2>&1; rc=$?
    find $R/parity -maxdepth 1 -name 'core*' -exec rm -f {} + 2>/dev/null
    if [ $rc -eq 124 ] || [ $rc -eq 137 ]; then
      say "$name try $try: timed out after ${TMO}s; killing its processes and containers"
      pkill -f "pixel-parity-r5-final/$out" 2>/dev/null; sleep 3; docker ps -aq | xargs -r docker rm -f >/dev/null 2>&1; trim; continue
    fi
    break
  done
  [ $rc -eq 0 ] && slim $out
  say "end $name exit $rc after $try tries (Mac free $(free_gb) GiB)"
  [ $rc -eq 0 ] || overall=1
  trim
}
unit default-I1 I1 --seeds default --only 'realtime/message_sent,realtime/attachment_sent,realtime/message_edited,realtime/message_deleted,realtime/boosted'
unit default-I2 I2 --seeds default --only 'realtime/boost_removed,realtime/typing/**,realtime/unread_in_sidebar,realtime/new_room_in_sidebar'
unit default-I3 I3 --seeds default --only 'realtime/removed_from_room,realtime/room_deleted_then_send,realtime/presence_read'
say "gate3 done, overall $overall"
echo $overall > $P/gate3.exit
