#!/usr/bin/env bash
# launch.sh: on the Mac. Waits for a quiet host (non-VM CPU under 100% for 3 samples, at most 600 s), writing host-load-cable.txt one level up,
# then starts cable/session.sh in the VM DETACHED with guard.sh beside it; the exit status lands in cable/session.exit. Wait with
#   FIRST= scripts/hostload-wait.sh cable bench/results/oncrack-r5-final/cable/session.exit 540   (repeat)
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-final
out=$R/host-load-cable.txt
nonvm() { ps -Ao pcpu,comm | awk 'NR>1 && $2 !~ /Virtualization|limactl|colima|ssh/ {c=$1; $1=""; sub(/^ /,""); k=split($0,p,"/"); printf "%s %s\n", c, p[k]}' | sort -rn; }
sample() { local t=$(date +%T) l=$(sysctl -n vm.loadavg | tr -d '{}'); local top=$(nonvm); local sum=$(echo "$top" | awk '{s+=$1} END {printf "%.0f", s}'); local t4=$(echo "$top" | head -4 | awk '{printf "%s %s, ", $1, $2}'); echo "$t load $l | sum $sum | $t4"; echo "$sum" > /tmp/hostsum.$$; }
echo "# host load during cable (ps -A, non-VM processes: top 4 by %CPU and the sum of all, every 10 s; loadavg)" > "$out"
waited=0; ok=0
while [ $waited -lt 600 ]; do
  sample >> "$out"; s=$(cat /tmp/hostsum.$$)
  if [ "$s" -lt 100 ]; then ok=$((ok+1)); else ok=0; fi
  [ $ok -ge 3 ] && break
  sleep 10; waited=$((waited+10))
done
rm -f /tmp/hostsum.$$
if [ $ok -ge 3 ]; then echo "# quiet after ${waited}s; session starts" >> "$out"; else echo "# NOT quiet after ${waited}s (sum >= 100%); session starts anyway" >> "$out"; fi
rm -f $R/cable/session.exit
colima ssh -- bash -c "setsid nohup bash $R/cable/run-guarded.sh > /dev/null 2>&1 < /dev/null &"
echo "started cable $(date +%T)"
