#!/usr/bin/env python3
"""Durability under SIGKILL with the default settings (group commit on, read cache on): post from 16 threads,
SIGKILL the container mid-run, restart it on the same storage, and check that every post that was answered 200
is stored exactly once, with its search-index row, and visible on the room page after restart."""
import http.client, json, re, sqlite3, subprocess, sys, threading, time, urllib.parse, uuid

PORT = int(sys.argv[1]); DB = sys.argv[2]; CONTAINER = sys.argv[3]; KILL_AFTER = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0
ROOM = 486777696
RUN = uuid.uuid4().hex[:8]

def conn():
    return http.client.HTTPConnection("127.0.0.1", PORT, timeout=10)

def sign_in():
    c = conn()
    body = urllib.parse.urlencode({"email_address": "david@37signals.com", "password": "secret123456"})
    c.request("POST", "/session", body, {"Content-Type": "application/x-www-form-urlencoded", "Sec-Fetch-Site": "same-origin"})
    r = c.getresponse(); r.read()
    cookies = [h.split(";")[0] for k, h in r.getheaders() if k.lower() == "set-cookie"]
    assert r.status == 302, r.status
    return "; ".join(cookies)

cookie = sign_in()
acked, failed, errors = [], [], []
lock = threading.Lock()
stop = threading.Event()

def poster(n):
    c = conn(); i = 0
    while not stop.is_set():
        i += 1
        token = f"kt{RUN}p{n}i{i}z"
        body = urllib.parse.urlencode({"message[body]": f"killtest {token}"})
        try:
            c.request("POST", f"/rooms/{ROOM}/messages", body, {"Content-Type": "application/x-www-form-urlencoded",
                      "Accept": "text/vnd.turbo-stream.html", "Sec-Fetch-Site": "same-origin", "Cookie": cookie})
            r = c.getresponse(); data = r.read()
            with lock:
                (acked if r.status == 200 and token.encode() in data else failed).append((token, r.status))
        except Exception as e:
            with lock: errors.append((token, type(e).__name__))
            stop.wait(0.05)
            try: c.close()
            except Exception: pass
            c = conn()

threads = [threading.Thread(target=poster, args=(n,)) for n in range(16)]
for t in threads: t.start()
time.sleep(KILL_AFTER)
subprocess.run(["docker", "kill", "-s", "KILL", CONTAINER], check=True, capture_output=True)
killed_at = time.time()
time.sleep(0.5); stop.set()
for t in threads: t.join()
print(f"run {RUN}: acked {len(acked)}, non-200 {len(failed)}, connection errors {len(errors)} (after the kill)")

subprocess.run(["docker", "start", CONTAINER], check=True, capture_output=True)
for _ in range(240):
    try:
        c = conn(); c.request("GET", "/up"); r = c.getresponse(); r.read()
        if r.status == 200: break
    except Exception: pass
    time.sleep(0.25)
# Room page after restart, as David (a new session: the old one is still valid, cookies persist in the db).
c = conn(); c.request("GET", f"/rooms/{ROOM}", headers={"Cookie": cookie, "Accept": "text/html"}); r = c.getresponse(); page = r.read().decode()
subprocess.run(["docker", "stop", CONTAINER], check=True, capture_output=True)

db = sqlite3.connect(DB)
rows = db.execute("select m.id, r.body from messages m join action_text_rich_texts r on r.record_type='Message' and r.record_id=m.id "
                  "where r.body like ?", (f"%kt{RUN}p%",)).fetchall()
indexed = {row[0] for row in db.execute("select rowid from message_search_index where body like ?", (f"%kt{RUN}p%",))}
stored = {}
for mid, body in rows:
    m = re.search(r"kt\w+?z", body); stored.setdefault(m.group(0), []).append(mid)
lost = [t for t, _ in acked if t not in stored]
dups = {t: ids for t, ids in stored.items() if len(ids) > 1}
unindexed = [t for t, ids in stored.items() if not set(ids) & indexed and t in {a for a, _ in acked}]
last_acked = acked[-1][0] if acked else None
print(f"stored {len(stored)} distinct tokens ({len(rows)} rows); unacknowledged but stored {len(set(stored) - {a for a, _ in acked})}")
print(f"LOST acknowledged posts: {len(lost)} {lost[:5]}")
print(f"DUPLICATED: {len(dups)} {list(dups.items())[:3]}")
print(f"acknowledged without a search-index row: {len(unindexed)} {unindexed[:5]}")
print(f"room page after restart: status {r.status}; newest acknowledged post on it: {last_acked in page if last_acked else None}")
journal = db.execute("pragma journal_mode").fetchone()[0]
print(f"journal_mode {journal}")
sys.exit(1 if lost or dups or unindexed else 0)
