#!/usr/bin/env bash
# onCrack round 1 review: decoded bodies of the benchmarked routes from Rust's and onCrack's parity images, the same seed, the
# same port, the clock frozen at 2026-03-02T16:00Z, unmasked; then their SHA-256. Inside colima:
#   bench/results/oncrack-round1-final/review/bytes.sh
# The bodies (bytes-APP/) are kept only for the comparison; each app's summary.json is committed as bytes-APP.json.
set -euo pipefail
cd /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack
R=bench/results/oncrack-round1-final/review
export PARITY_NET_DIR=/tmp/parity-net; mkdir -p "$PARITY_NET_DIR"
for app in rust oncrack; do
  PARITY_CANDIDATE_APP=$app parity/bin/candidate up --seed default --port 4312 --time 2026-03-02T16:00:00Z --freeze >/dev/null
  rm -rf "$R/bytes-$app"; python3 "$R/bytes.py" http://127.0.0.1:4312 "$R/bytes-$app" > /dev/null
  PARITY_CANDIDATE_APP=$app parity/bin/candidate down --port 4312 >/dev/null
done
(cd "$R" && sha256sum bytes-rust/* bytes-oncrack/* | grep -v summary.json) | tee "$R/bytes-sha256.txt"
python3 - "$R" <<'PY'
import hashlib, os, sys
r = sys.argv[1]
for f in sorted(os.listdir(f"{r}/bytes-rust")):
    if f == "summary.json": continue
    a, b = (open(f"{r}/bytes-{x}/{f}", "rb").read() for x in ("rust", "oncrack"))
    print(f"{f}: {'IDENTICAL' if a == b else 'DIFFERENT'} ({len(a)} / {len(b)} bytes)")
PY
