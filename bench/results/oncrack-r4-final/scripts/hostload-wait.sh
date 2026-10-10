#!/usr/bin/env bash
# hostload-wait.sh NAME EXITFILE [MAXSECS]: on the Mac. Appends the host sample (as hostload.sh) every 10 s to host-load-NAME.txt until EXITFILE
# exists or MAXSECS (540) pass, so a session detached in the VM can be waited on in chunks under the Bash tool's 10 minutes. The first call of a
# session is made with FIRST=1 (waits for a quiet host as hostload.sh does, writes the header).
name=$1; ef=$2; max=${3:-540}
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r4-final
out=$R/host-load-$name.txt
nonvm() { ps -Ao pcpu,comm | awk 'NR>1 && $2 !~ /Virtualization|limactl|colima|ssh/ {c=$1; $1=""; sub(/^ /,""); k=split($0,p,"/"); printf "%s %s\n", c, p[k]}' | sort -rn; }
sample() { local t=$(date +%T) l=$(sysctl -n vm.loadavg | tr -d '{}'); local top=$(nonvm); local sum=$(echo "$top" | awk '{s+=$1} END {printf "%.0f", s}'); local t4=$(echo "$top" | head -4 | awk '{printf "%s %s, ", $1, $2}'); echo "$t load $l | sum $sum | $t4"; }
[ -n "$FIRST" ] && echo "# host load during $name (ps -A, non-VM processes: top 4 by %CPU and the sum of all, every 10 s; loadavg)" > "$out"
[ -n "$FIRST" ] && echo "# quiet after 0s; session starts" >> "$out"
t=0
while [ ! -f "$ef" ] && [ $t -lt $max ]; do sample >> "$out"; sleep 10; t=$((t+10)); done
[ -f "$ef" ] && echo "# session ended $(date +%T), exit $(cat $ef)" >> "$out"
exit 0
