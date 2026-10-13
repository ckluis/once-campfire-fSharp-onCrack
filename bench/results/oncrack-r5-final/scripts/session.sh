#!/usr/bin/env bash
# session.sh NAME [bin/benchmark args...] (NAME review-*: runs review-round.sh with the tag NAME and the args as variants instead): on the Mac. (1) waits for a quiet host (non-VM CPU under 100% for 3 samples 10 s apart, at most 600 s, then
# starts anyway and says so), writing host-load-NAME.txt; (2) starts run-fg.sh NAME in the VM DETACHED (nohup, setsid), which writes
# logs/session-NAME.exit on the Mac's disk when it ends; (3) returns. Wait with: scripts/hostload-wait.sh NAME logs/session-NAME.exit 540 (repeat).
name=$1; shift
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-final
out=$R/host-load-$name.txt
nonvm() { ps -Ao pcpu,comm | awk 'NR>1 && $2 !~ /Virtualization|limactl|colima|ssh/ {c=$1; $1=""; sub(/^ /,""); k=split($0,p,"/"); printf "%s %s\n", c, p[k]}' | sort -rn; }
sample() { local t=$(date +%T) l=$(sysctl -n vm.loadavg | tr -d '{}'); local top=$(nonvm); local sum=$(echo "$top" | awk '{s+=$1} END {printf "%.0f", s}'); local t4=$(echo "$top" | head -4 | awk '{printf "%s %s, ", $1, $2}'); echo "$t load $l | sum $sum | $t4"; echo "$sum" > /tmp/hostsum.$$; }
echo "# host load during $name (ps -A, non-VM processes: top 4 by %CPU and the sum of all, every 10 s; loadavg)" > "$out"
waited=0; ok=0
while [ $waited -lt 600 ]; do
  sample >> "$out"; s=$(cat /tmp/hostsum.$$)
  if [ "$s" -lt 100 ]; then ok=$((ok+1)); else ok=0; fi
  [ $ok -ge 3 ] && break
  sleep 10; waited=$((waited+10))
done
rm -f /tmp/hostsum.$$
if [ $ok -ge 3 ]; then echo "# quiet after ${waited}s; session starts" >> "$out"; else echo "# NOT quiet after ${waited}s (sum >= 100%); session starts anyway" >> "$out"; fi
rm -f $R/logs/session-$name.exit
case $name in review-*) cmd="$R/scripts/review-round.sh $name $*" ;; *) cmd="$R/scripts/run-fg.sh $name $*" ;; esac
colima ssh -- bash -c "setsid nohup bash -c '$cmd > $R/logs/session-$name.log 2>&1; echo \$? > $R/logs/session-$name.exit' > /dev/null 2>&1 < /dev/null &"
echo "started $name $(date +%T)"
