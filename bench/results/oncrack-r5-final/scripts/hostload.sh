#!/usr/bin/env bash
# hostload.sh NAME CMD...: on the Mac. Waits for a quiet host (non-VM CPU under 100% for 3 samples 10 s apart, at most 600 s), samples the
# host every 10 s into host-load-NAME.txt (top 4 non-VM processes, their sum, load average), runs CMD in the foreground, stops the sampler.
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
if [ $ok -ge 3 ]; then echo "# quiet after ${waited}s; session starts" >> "$out"; else echo "# NOT quiet after ${waited}s (sum >= 100%); session starts anyway" >> "$out"; fi
( while :; do sample >> "$out"; sleep 10; done ) &
sp=$!
"$@"
rc=$?
kill $sp 2>/dev/null; wait $sp 2>/dev/null
echo "# session ended $(date +%T), exit $rc" >> "$out"
rm -f /tmp/hostsum.$$
exit $rc
