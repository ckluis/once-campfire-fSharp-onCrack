#!/usr/bin/env bash
# gocache-watch.sh EXITFILE: on the Mac, beside a detached session. Every 15 s: if the Mac has under 14 GiB free and no go, compile or link
# process is running, `go clean -cache` (another project's Go build cache is what took the Mac under the 12 GiB floor twice in round 5; the
# rule allows exactly this). Logs each clean to reliability/gocache-watch.log. Ends when EXITFILE exists.
ef=$1; log=$(dirname "$0")/gocache-watch.log
while [ ! -f "$ef" ]; do
  free=$(df -k /Users/clank | awk 'NR==2 {printf "%.1f", $4/1024/1024}')
  if awk -v f="$free" 'BEGIN {exit !(f < 14)}' && ! pgrep -x 'go|compile|link|gopls' > /dev/null; then
    before=$(du -sh ~/Library/Caches/go-build 2>/dev/null | cut -f1)
    go clean -cache 2>/dev/null
    echo "$(date +%T) free $free GiB, no go process: go clean -cache (cache was $before)" >> "$log"
  fi
  sleep 15
done
