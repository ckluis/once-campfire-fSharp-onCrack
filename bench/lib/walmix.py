#!/usr/bin/env python3
"""What a WAL holds, by table and index: reads the frames of the WAL's current generation (the salts of its header) and
names each frame's page by the b-tree that owns it (dbstat over the database with that WAL), for frames per commit and which
b-trees take them.

  bench/lib/walmix.py DIR [--posts N]     # DIR holds production.sqlite3 and its -wal (bench/post-micro's POST_MICRO_KEEP)

Run it on a copy: opening the database may checkpoint the WAL when the last connection closes, so it copies DIR first.
"""
import collections, os, shutil, sqlite3, struct, sys, tempfile

src = sys.argv[1]
posts = int(sys.argv[sys.argv.index("--posts") + 1]) if "--posts" in sys.argv else 0
work = tempfile.mkdtemp()
for f in ("production.sqlite3", "production.sqlite3-wal"):
    shutil.copy(os.path.join(src, f), os.path.join(work, f))
wal = open(os.path.join(work, "production.sqlite3-wal"), "rb").read()
magic, version, page_size, seq, salt1, salt2, c1, c2 = struct.unpack(">IIIIIIII", wal[:32])
frames, commits = [], 0
off = 32
while off + 24 + page_size <= len(wal):
    pgno, dbsize, s1, s2 = struct.unpack(">IIII", wal[off:off + 16])
    if (s1, s2) != (salt1, salt2):
        break
    frames.append(pgno)
    if dbsize:
        commits += 1
    off += 24 + page_size
db = sqlite3.connect(os.path.join(work, "production.sqlite3"))
owner = {}
try:
    for name, pageno in db.execute("SELECT name, pageno FROM dbstat"):
        owner[pageno] = name
except sqlite3.OperationalError as e:
    sys.exit(f"dbstat: {e}")
by = collections.Counter(owner.get(p, "(free or new)") for p in frames)
distinct = collections.Counter(owner.get(p, "(free or new)") for p in set(frames))
print(f"page size {page_size}; {len(frames)} frames in {commits} commits, {len(frames) / max(commits, 1):.1f} frames a commit; "
      f"{len(set(frames))} distinct pages" + (f"; {len(frames) / posts:.2f} frames a post" if posts else ""))
print(f"{'b-tree':48} {'frames':>8} {'share':>6} {'/commit':>8} {'distinct':>8}")
for name, n in by.most_common(25):
    print(f"{name:48} {n:8} {n / len(frames):6.1%} {n / max(commits, 1):8.2f} {distinct[name]:8}")
shutil.rmtree(work)
