#!/usr/bin/env bash
# The R5.1 hunt, inside colima, detached: block after block (scripts/block.sh), each its own directory under /var/tmp/r5-lost-frame/.
# Starts with the blocks that matter most (onCrack, default configuration), then the controls. Writes /var/tmp/r5-lost-frame/hunt.done
# when the last block has ended. Disk: stops before a block when the VM's /var/tmp has under 4 GB free.
set -uo pipefail
B=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-lost-frame/scripts/block.sh
rm -f /var/tmp/r5-lost-frame/hunt.done
run() {
  local free; free=$(df -k /var/tmp | awk 'NR==2 {printf "%d", $4/1024/1024}')
  if [ "$free" -lt 4 ]; then echo "STOP: /var/tmp has ${free} GB free before $1" >> /var/tmp/r5-lost-frame/hunt.log; return 1; fi
  echo "$(date +%T) block $1 start" >> /var/tmp/r5-lost-frame/hunt.log
  "$B" "$@"
  echo "$(date +%T) block $1 end" >> /var/tmp/r5-lost-frame/hunt.log
}
mkdir -p /var/tmp/r5-lost-frame
for spec in "$@"; do
  # spec: NAME|loop arguments
  name=${spec%%|*}; args=${spec#*|}
  # shellcheck disable=SC2086
  run "$name" $args || break
done
touch /var/tmp/r5-lost-frame/hunt.done
