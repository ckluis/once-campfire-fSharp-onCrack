#!/usr/bin/env python3
"""No-timestamp (and timestamped) foreign SQL edits from another SQLite connection, revoked sessions and memberships, stale
conditionals. Each case: fresh container, sign in, warm the page 5 times (read cache stored, fast path offered and replayed),
edit from a separate connection, then request once at once and once 1.5 s later."""
import json, sys, time
from lib import *

def now():
    return time.strftime("%Y-%m-%d %H:%M:%S.000000", time.gmtime())

def warm(c, path, n=5):
    for _ in range(n):
        r = c.get(path)
    return r

CASES = {}
def case(f): CASES[f.__name__] = f; return f

@case
def room_rename(a, c):
    p = f"/rooms/{DESIGNERS}"; warm(c, p); warm(c, "/users/me/sidebar")
    a.foreign(("UPDATE rooms SET name='FRoomZ1' WHERE id=?", (DESIGNERS,)))
    return [("room page", p, lambda r: "FRoomZ1" in r.text), ("sidebar", "/users/me/sidebar", lambda r: "FRoomZ1" in r.text)]

@case
def body_edit(a, c):
    m, _ = latest_message(a, DESIGNERS); p = f"/rooms/{DESIGNERS}"; warm(c, p); warm(c, f"/rooms/{DESIGNERS}/@{m}")
    a.foreign(("UPDATE action_text_rich_texts SET body='<p>FBodyZ2</p>' WHERE record_type='Message' AND record_id=?", (m,)))
    return [("room page", p, lambda r: "FBodyZ2" in r.text), ("permalink", f"/rooms/{DESIGNERS}/@{m}", lambda r: "FBodyZ2" in r.text)]

@case
def creator_change(a, c):
    m, _ = latest_message(a, DESIGNERS); p = f"/rooms/{DESIGNERS}"; warm(c, p)
    a.foreign(("UPDATE messages SET creator_id=? WHERE id=?", (LOU, m)))
    return [("room page", p, lambda r: "Lonely Lou" in r.text)]

@case
def creator_rename(a, c):
    m, creator = latest_message(a, DESIGNERS); p = f"/rooms/{DESIGNERS}"; warm(c, p)
    a.foreign(("UPDATE users SET name='FUserZ4' WHERE id=?", (creator,)))
    return [("room page", p, lambda r: "FUserZ4" in r.text)]

@case
def boost_insert(a, c):
    m, _ = latest_message(a, DESIGNERS); p = f"/rooms/{DESIGNERS}"; warm(c, p)
    t = now()
    a.foreign(("INSERT INTO boosts (booster_id, content, created_at, message_id, updated_at) VALUES (?, 'FBoostZ3', ?, ?, ?)", (LOU, t, m, t)))
    return [("room page", p, lambda r: "FBoostZ3" in r.text)]

@case
def boost_update(a, c):
    p = f"/rooms/{DESIGNERS}"; warm(c, p)
    a.foreign("UPDATE boosts SET content='FBoostZ6' WHERE message_id IN (SELECT id FROM messages WHERE room_id=654632876)")
    return [("room page", p, lambda r: "FBoostZ6" in r.text)]

@case
def new_message_with_timestamps(a, c):
    p = f"/rooms/{DESIGNERS}"; warm(c, p)
    t = now(); db = a.db()
    db.execute("BEGIN IMMEDIATE")
    cur = db.execute("INSERT INTO messages (client_message_id, created_at, creator_id, room_id, updated_at) VALUES ('foreign-1', ?, ?, ?, ?)", (t, JASON, DESIGNERS, t))
    mid = cur.lastrowid
    db.execute("INSERT INTO action_text_rich_texts (name, body, record_type, record_id, created_at, updated_at) VALUES ('body', '<p>FNewZ5</p>', 'Message', ?, ?, ?)", (mid, t, t))
    db.execute("UPDATE rooms SET updated_at=? WHERE id=?", (t, DESIGNERS))
    db.execute("COMMIT"); db.close()
    return [("room page", p, lambda r: "FNewZ5" in r.text)]

@case
def session_deleted(a, c):
    p = f"/rooms/{DESIGNERS}"; warm(c, p)
    a.foreign(("DELETE FROM sessions WHERE user_id=?", (KEVIN,)))
    return [("room page", p, lambda r: r.status in (302, 303) and "/session/new" in (r.h("location") or ""))]

@case
def session_token_rotated(a, c):
    p = f"/rooms/{DESIGNERS}"; warm(c, p)
    a.foreign(("UPDATE sessions SET token='rotated-token-x' WHERE user_id=?", (KEVIN,)))
    return [("room page", p, lambda r: r.status in (302, 303) and "/session/new" in (r.h("location") or ""))]

@case
def membership_deleted(a, c):
    p = f"/rooms/{DESIGNERS}"; warm(c, p)
    a.foreign(("DELETE FROM memberships WHERE user_id=? AND room_id=?", (KEVIN, DESIGNERS)))
    return [("room page", p, lambda r: r.status != 200 and "Designers" not in r.text)]

@case
def membership_deleted_messages(a, c):
    p = f"/rooms/{DESIGNERS}/messages"; warm(c, p)
    a.foreign(("DELETE FROM memberships WHERE user_id=? AND room_id=?", (KEVIN, DESIGNERS)))
    return [("messages page", p, lambda r: r.status != 200)]

@case
def user_deactivated(a, c):
    # Rails deactivation deletes the user's sessions too; this edits status alone, as a foreign admin tool might.
    p = f"/rooms/{DESIGNERS}"; warm(c, p)
    a.foreign(("UPDATE users SET status=1 WHERE id=?", (KEVIN,)))
    return [("room page (status=1 only)", p, lambda r: r.status != 200)]

@case
def stale_conditional(a, c):
    p = f"/rooms/{DESIGNERS}/messages"; r0 = warm(c, p); etag = r0.h("etag"); lm = r0.h("last-modified")
    m, _ = latest_message(a, DESIGNERS)
    a.foreign(("UPDATE action_text_rich_texts SET body='<p>FCondZ7</p>' WHERE record_type='Message' AND record_id=?", (m,)))
    def check(r): return r.status == 200 and "FCondZ7" in r.text
    return [(f"If-None-Match {etag}", (p, {"If-None-Match": etag}), check)]

@case
def search_body_edit(a, c):
    p = "/searches?q=Pizza"; r = warm(c, p)
    a.foreign("UPDATE action_text_rich_texts SET body='<p>Pizza FSearchZ8</p>' WHERE record_type='Message' AND record_id IN (SELECT rowid FROM message_search_index WHERE message_search_index MATCH 'Pizza' LIMIT 1)")
    return [("search page", p, lambda r: "FSearchZ8" in r.text)]


@case
def search_body_edit_visible(a, c):
    m, _ = latest_message(a, DESIGNERS)
    db = a.db(); text = db.execute('SELECT body FROM message_search_index WHERE rowid=?', (m,)).fetchone()[0]; db.close()
    import re
    word = [w for w in re.findall(r'[A-Za-z]{4,}', text)][0]
    p = '/searches?q=' + word; warm(c, p)
    a.foreign(('UPDATE action_text_rich_texts SET body=? WHERE record_type="Message" AND record_id=?', ('<div>' + word + ' FSearchZ9</div>', m)))
    return [('search page (' + word + ')', p, lambda r: 'FSearchZ9' in r.text)]

def run(app, port, env, names, user=KEVIN):
    results = []
    for name in names:
        with App(f"f{port}", app, port, env=env) as a:
            c = Client(port); c.sign_in(EMAILS[user])
            checks = CASES[name](a, c)
            for label, target, ok in checks:
                path, hdrs = (target if isinstance(target, tuple) else (target, None))
                r1 = c.get(path, headers=hdrs); time.sleep(1.5); r2 = c.get(path, headers=hdrs)
                res = {"case": name, "check": label, "app": app, "env": env, "now": ok(r1), "after_1.5s": ok(r2), "status": [r1.status, r2.status]}
                if not res["now"]: res["evidence"] = (r1.h("location") or "") + " etag=" + str(r1.h("etag")) + " xrt=" + str(r1.h("x-runtime"))
                results.append(res); print(json.dumps(res), flush=True)
    return results

if __name__ == "__main__":
    app, port = sys.argv[1], int(sys.argv[2]); env = [e for e in sys.argv[3].split(",") if e] if len(sys.argv) > 3 else []
    names = sys.argv[4].split(",") if len(sys.argv) > 4 and sys.argv[4] else list(CASES)
    run(app, port, env, names)
