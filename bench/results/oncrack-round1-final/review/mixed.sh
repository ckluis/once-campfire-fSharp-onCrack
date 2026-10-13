#!/usr/bin/env bash
# onCrack round 1 review: the room page read while the same room is written to. bench/run's read workloads never write, so onCrack's
# read cache answers every request from a stored page; this is the other end: one connection posts to the room being read as fast as
# the app answers (every post moves the room's counter, so most reads find the page stale and render it), while 16 connections read
# that room's page. 30 s of both together as a warm-up, then a 15 s window of both; CPU from cpu.stat covers both. Rows counted in SQLite.
#   bench/results/oncrack-round1-final/review/mixed.sh APP   (rust|fsharp|oncrack), inside colima. Built from manual.sh.
set -euo pipefail
cd /Users/clank/Desktop/projects/once-campfire-fsharp-oncrack
APP=$1 PORT=4395 NAME=mixed-$1
case "$APP" in rust) IMAGE=campfire-rust:app ;; fsharp) IMAGE=campfire-fsharp:app ;; oncrack) IMAGE=campfire-oncrack:app ;; *) echo "app: rust|fsharp|oncrack" >&2; exit 2 ;; esac
LG=target/rust/aarch64-unknown-linux-gnu/release/loadgen
W=/var/tmp/campfire-mixed/$APP
rm -rf "$W"; mkdir -p "$W/db" "$W/storage"
cp -a parity/.seed/default/db/. "$W/db/"; cp -a parity/.seed/default/storage/. "$W/storage/"
python3 - "$W/db/production.sqlite3" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
db.execute("UPDATE push_subscriptions SET endpoint = 'https://127.0.0.1:9/push/' || id")
db.execute("UPDATE webhooks SET url = 'http://127.0.0.1:9/hook/' || id")
db.commit()
PY
args=(); while IFS= read -r l; do args+=("$l"); done < <(grep -Ev '^(#|$|WEB_CONCURRENCY|JOB_CONCURRENCY|RAILS_MAX_THREADS|RAILS_LOG_LEVEL)' parity/.env.reference | sed 's/^/-e\n/')
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" --cpuset-cpus 0-3 --user "$(id -u):$(id -g)" --log-driver json-file --log-opt max-size=512m --log-opt max-file=4 --network host \
  -e HTTP_PORT=$PORT -e TARGET_PORT=$((PORT + 1)) "${args[@]}" -e WEB_CONCURRENCY=3 -e JOB_CONCURRENCY=3 -e RAILS_MAX_THREADS=5 -e RAILS_LOG_LEVEL=warn \
  -v "$W/db:/rails/storage/db" -v "$W/storage:/rails/storage/files" "$IMAGE" >/dev/null
for _ in $(seq 1 500); do curl -fsS -o /dev/null http://127.0.0.1:$PORT/up 2>/dev/null && break; sleep 0.02; done
echo "image: $(docker inspect -f '{{.Image}}' "$NAME") revision: $(docker image inspect -f '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$IMAGE")"
CG=/sys/fs/cgroup/docker/$(docker inspect -f '{{.Id}}' "$NAME"); [ -d "$CG" ] || CG=/sys/fs/cgroup/system.slice/docker-$(docker inspect -f '{{.Id}}' "$NAME").scope
L=$(python3 -c 'import json;print(json.dumps(json.load(open("parity/.seed/default/labels.json"))))')
lab() { python3 -c 'import json,sys;print(json.loads(sys.argv[1])[sys.argv[2]])' "$L" "$1"; }
ROOM=$(lab rooms.watercooler) WROOM=$(lab rooms.hq)
COOKIE=$($LG login --base http://127.0.0.1:$PORT --email "$(lab emails.david)" --password "$(lab passwords.all)" | python3 -c 'import json,sys;print(json.load(sys.stdin)["cookie"])')
CSRF=$($LG scrape --base http://127.0.0.1:$PORT --cookie "$COOKIE" --room "$ROOM" | python3 -c 'import json,sys;print(json.load(sys.stdin)["csrf"] or "")')
rows() { python3 -c 'import sqlite3,sys;print(sqlite3.connect(sys.argv[1],timeout=30).execute("select count(*) from messages where room_id=?",(int(sys.argv[2]),)).fetchone()[0])' "$W/db/production.sqlite3" "$WROOM"; }
loglines() { docker logs --since "$1" --until "$2" "$NAME" 2>&1 | grep -c 'Request.*path' || true; }
usage() { awk '$1=="usage_usec"{print $2}' "$CG/cpu.stat"; }
rrows() { python3 -c 'import sqlite3,sys;print(sqlite3.connect(sys.argv[1],timeout=30).execute("select count(*) from messages where room_id=?",(int(sys.argv[2]),)).fetchone()[0])' "$W/db/production.sqlite3" "$ROOM"; }
both() {   # both SECS: reader c=16 on the room page and poster c=1 into the same room, together
  taskset -c 4-7 $LG http --base http://127.0.0.1:$PORT --cookie "$COOKIE" --post-room "$ROOM" --csrf "$CSRF" --conc 1 --duration "$1" > "$W/post.json" &
  local p=$!
  taskset -c 4-7 $LG http --base http://127.0.0.1:$PORT --cookie "$COOKIE" --path "/rooms/$ROOM" --conc 16 --duration "$1" > "$W/read.json"
  wait $p
}
both 30
sleep 1
r0=$(rrows); u0=$(usage); t0=$(date +%s.%N)
both 15
u1=$(usage); t1=$(date +%s.%N); sleep 1; r1=$(rrows)
python3 - "$APP" "$W/read.json" "$W/post.json" "$u0" "$u1" "$t0" "$t1" "$r0" "$r1" "$(cut -d' ' -f1-3 /proc/loadavg)" "$(python3 bench/lib/hostprobe.py 0-3,4-7 /var/tmp/campfire-bench-work/.hostprobe-baseline)" <<'PY'
import json, sys
app, rf, pf, u0, u1, t0, t1, r0, r1, load, probe = sys.argv[1:]
rd, po = json.load(open(rf)), json.load(open(pf)); wall = float(t1) - float(t0); n = rd["latency"]["n"] + po["latency"]["n"]
print(json.dumps({"app": app, "read_rps": rd["rps"], "read_statuses": rd["statuses"], "read_errors": rd["errors"], "read_p50": rd["latency"].get("p50_ms"),
  "read_p99": rd["latency"].get("p99_ms"), "read_bytes": rd.get("avg_bytes"), "post_rps": po["rps"], "post_statuses": po["statuses"], "post_errors": po["errors"],
  "rows_written": int(r1) - int(r0), "posts_ok": po["latency"]["n"], "cpu_us_per_req_all": round((int(u1) - int(u0)) / n, 1),
  "cores_busy": round((int(u1) - int(u0)) / 1e6 / wall, 2), "loadavg_after": load, "host_probe_after": json.loads(probe)["ratio"]}))
PY
docker rm -f "$NAME" >/dev/null; rm -rf "$W"
