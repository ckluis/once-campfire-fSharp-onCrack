#!/usr/bin/env bash
# run-r33.sh NAME [bin/benchmark args...]: one detached harness session, output in /mnt/cfv/out/NAME, log in /mnt/cfv/out/NAME.log, pid in NAME.pid,
# with guard.sh beside it (stops the session under 12 GB free on the Mac, trims after it)
name=$1; shift
source /Users/clank/Desktop/projects/upstream-campfire/scripts/env-r33.sh
umask 002
setsid nohup $BENCH --output /mnt/cfv/out/$name "$@" > /mnt/cfv/out/$name.log 2>&1 < /dev/null &
pid=$!
echo $pid > /mnt/cfv/out/$name.pid
setsid nohup taskset -c 4-7 /Users/clank/Desktop/projects/upstream-campfire/scripts/guard.sh $pid > /dev/null 2>&1 < /dev/null &
echo "started $name pid $pid, guard $!"
