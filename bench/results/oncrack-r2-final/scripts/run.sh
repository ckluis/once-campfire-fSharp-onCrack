#!/usr/bin/env bash
# run.sh NAME [bin/benchmark args...]: one detached harness session, output in /mnt/cfv/out/NAME, log in /mnt/cfv/out/NAME.log
name=$1; shift
source /Users/clank/Desktop/projects/upstream-campfire/scripts/env.sh
umask 002
setsid nohup $BENCH --output /mnt/cfv/out/$name "$@" > /mnt/cfv/out/$name.log 2>&1 < /dev/null &
echo "started $name pid $!"
