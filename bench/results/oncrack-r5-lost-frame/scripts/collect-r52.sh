#!/usr/bin/env bash
# Unit R5.2: copies the proofs and the cost runs from the VM into data-r52/, inside colima:
#   proof-poh/  /var/tmp/r52-proof   the first fix (426bcef, payloads on the pinned object heap)
#   proof/      /var/tmp/r52b-proof  the kept fix (54fb67f, payloads pinned on the stack)
#   cost-poh/   /var/tmp/r52-cost    the first fix against gather off and round 4's image (cost-r52.sh)
#   arms/       /var/tmp/r52-arms    pre-fix, pinned heap, stack, gather off (arms-r52.sh)
#   final/      /var/tmp/r52-final   the kept fix, gather on against off (arms-r52.sh)
#   alt/        /var/tmp/r52-alt     the two fixes alternated by block, warm, 500 clients: phases.jsonl, env.txt and each phase's `mem:` lines
# Per proof block: env.txt, phases.jsonl, loop.exit, misses.txt (if any), the loop's log, and app-errors.log/verdict.json of every flagged
# phase. Per cost run: bench/run's oncrack-*.json, env.txt and load.txt (the container logs stay in the VM).
set -euo pipefail
OUT=$(cd "$(dirname "$0")/.." && pwd)/data-r52
proof() {
  local src=$1 dst=$OUT/$2; mkdir -p "$dst"
  for b in "$src"/*/; do
    b=${b%/}; name=$(basename "$b"); [ -f "$b/phases.jsonl" ] || continue
    mkdir -p "$dst/$name"
    for f in env.txt phases.jsonl loop.exit misses.txt; do [ -f "$b/$f" ] && cp "$b/$f" "$dst/$name/"; done
    [ -f "$b.log" ] && cp "$b.log" "$dst/$name/block.log"
    for p in "$b"/run*/; do
      if [ -s "$p/app-errors.log" ]; then mkdir -p "$dst/$name/flagged/$(basename "$p")"; cp "$p/app-errors.log" "$p/verdict.json" "$dst/$name/flagged/$(basename "$p")/" 2>/dev/null || true; fi
    done
  done
  cp "$src/proof.log" "$dst/" 2>/dev/null || true
}
runs() {
  local src=$1 dst=$OUT/$2; mkdir -p "$dst"
  for d in "$src"/r*/; do
    d=${d%/}; name=$(basename "$d"); mkdir -p "$dst/$name"
    cp "$d"/oncrack-*.json "$d"/env.txt "$d"/load.txt "$dst/$name/" 2>/dev/null || true
  done
  cp "$src"/*.log "$dst/" 2>/dev/null || true
}
[ -d /var/tmp/r52-proof ] && proof /var/tmp/r52-proof proof-poh
[ -d /var/tmp/r52b-proof ] && proof /var/tmp/r52b-proof proof
[ -d /var/tmp/r52-cost ] && runs /var/tmp/r52-cost cost-poh
[ -d /var/tmp/r52-arms ] && runs /var/tmp/r52-arms arms
[ -d /var/tmp/r52-final ] && runs /var/tmp/r52-final final
if [ -d /var/tmp/r52-alt ]; then
  for b in /var/tmp/r52-alt/*/; do
    b=${b%/}; name=$(basename "$b"); [ -f "$b/phases.jsonl" ] || continue
    mkdir -p "$OUT/alt/$name"; cp "$b/env.txt" "$b/phases.jsonl" "$OUT/alt/$name/"
    for p in "$b"/run*/; do
      [ -f "$p/app.log" ] || continue
      mkdir -p "$OUT/alt/$name/$(basename "$p")"; grep 'mem:' "$p/app.log" > "$OUT/alt/$name/$(basename "$p")/mem.log" || true
    done
  done
  cp /var/tmp/r52-alt/proof.log "$OUT/alt/" 2>/dev/null || true
fi
du -sh "$OUT"
