#!/usr/bin/env bash
# Wait (at most ~6 min) for the VM's 1-minute load average to drop under 1.5, so a part does not spend its own time limit waiting.
w=0; while awk '{exit !($1 >= 1.5)}' /proc/loadavg && [ $w -lt 360 ]; do sleep 10; w=$((w+10)); done
echo "waited ${w}s: $(cut -d' ' -f1-3 /proc/loadavg)"; df -h /Users/clank | tail -1
