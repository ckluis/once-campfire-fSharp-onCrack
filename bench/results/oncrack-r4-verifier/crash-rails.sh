#!/usr/bin/env bash
# Round 4 verifier: kill -9 mid group commit, then (1) SQLite's and FTS5's integrity checks and the search index matching every stored
# post, (2) Rails (campfire-reference:app) reading and searching the database onCrack wrote and writing a post of its own, (3) onCrack
# starting again on it and finding Rails' post on the room page and in search. Run inside colima from the repo root:
#   colima ssh -- bash -c "cd $PWD && bench/results/oncrack-r4-verifier/crash-rails.sh [KILL_AFTER]"
set -uo pipefail
port=4399 name=campfire-candidate-4399 dir=parity/.seed/.candidates/4399 room=486777696
parity/bin/candidate up --seed default --port $port >/dev/null || exit 1
out=$(python3 bench/results/oncrack-verifier/killtest.py $port $dir/db/production.sqlite3 $name "${1:-5}"); status=$?
echo "$out"
run=$(echo "$out" | sed -n 's/^run \([0-9a-f]*\):.*/\1/p')
echo "killtest exit=$status run=$run"
python3 - "$dir/db/production.sqlite3" "$run" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1]); run = sys.argv[2]
print("pragma integrity_check:", db.execute("pragma integrity_check").fetchone()[0])
db.execute("insert into message_search_index(message_search_index) values('integrity-check')"); print("fts5 integrity-check: ok")
stored = db.execute("select count(*) from action_text_rich_texts where record_type='Message' and body like ?", (f"%kt{run}p%",)).fetchone()[0]
matched = db.execute("select count(*) from message_search_index where message_search_index match ?", (f"kt{run}*",)).fetchone()[0]
print(f"stored posts {stored}, matched by the index {matched}")
sys.exit(0 if stored == matched and stored > 0 else 1)
PY
echo "index exit=$?"
parity/bin/reference exec --storage $dir bin/rails runner "
  q = 'kt$run*'
  puts \"rails: messages matching #{q}: #{Message.search(q).count}\"
  david = User.find_by!(email_address: 'david@37signals.com')
  m = Room.find($room).messages.create!(creator: david, body: 'rails wrote this after the crash rl$run')
  puts \"rails: created message #{m.id}; matching rl$run: #{Message.search('rl$run').count}\"
  puts \"rails: room page messages #{Room.find($room).messages.count}\"
" 2>&1 | grep -v "^W, \|warning" | tail -5
docker start $name >/dev/null
for i in $(seq 1 120); do curl -fsS -o /dev/null http://127.0.0.1:$port/up 2>/dev/null && break; sleep 0.25; done
python3 - $port $room "$run" <<'PY'
import http.client, sys, urllib.parse
port, room, run = int(sys.argv[1]), sys.argv[2], sys.argv[3]
c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
c.request("POST", "/session", urllib.parse.urlencode({"email_address": "david@37signals.com", "password": "secret123456"}),
          {"Content-Type": "application/x-www-form-urlencoded", "Sec-Fetch-Site": "same-origin"})
r = c.getresponse(); r.read(); cookie = "; ".join(h.split(";")[0] for k, h in r.getheaders() if k.lower() == "set-cookie")
c.request("GET", f"/rooms/{room}", headers={"Cookie": cookie, "Accept": "text/html"}); r = c.getresponse(); page = r.read().decode()
print(f"oncrack after rails: room page {r.status}, rails' post on it: {('rl' + run) in page}")
c.request("GET", f"/searches?q=rl{run}", headers={"Cookie": cookie, "Accept": "text/html"}); r = c.getresponse(); page = r.read().decode()
print(f"oncrack after rails: search {r.status}, rails' post found: {('rl' + run) in page}")
sys.exit(0 if ("rl" + run) in page else 1)
PY
echo "roundtrip exit=$?"
parity/bin/candidate down $port
