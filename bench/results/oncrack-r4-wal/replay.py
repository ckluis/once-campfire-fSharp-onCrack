#!/usr/bin/env python3
"""Offline replay of the post path's SQL against a copy of the crowd seed: GROUPS commits of K posts each, the WAL's frames by b-tree
(dbstat of the final database; pages are only appended while nothing is freed, so run with --automerge 0/16 for a clean attribution).
  replay.py [--k 5] [--groups 400] [--automerge N] [--drop-index NAME] [--fts-after]"""
import argparse, collections, os, shutil, sqlite3, struct, tempfile, uuid, datetime
ap = argparse.ArgumentParser()
ap.add_argument("--k", type=int, default=5); ap.add_argument("--groups", type=int, default=400)
ap.add_argument("--automerge", type=int, default=None); ap.add_argument("--drop-index", default=None)
ap.add_argument("--seed", default=os.path.join(os.path.dirname(__file__), "../../../parity/.seed/crowd/db"))
a = ap.parse_args()
w = tempfile.mkdtemp()
shutil.copy(os.path.join(a.seed, "production.sqlite3"), w)
db = sqlite3.connect(w + "/production.sqlite3", isolation_level=None)
db.execute("pragma journal_mode=wal"); db.execute("pragma synchronous=normal"); db.execute("pragma wal_autocheckpoint=0")
db.execute("CREATE INDEX IF NOT EXISTS index_messages_on_room_id_and_created_at ON messages (room_id, created_at)")
if a.drop_index: db.execute(f"drop index {a.drop_index}")
if a.automerge is not None: db.execute(f"INSERT INTO message_search_index(message_search_index, rank) VALUES('automerge', {a.automerge})")
db.execute("pragma wal_checkpoint(truncate)")
room = db.execute("select room_id from messages group by room_id order by count(*) desc limit 1").fetchone()[0]
user = db.execute("select creator_id from messages where room_id=? limit 1", (room,)).fetchone()[0]
now = lambda: datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
base = os.path.getsize(w + "/production.sqlite3-wal") if os.path.exists(w + "/production.sqlite3-wal") else 0
for g in range(a.groups):
    db.execute("BEGIN IMMEDIATE"); ids = []
    for i in range(a.k):
        db.execute("SAVEPOINT s")
        t = now()
        mid = db.execute('INSERT INTO messages (client_message_id, created_at, creator_id, room_id, updated_at) VALUES (?,?,?,?,?) RETURNING id', (str(uuid.uuid4()), t, user, room, t)).fetchone()[0]
        db.execute('INSERT INTO action_text_rich_texts (body, created_at, name, record_id, record_type, updated_at) VALUES (?,?,?,?,?,?)', ("<div>hello world number %d from the bench %s</div>" % (mid, uuid.uuid4().hex[:8]), t, "body", mid, "Message", t))
        db.execute("UPDATE messages SET updated_at=? WHERE id=?", (t, mid))
        db.execute("UPDATE rooms SET updated_at=? WHERE id=?", (t, room))
        db.execute("RELEASE s"); ids.append(mid)
    for mid in ids:
        db.execute("insert into message_search_index(rowid, body) values (?,?)", (mid, "hello world number %d from the bench" % mid))
    db.execute("COMMIT")
w2 = tempfile.mkdtemp()
for f in ("production.sqlite3", "production.sqlite3-wal"): shutil.copy(os.path.join(w, f), w2)
db.close()
w = w2
wal = open(w + "/production.sqlite3-wal", "rb").read()
ps = struct.unpack(">I", wal[8:12])[0]; salt = wal[16:24]
off, frames, commits = 32, [], 0
while off + 24 + ps <= len(wal):
    pg, dbs = struct.unpack(">II", wal[off:off + 8])
    if wal[off + 8:off + 16] != salt: break
    frames.append(pg); commits += (dbs != 0); off += 24 + ps
d = sqlite3.connect(w + "/production.sqlite3")
owner = {p: n for n, p in d.execute("select name,pageno from dbstat")}
by = collections.Counter(owner.get(p, "(new)") for p in frames)
n = a.groups * a.k
print(f"k={a.k} groups={a.groups} automerge={a.automerge} drop={a.drop_index}: {len(frames)} frames, {len(frames)/commits:.1f}/commit, {len(frames)/n:.3f}/post")
for name, c in by.most_common(14): print(f"   {name:48} {c/commits:6.2f}/commit  {c/n:6.3f}/post")
shutil.rmtree(w)
