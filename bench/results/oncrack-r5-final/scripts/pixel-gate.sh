#!/usr/bin/env bash
# Step 3 of PLAN.md, inside colima, detached: the full pixel gate. The four small seeds in one run, then the default seed in the twelve --only slices of
# pixels/pixel_parity.py (SLICES), one after another. Before each unit the Mac's free space is read through the virtiofs mount (floor 12 GiB: trim, and
# if it is still under, stop). After each unit: dangling images, build cache, fstrim. Per-unit status lines in pixels/status.txt; exit status in pixels/gate.exit.
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack
P=$R/bench/results/oncrack-r5-final/pixels
OUT=$R/parity/out/pixel-parity-r5-final
cd $R; mkdir -p $OUT $P/logs /tmp/parity-net; rm -f $P/gate.exit $P/status.txt
export PIXEL_PARITY_IN_VM=1 PARITY_NET_DIR=/tmp/parity-net
free_gb() { echo $(( $(df -k /Users/clank | awk 'NR==2 {print $4}') / 1024 / 1024 )); }
trim() { docker image prune -f >/dev/null 2>&1; docker buildx prune -f --filter until=10m >/dev/null 2>&1; sudo fstrim /var/lib/docker >/dev/null 2>&1; sync; sudo fstrim -av >/dev/null 2>&1; }
say() { echo "$(date +%T) $*" | tee -a $P/status.txt; }
overall=0
unit() {   # unit NAME ARGS...
  local name=$1; shift
  if [ "$(free_gb)" -lt 12 ]; then trim; fi
  if [ "$(free_gb)" -lt 12 ]; then say "STOP before $name: Mac free $(free_gb) GiB, under the 12 GiB floor"; echo 3 > $P/gate.exit; exit 3; fi
  say "start $name (Mac free $(free_gb) GiB)"
  bin/pixel-parity "$@" > $P/logs/$name.log 2>&1; local rc=$?
  find $R/parity -maxdepth 1 -name 'core*' -exec rm -f {} + 2>/dev/null
  say "end $name exit $rc (Mac free $(free_gb) GiB)"
  [ $rc -eq 0 ] || overall=1
  trim
}
unit small --seeds crowd,custom_styles,first_run,restricted --out $OUT/small
for s in A B C D E F G H I J K L; do
  only=$(python3 - "$s" <<'PY'
import sys, re
src = open('/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r5-final/pixels/pixel_parity.py').read()
ns = {}
exec(re.search(r"^SLICES = \{.*?^\}", src, re.S | re.M).group(0), ns)
print(ns['SLICES'][sys.argv[1]])
PY
)
  unit default-$s --seeds default --only "$only" --out $OUT/$s
done
say "gate done, overall $overall"
echo $overall > $P/gate.exit
