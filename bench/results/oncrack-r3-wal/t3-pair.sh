#!/usr/bin/env bash
# Unit R3.4: one rep of post_message at c=16 and c=64 for the shipped WAL policy and for R2.2's (CAMPFIRE_WAL_DEFER=off), on the
# rebuilt image, this suite's full warm-up (30-90 s until flat); the order alternates by rep (on/off, off/on, on/off).
#   colima ssh -- bash -c "cd REPO && bench/results/oncrack-r3-wal/t3-pair.sh REP"
set -euo pipefail
rep=$1
run() {
  ONCRACK_EXTRA_ENV="$2" bench/quick --routes post_message --concs "16 64" --reps 1 --out "bench/results/oncrack-r3-wal/t3-$1-$rep" \
    >"bench/results/oncrack-r3-wal/t3-$1-$rep.txt" 2>&1 || { tail -20 "bench/results/oncrack-r3-wal/t3-$1-$rep.txt"; exit 1; }
}
# The image at 1efc805 shipped the deferred restart on by default; from 4ac9b2b it is an opt-in, so it is asked for by name.
# `ceiling` (t3-ceiling-REP) is the opt-in with a 150,000-frame ceiling: bench/results/oncrack-r3-wal/t3-pair.sh REP ceiling
if [ "${2-}" = ceiling ]; then run ceiling "CAMPFIRE_WAL_DEFER=on CAMPFIRE_WAL_CEILING_PAGES=150000"; exit; fi
# `ceilpair`: the 150,000-frame opt-in and R2.2's restart in one call, alternating by rep (t3-ceiling-REP, t3-r22-REP).
if [ "${2-}" = ceilpair ]; then
  if [ $((rep % 2)) = 1 ]; then run ceiling "CAMPFIRE_WAL_DEFER=on CAMPFIRE_WAL_CEILING_PAGES=150000"; run r22 "CAMPFIRE_WAL_DEFER=off"
  else run r22 "CAMPFIRE_WAL_DEFER=off"; run ceiling "CAMPFIRE_WAL_DEFER=on CAMPFIRE_WAL_CEILING_PAGES=150000"; fi
  exit
fi
if [ $((rep % 2)) = 1 ]; then run defer "CAMPFIRE_WAL_DEFER=on"; run r22 "CAMPFIRE_WAL_DEFER=off"; else run r22 "CAMPFIRE_WAL_DEFER=off"; run defer "CAMPFIRE_WAL_DEFER=on"; fi
