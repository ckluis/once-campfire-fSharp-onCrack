#!/usr/bin/env bash
# session.sh NAME [bin/benchmark args...]: runs on the Mac. (1) waits for a quiet host (non-VM CPU under QUIET_CPU, default 100%, for 3 samples
# 10 s apart; at most QUIET_WAIT s, default 600, then runs anyway and says so), (2) samples the host every 10 s into host-load-NAME.txt (top 4
# non-VM processes by %CPU, their total, the load average), (3) runs run-fg.sh in the VM, (4) stops the sampler.
name=$1; shift
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r3-final
out=$R/host-load-$name.txt
quiet=${QUIET_CPU:-100}; maxwait=${QUIET_WAIT:-600}
nonvm() { ps -Ao pcpu,comm | awk 'NR>1 && $2 !~ /Virtualization|limactl|colima|ssh/ {n=split($0,a," "); c=$1; $1=""; sub(/^ /,""); k=split($0,p,"/"); printf "%s %s\n", c, p[k]}' | sort -rn; }
sample() { local t=$(date +%T) l=$(sysctl -n vm.loadavg | tr -d '{}'); local top=$(nonvm); local sum=$(echo "$top" | awk '{s+=$1} END {printf "%.0f", s}'); local t4=$(echo "$top" | head -4 | awk '{printf "%s %s, ", $1, $2}'); echo "$t load $l | sum $sum | $t4"; echo "$sum" > /tmp/hostsum.$$; }
echo "# host load during $name (ps -A, non-VM processes: top 4 by %CPU and the sum of all, every 10 s; loadavg)" > "$out"
waited=0; ok=0
while [ $waited -lt $maxwait ]; do
  sample >> "$out"; s=$(cat /tmp/hostsum.$$)
  if [ "$s" -lt "$quiet" ]; then ok=$((ok+1)); else ok=0; fi
  [ $ok -ge 3 ] && break
  sleep 10; waited=$((waited+10))
done
if [ $ok -ge 3 ]; then echo "# quiet after ${waited}s; session starts" >> "$out"; else echo "# NOT quiet after ${waited}s (sum >= ${quiet}%); session starts anyway" >> "$out"; fi
( while :; do sample >> "$out"; sleep 10; done ) &
sp=$!
colima ssh -- bash -c "$R/scripts/review-round.sh $name $*"
rc=$?
kill $sp 2>/dev/null; wait $sp 2>/dev/null
echo "# session ended $(date +%T), exit $rc" >> "$out"
rm -f /tmp/hostsum.$$
exit $rc
