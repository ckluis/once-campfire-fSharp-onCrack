#!/usr/bin/env bash
# Unit R5.3: what one delivery puts on the wire. Inside colima, like bench/cable/perf:
#   ONCRACK_MOUNT=DIR [ONCRACK_EXTRA_ENV="K=V"] netab.sh CLIENTS OUTFILE
# Starts the app, runs a short warm-up, then a saturated fan-out; over 4 s of the saturated phase it reads the VM's TCP counters
# (/proc/net/snmp OutSegs, /proc/net/netstat OutOctets) and the app's sendmsg count (perf stat), and prints them per delivery.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)
CLIENTS=$1 OUTF=$2
set --
export SERVER_CPUS=${SERVER_CPUS:-0-3} LOADGEN_CPUS=${LOADGEN_CPUS:-4-7} WORK=${WORK:-/var/tmp/campfire-bench-work}
BENCH_RUN_LIB=1 source "$ROOT/bench/run"
wait_for_quiet
start_app oncrack >/dev/null
PID=$(docker inspect -f '{{.State.Pid}}' "$CONTAINER")
sleep 3
cookie=$(lg login --base "$BASE" --email "$EMAIL" --password "$PASSWORD" | python3 -c 'import json,sys; print(json.load(sys.stdin)["cookie"])')
scrape=$(lg scrape --base "$BASE" --cookie "$cookie" --room "$ROOM")
csrf=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["csrf"] or "")' "$scrape")
streams=$(python3 -c 'import json,sys; print(",".join(json.loads(sys.argv[1])["streams"]))' "$scrape")
D=$(mktemp -d)
lg cable --base "$BASE" --cookie "$cookie" --room "$ROOM" --csrf "$csrf" --streams "$streams" --clients "$CLIENTS" --tput-secs 8 --posters 4 > "$D/warm.json" 2>/dev/null
lg cable --base "$BASE" --cookie "$cookie" --room "$ROOM" --csrf "$csrf" --streams "$streams" --clients "$CLIENTS" --tput-secs 22 --posters 4 > "$D/run.json" 2> "$D/run.stderr" &
lgpid=$!
for _ in $(seq 1 600); do grep -q 'PHASE saturated ' "$D/run.stderr" 2>/dev/null && break; sleep 0.1; done
sleep 4
snap() { awk '/^Tcp:/ && !h {h=1; next} /^Tcp:/ {print "OutSegs", $12}' /proc/net/snmp; awk '/^IpExt:/ && !h {for(i=1;i<=NF;i++) if ($i=="OutOctets") c=i; h=1; next} /^IpExt:/ {print "OutOctets", $c}' /proc/net/netstat; }
snap > "$D/a"
sudo perf stat -x, -e 'syscalls:sys_enter_sendmsg' -p "$PID" -o "$D/perf.csv" -- sleep 4 >/dev/null 2>&1 || true
snap > "$D/b"
wait "$lgpid"
python3 - "$D" "$OUTF" "$CLIENTS" <<'PY'
import json, sys
d, outf, clients = sys.argv[1], sys.argv[2], int(sys.argv[3])
rate = json.load(open(d + '/run.json'))['throughput']['delivered_msgs_per_sec']
a = dict(l.split() for l in open(d + '/a')); b = dict(l.split() for l in open(d + '/b'))
sends = next(int(l.split(',')[0]) for l in open(d + '/perf.csv') if 'sendmsg' in l)
dl = rate * clients * 4
segs = (int(b['OutSegs']) - int(a['OutSegs'])) / dl; octets = (int(b['OutOctets']) - int(a['OutOctets'])) / dl
line = f"{clients} clients {rate:.0f} msgs/s: sendmsg/delivery {sends / dl:.4f}  segments/delivery {segs:.4f}  octets/delivery {octets:.0f}  octets/segment {octets / segs:.0f}"
print(line); open(outf, 'a').write(line + '\n')
PY
docker rm -f "$CONTAINER" >/dev/null; rm -rf "${WORK:?}/oncrack" "$D"
