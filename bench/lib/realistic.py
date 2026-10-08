#!/usr/bin/env python3
"""The realistic workloads of bench/run and bench/quick (unit R2.0): reads while writing, many rooms and users, and search over many
queries. The five classic workloads repeat one URL as one user and never write while they read, so onCrack's read cache answers
every one of them from a stored page; these are the other ends.

  realistic.py prepare --base URL --seed-dir DIR --loadgen PATH --out DIR [--users N] [--workers 8] [--loadgen-cpus 4-7]
      signs the seed's people in (every active, non-bot user with an email address, by id; --users caps it) and writes DIR/users.json
      (cookie, CSRF token for the users who post, the rooms each is a member of). Each sign-in comes from its own X-Forwarded-For
      address (10.77.x.y), so 500 sign-ins from loopback are not one client to the apps' sign-in rate limit (Rails: 10 in 3 minutes).
  realistic.py spec WORKLOAD --prepared DIR --out FILE      the load generator's spec (loadgen http --mix-spec FILE)
  realistic.py describe --prepared DIR                      the size of every workload, as JSON (what a run's env.txt records)

The workloads (`scale` lanes take the measured concurrency c; the others keep theirs):

  mixed          c connections read the busy room's page (/rooms/<watercooler>) as david while MIX_POSTERS connections (default 1) post
                 into that same room as david, as fast as the app answers: round 1's review/mixed.sh as a workload. Every post moves the
                 room's version, so onCrack serves a mix of stored pages and renders.
  spread         c connections, each request a (user, page) drawn uniformly from every signed-in user's room pages (each room they are
                 a member of) and their sidebar, each with its own cookie. Read-only: after the warm-up a cache holds whatever fits.
  spread_mixed   spread, plus SPREAD_POSTERS connections (default 1) posting, each post by one of the first POSTING_USERS users (default
                 32) into one of their rooms, drawn uniformly. A post into an open room moves the version of a room 500+ people read,
                 and the sidebar of every one of them.
  search_spread  c connections, each request a search (/searches?q=...) by a user and a query drawn independently and uniformly from
                 every signed-in user who is a member of a room (524: Rails' search page raises for a user with none, Lonely Lou,
                 at searches/index.html.erb:63, room_path(nil)) and SEARCH_QUERIES (default 200) words of the seed's messages.
                 Read-only, but users x queries is far more pages than a 64 MB cache holds.

The seed is the crowd seed (parity/.seed/crowd: the default seed plus 520 members of the three open rooms), so there are 525 people to
sign in; bench/run starts the realistic workloads' container on it. The Broken room (its message's author is missing) is left out of the
targets: it is a parity case, not a page people read.
"""
import argparse
import concurrent.futures
import html
import json
import os
import random
import re
import sqlite3
import subprocess
import sys

WORKLOADS = ("mixed", "spread", "spread_mixed", "search_spread")


def labels(seed_dir):
    with open(os.path.join(seed_dir, "labels.json")) as f:
        return json.load(f)


def people(seed_dir):
    db = sqlite3.connect(os.path.join(seed_dir, "db", "production.sqlite3"))
    rows = db.execute("SELECT id, email_address FROM users WHERE status = 0 AND role != 2 AND email_address IS NOT NULL ORDER BY id").fetchall()
    broken = labels(seed_dir).get("rooms.broken")
    rooms = {}
    for user_id, room_id in db.execute("SELECT user_id, room_id FROM memberships ORDER BY room_id"):
        if room_id != broken:
            rooms.setdefault(user_id, []).append(room_id)
    return [{"id": uid, "email": email, "rooms": rooms.get(uid, [])} for uid, email in rows]


def queries(seed_dir, n):
    """n distinct words (3+ letters) of the seed's message bodies, in a fixed shuffled order."""
    db = sqlite3.connect(os.path.join(seed_dir, "db", "production.sqlite3"))
    words = set()
    for (body,) in db.execute("SELECT body FROM action_text_rich_texts WHERE record_type = 'Message'"):
        text = html.unescape(re.sub(r"<[^>]+>", " ", body or ""))
        words.update(w.lower() for w in re.findall(r"[A-Za-z]{3,}", text))
    words = sorted(words)
    random.Random(7).shuffle(words)
    return words[:n]


def lg(loadgen, cpus, *args):
    cmd = (["taskset", "-c", cpus] if cpus else []) + [loadgen, *args]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if out.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:1])}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def prepare(a):
    lab = labels(a.seed_dir)
    who = people(a.seed_dir)
    if a.users:
        who = who[: a.users]
    password = lab["passwords.all"]
    posting = int(os.environ.get("POSTING_USERS", "32"))

    def sign_in(i):
        p = who[i]
        r = lg(a.loadgen, a.loadgen_cpus, "login", "--base", a.base, "--email", p["email"], "--password", password,
               "--forwarded-for", f"10.77.{i // 250}.{i % 250 + 1}")
        p["cookie"] = r["cookie"]
        p["csrf"] = ""
        if (i < posting or p["email"] == lab["emails.david"]) and p["rooms"]:
            s = lg(a.loadgen, a.loadgen_cpus, "scrape", "--base", a.base, "--cookie", p["cookie"], "--room", str(p["rooms"][0]))
            p["csrf"] = s["csrf"] or ""
        return i

    with concurrent.futures.ThreadPoolExecutor(a.workers) as pool:
        list(pool.map(sign_in, range(len(who))))
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "users.json"), "w") as f:
        json.dump({"seed": os.path.basename(os.path.normpath(a.seed_dir)), "users": who, "seed_dir": os.path.abspath(a.seed_dir)}, f)
    print(json.dumps({"signed_in": len(who), "posting": min(posting, len(who))}))


def spec(workload, prepared):
    with open(os.path.join(prepared, "users.json")) as f:
        p = json.load(f)
    who, seed_dir = p["users"], p["seed_dir"]
    lab = labels(seed_dir)
    users = [{"cookie": u["cookie"], "csrf": u.get("csrf", "")} for u in who]
    david = next(i for i, u in enumerate(who) if u["email"] == lab["emails.david"])
    room = lab["rooms.watercooler"]
    reads = [{"u": i, "path": f"/rooms/{r}"} for i, u in enumerate(who) for r in u["rooms"]] + \
            [{"u": i, "path": "/users/me/sidebar"} for i in range(len(who))]
    posting = int(os.environ.get("POSTING_USERS", "32"))
    posts = [{"u": i, "room": r} for i, u in enumerate(who[:posting]) for r in u["rooms"]]
    if workload == "mixed":
        lanes = [{"name": "reads", "conc": 16, "scale": True, "pick": "cycle", "targets": [{"u": david, "path": f"/rooms/{room}"}]},
                 {"name": "posts", "conc": int(os.environ.get("MIX_POSTERS", "1")), "pick": "cycle", "targets": [{"u": david, "room": room}]}]
    elif workload == "spread":
        lanes = [{"name": "reads", "conc": 16, "scale": True, "pick": "random", "seed": 11, "targets": reads}]
    elif workload == "spread_mixed":
        lanes = [{"name": "reads", "conc": 16, "scale": True, "pick": "random", "seed": 11, "targets": reads},
                 {"name": "posts", "conc": int(os.environ.get("SPREAD_POSTERS", "1")), "pick": "random", "seed": 13, "targets": posts}]
    elif workload == "search_spread":
        qs = queries(seed_dir, int(os.environ.get("SEARCH_QUERIES", "200")))
        lanes = [{"name": "reads", "conc": 16, "scale": True, "pick": "random", "seed": 17,
                  "cross": {"users": [i for i, u in enumerate(who) if u["rooms"]], "paths": [f"/searches?q={q}" for q in qs]}}]
    else:
        raise SystemExit(f"unknown workload {workload}; one of {', '.join(WORKLOADS)}")
    return {"name": workload, "seed": p["seed"], "users": users, "lanes": lanes}


def describe(prepared):
    out = {}
    for w in WORKLOADS:
        s = spec(w, prepared)
        out[w] = {l["name"]: {"conc": "c" if l.get("scale") else l["conc"], "pick": l["pick"],
                              "targets": len(l["cross"]["users"]) * len(l["cross"]["paths"]) if "cross" in l else len(l["targets"]),
                              "users": len({t["u"] for t in l["targets"]}) if "targets" in l else len(l["cross"]["users"])}
                  for l in s["lanes"]}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--base", required=True); p.add_argument("--seed-dir", required=True); p.add_argument("--loadgen", required=True)
    p.add_argument("--out", required=True); p.add_argument("--users", type=int, default=0); p.add_argument("--workers", type=int, default=8)
    p.add_argument("--loadgen-cpus", default="")
    s = sub.add_parser("spec"); s.add_argument("workload"); s.add_argument("--prepared", required=True); s.add_argument("--out", required=True)
    d = sub.add_parser("describe"); d.add_argument("--prepared", required=True)
    a = ap.parse_args()
    if a.cmd == "prepare":
        prepare(a)
    elif a.cmd == "spec":
        with open(a.out, "w") as f:
            json.dump(spec(a.workload, a.prepared), f)
    else:
        print(json.dumps(describe(a.prepared)))
