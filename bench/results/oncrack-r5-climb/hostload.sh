#!/bin/sh
# Mac side: one sample every 30 s (time, load average, non-VM CPU %, free GiB) until .exit4 exists. Evidence for which reps the host disturbed.
D=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-climb
echo "# time loadavg nonvm_cpu_pct mac_free_gib" > $D/host-load-climb4.txt
while [ ! -f $D/.exit4 ]; do
  s=$(ps -Ao pcpu,comm | awk 'NR>1 && $2 !~ /Virtualization|limactl|colima|ssh/ {s+=$1} END {printf "%d", s}')
  echo "$(date +%T) $(sysctl -n vm.loadavg | tr -d '{}') $s $(df -k /Users/clank | awk 'NR==2{printf "%.1f", $4/1024/1024}')" >> $D/host-load-climb4.txt
  sleep 30
done
