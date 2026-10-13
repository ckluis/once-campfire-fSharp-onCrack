#!/usr/bin/env bash
# netab.sh over arms, detached: OUT=FILE netab-run.sh CLIENTS "NAME|ENV" ...   (MOUNT env: bin/publish-mounted dir)
cd "$(dirname "${BASH_SOURCE[0]}")/../../../.."
for spec in "${@:2}"; do
  name=${spec%%|*}; env=${spec#*|}
  echo "== $name" >> "$OUT"
  ONCRACK_MOUNT="$MOUNT" ONCRACK_EXTRA_ENV="$env" bench/results/oncrack-r5-fanout/scripts/netab.sh "$1" "$OUT" > "$OUT.$name.log" 2>&1
  echo "$name exit $?" >> "$OUT"
done
touch "$OUT.done"
