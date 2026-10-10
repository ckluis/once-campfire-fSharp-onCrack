#!/usr/bin/env bash
# guard.sh PID [FLOOR_GB]: runs inside colima beside a harness session (started detached by run-r32.sh, on the load generator's CPUs).
# Every 20 s it reads the Mac's free space (through the virtiofs mount) and, under FLOOR_GB (12), kills the session and its container.
# It trims the Docker disk only after the session: a trim during a timed sample cost upstream Rust 6% on the room page (a 20 s trim
# loop, 2026-10-09), and the session that ran beside one read Rust, C and the port 30-50% low. Container logs are what grow the
# disk (upstream Rust writes ~1.3 GB a container); cap them in the VM's dockerd (log-opts max-size 64m, max-file 2) before a session.
# Logs to /mnt/cfv/out/guard-PID.log.
pid=$1; floor=$(( ${2:-12} * 1024 * 1024 ))
log=/mnt/cfv/out/guard-$pid.log
while kill -0 "$pid" 2>/dev/null; do
  free=$(df -k /Users/clank | awk 'NR==2 {print $4}')
  echo "$(date +%T) mac_free_gb=$((free / 1024 / 1024))" >> "$log"
  if [ "$free" -lt "$floor" ]; then
    echo "$(date +%T) under the floor: stopping the session" >> "$log"
    kill "$pid"; sleep 2; docker ps -q --filter name=cf-native-bench | xargs -r docker rm -f >/dev/null
    break
  fi
  sleep 20
done
sudo fstrim /var/lib/docker >/dev/null 2>&1
echo "$(date +%T) session $pid ended, disk trimmed" >> "$log"
