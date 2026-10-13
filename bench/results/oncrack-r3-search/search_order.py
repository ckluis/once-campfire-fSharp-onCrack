#!/usr/bin/env python3
"""R3.3: does each app list a search's messages in the order the database says upstream does, for several users and queries?

Run inside the colima VM, with the verification harness at $VFY (default /mnt/cfv/once-campfire-verification):

    python3 search_order.py APP IMAGE OUT.json [--env JSON]

One container per app on a copy of the harness seed (host network, server CPUs 0-3, the harness's environment). For each (user, query)
it signs in, fetches /searches?q=QUERY and reads the message ids in page order, and compares them with the database's own answer,
the newest 100 matches the user can reach by message id (oldest first), which is what Rails dbc7620's Message.search_reachable returns.
Writes {query, user, ids, expected, equal} rows, and exits 1 if any differ.
"""
import argparse, json, os, re, shutil, subprocess, sys, time, urllib.parse

VFY = os.environ.get('VFY', '/mnt/cfv/once-campfire-verification')
LG = os.path.join(VFY, 'loadgen/target/release/loadgen')
SEED = os.path.join(VFY, 'fixtures/default')
PORT = 25160
BASE = 'http://127.0.0.1:%d' % PORT
USERS = ['david', 'jason', 'jz', 'kevin']
QUERIES = ['coffee', 'launch', 'wifi', 'the', 'a', 'is', 'post', 'lunch', 'meeting', 'hello', 'thanks', 'zebra']


def sh(*cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout


def sql(db, q):
    out = sh('sqlite3', '-cmd', '.timeout 10000', '-readonly', '-json', db, q)
    return json.loads(out) if out.strip() else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('app'); ap.add_argument('image'); ap.add_argument('out'); ap.add_argument('--env', default='{}')
    a = ap.parse_args()
    labels = json.load(open(os.path.join(SEED, 'labels.json')))
    data = '/mnt/cfv/searchorder-%s' % a.app
    shutil.rmtree(data, ignore_errors=True)
    os.makedirs(data + '/logs')
    shutil.copytree(SEED + '/db', data + '/db'); shutil.copytree(SEED + '/storage', data + '/files')
    db = data + '/db/production.sqlite3'
    if a.app == 'c':
        subprocess.run(['sqlite3', db, 'PRAGMA user_version=1;'], check=True)
    env = dict(l.split('=', 1) for l in open(SEED + '/reference.env').read().splitlines() if l and not l.startswith('#'))
    env.update({'WEB_CONCURRENCY': '3', 'JOB_CONCURRENCY': '3', 'RAILS_MAX_THREADS': '5', 'RAILS_LOG_LEVEL': 'warn', 'HTTP_PORT': str(PORT), 'TARGET_PORT': str(PORT + 1)})
    env.update(json.loads(a.env))
    name = 'cf-searchorder-' + a.app
    subprocess.run(['docker', 'rm', '-f', name], capture_output=True)
    cmd = ['docker', 'run', '-d', '--name', name, '--network', 'host', '--cpuset-cpus', '0-3']
    for k, v in env.items():
        cmd += ['-e', '%s=%s' % (k, v)]
    for h, t in ((data + '/db', '/rails/storage/db'), (data + '/files', '/rails/storage/files'), (data + '/logs', '/rails/storage/logs')):
        cmd += ['-v', '%s:%s' % (h, t)]
    sh(*cmd, a.image)
    rows, bad = [], 0
    try:
        for _ in range(900):
            if subprocess.run(['curl', '-sf', '-o', '/dev/null', BASE + '/up']).returncode == 0:
                break
            time.sleep(0.1)
        sh('docker', 'exec', '--user', 'root', name, 'chmod', '-R', 'a+rwX', '/rails/storage/db')
        time.sleep(2)
        for user in USERS:
            email = labels['emails.' + user]
            cookie = json.loads(sh('taskset', '-c', '4-7', LG, 'login', '--base', BASE, '--email', email, '--password', labels['passwords.all']))['cookie']
            for q in QUERIES:
                html = sh('curl', '-s', '--compressed', '-H', 'Cookie: ' + cookie, BASE + '/searches?q=' + urllib.parse.quote(q))
                ids = [int(i) for i in re.findall(r'data-message-id="(\d+)"', html)]
                esc = email.replace("'", "''")
                exp = [r['id'] for r in sql(db, "SELECT m.id FROM messages m JOIN message_search_index idx ON idx.rowid=m.id JOIN memberships mm ON mm.room_id=m.room_id JOIN users u ON u.id=mm.user_id "
                                                "WHERE u.email_address='%s' AND idx.body MATCH '\"%s\"' ORDER BY m.id DESC LIMIT 100" % (esc, q))][::-1]
                eq = ids == exp
                bad += not eq
                rows.append({'user': user, 'query': q, 'ids': ids, 'expected': exp, 'equal': eq})
    finally:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True)
    json.dump({'app': a.app, 'image': a.image, 'rows': rows, 'different': bad, 'with_results': sum(1 for r in rows if r['expected']),
               'disagree_by_time': None}, open(a.out, 'w'))
    print('%s: %d of %d (user, query) pages equal the id order; %d have results; %d differ' % (a.app, len(rows) - bad, len(rows), sum(1 for r in rows if r['expected']), bad))
    sys.exit(1 if bad else 0)


main()
