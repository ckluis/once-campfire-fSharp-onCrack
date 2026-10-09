#!/usr/bin/env python3
"""The hand re-run of the review (oncrack-r2-final.md): room page, mixed and post, outside bin/benchmark, with the server's CPU.

Run inside the colima VM, with the verification harness at $VFY (default /mnt/cfv/once-campfire-verification):

    python3 review.py APP IMAGE OUT.jsonl [--env JSON] [--secs 15] [--warmup 20]

APP names the run (oncrack, rust, c). Same seed copy, CPUs (server 0-3, load generator 4-7), host network, environment and
validation contracts as bin/benchmark (its bench/contracts.rb writes them; every response is validated). Differences, on
purpose: one container per app for all three phases, a 20 s warm-up at 16 clients before each 15 s window, and the
container's CPU read from its cgroup (cpu.stat usage_usec) around each window, so each line has server CPU us per request.
Phases: room_show c=16, mixed (room_show c=16 plus one writer at 10 posts/s into HQ, as --mixed-write-rate 10), post_message c=16.
After the run, every acknowledged post is checked against the database (messages, rich text and FTS rows, as the harness's audit).
"""
import argparse
import json
import os
import shutil
import subprocess
import time

VFY = os.environ.get('VFY', '/mnt/cfv/once-campfire-verification')
LG = os.path.join(VFY, 'loadgen/target/release/loadgen')
SEED = os.path.join(VFY, 'fixtures/default')
PORT = 25150
BASE = 'http://127.0.0.1:%d' % PORT


def sh(*cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout


def sql(db, q):
    out = sh('sqlite3', '-cmd', '.timeout 10000', '-readonly', '-json', db, q)
    return json.loads(out) if out.strip() else []


def cpu_usec(cid):
    for p in ('/sys/fs/cgroup/system.slice/docker-%s.scope/cpu.stat' % cid, '/sys/fs/cgroup/docker/%s/cpu.stat' % cid):
        if os.path.exists(p):
            return int(next(l for l in open(p) if l.startswith('usage_usec')).split()[1])
    raise SystemExit('no cgroup cpu.stat for ' + cid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('app'); ap.add_argument('image'); ap.add_argument('out')
    ap.add_argument('--env', default='{}'); ap.add_argument('--phases', default='room_show,mixed,post_message'); ap.add_argument('--tag', default=''); ap.add_argument('--secs', type=int, default=15); ap.add_argument('--warmup', type=int, default=20)
    a = ap.parse_args()
    a.name = a.app + (('-' + a.tag) if a.tag else '')
    labels = json.load(open(os.path.join(SEED, 'labels.json')))
    room, write_room = int(labels['rooms.watercooler']), int(labels['rooms.hq'])
    data = '/mnt/cfv/review-%s' % a.name
    shutil.rmtree(data, ignore_errors=True)
    os.makedirs(data + '/logs')
    shutil.copytree(SEED + '/db', data + '/db'); shutil.copytree(SEED + '/storage', data + '/files')
    db = data + '/db/production.sqlite3'
    if a.app == 'c':
        subprocess.run(['sqlite3', db, 'PRAGMA user_version=1;'], check=True)
    subprocess.run(['sqlite3', db, "UPDATE push_subscriptions SET endpoint = 'https://127.0.0.1:9/push/' || id; UPDATE webhooks SET url = 'http://127.0.0.1:9/hook/' || id;"], check=True)
    env = dict(l.split('=', 1) for l in open(SEED + '/reference.env').read().splitlines() if l and not l.startswith('#'))
    env.update({'WEB_CONCURRENCY': '3', 'JOB_CONCURRENCY': '3', 'RAILS_MAX_THREADS': '5', 'RAILS_LOG_LEVEL': 'warn', 'HTTP_PORT': str(PORT), 'TARGET_PORT': str(PORT + 1)})
    env.update(json.loads(a.env))
    name = 'cf-review-' + a.name
    subprocess.run(['docker', 'rm', '-f', name], capture_output=True)
    cmd = ['docker', 'run', '-d', '--name', name, '--network', 'host', '--cpuset-cpus', '0-3']
    for k, v in env.items():
        cmd += ['-e', '%s=%s' % (k, v)]
    for h, t in ((data + '/db', '/rails/storage/db'), (data + '/files', '/rails/storage/files'), (data + '/logs', '/rails/storage/logs')):
        cmd += ['-v', '%s:%s' % (h, t)]
    cid = sh(*cmd, a.image).strip()
    image_id = sh('docker', 'image', 'inspect', '-f', '{{.Id}}', a.image).strip()
    try:
        for _ in range(900):
            if subprocess.run(['curl', '-sf', '-o', '/dev/null', BASE + '/up']).returncode == 0:
                break
            time.sleep(0.1)
        sh('docker', 'exec', '--user', 'root', name, 'chmod', '-R', 'a+rwX', '/rails/storage/db')
        time.sleep(3)
        lg = lambda *args: json.loads(sh('taskset', '-c', '4-7', LG, *args))
        cookie = lg('login', '--base', BASE, '--email', labels['emails.david'], '--password', labels['passwords.all'])['cookie']
        scrape = lg('scrape', '--base', BASE, '--cookie', cookie, '--room', str(room))
        csrf = str(scrape.get('csrf') or '')
        so = 'created_at' if a.app in ('oncrack', 'fsharp') else 'id'
        prep = json.loads(sh('ruby', '-e', 'require "%s/bench/contracts"; base, cookie, db, labels, css, dest, so = ARGV; '
                                        'puts JSON.generate(BenchmarkContracts.prepare(base, cookie, db, JSON.parse(File.read(labels)), css, dest, search_order: so))' % VFY,
                             BASE, cookie, db, SEED + '/labels.json', scrape['css'], data + '/contracts', so))
        contracts = prep['contracts']
        initial_max = sql(db, 'SELECT MAX(id) AS id FROM messages')[0]['id']
        initial_hq = sql(db, 'SELECT COUNT(*) AS n FROM messages WHERE room_id=%d' % write_room)[0]['n']
        acked = 0
        audits = []
        phases = [('room_show', ['--path', '/rooms/%d' % room, '--validate', contracts['room_show']], False),
                  ('mixed', ['--path', '/rooms/%d' % room, '--validate', contracts['room_show']], True),
                  ('post_message', ['--post-room', str(write_room), '--csrf', csrf, '--validate', contracts['post_message']], False)]
        phases = [p for p in phases if p[0] in a.phases.split(',')]
        with open(a.out, 'a') as out:
            for phase, args, mixed in phases:
                for kind, secs in (('warmup', a.warmup), ('window', a.secs)):
                    extra = []
                    if phase == 'post_message':
                        audits.append('%s/audit-%s-%s.jsonl' % (data, phase, kind)); extra = ['--audit-writes', audits[-1]]
                    if mixed:
                        audits.append('%s/audit-%s-%s.jsonl' % (data, phase, kind))
                        extra = ['--mixed-write-rate', '10', '--mixed-write-room', str(write_room), '--mixed-write-validate', contracts['post_message'],
                                 '--mixed-write-audit', audits[-1], '--csrf', csrf]
                    c0, t0 = cpu_usec(cid), time.monotonic()
                    v = lg('http', '--base', BASE, '--cookie', cookie, *args, *extra, '--conc', '16', '--duration', str(secs))
                    c1, t1 = cpu_usec(cid), time.monotonic()
                    ok_all = v['errors'] == 0 and v['invalid_responses'] == 0 and v['statuses'] == {'200': v['ok']}
                    if phase == 'post_message':
                        acked += v['ok']
                    if mixed:
                        w = v['writer']; acked += w['ok']
                        ok_all = ok_all and w['errors'] == 0 and w['invalid_responses'] == 0
                    reqs = v['ok'] + (v['writer']['ok'] if mixed else 0)
                    row = {'app': a.app, 'tag': a.tag, 'env': json.loads(a.env), 'image': image_id, 'phase': phase, 'kind': kind, 'rps': v['rps'], 'ok': v['ok'], 'valid': ok_all,
                           'writer_ok': v['writer']['ok'] if mixed else None, 'p50_ms': v['latency']['p50_ms'], 'p99_ms': v['latency']['p99_ms'],
                           'server_cpu_us_per_req': (c1 - c0) / reqs if reqs else None, 'server_cores_busy': (c1 - c0) / 1e6 / (t1 - t0)}
                    out.write(json.dumps(row) + '\n'); out.flush()
                    if kind == 'window':
                        print(json.dumps(row))
                    if not ok_all:
                        raise SystemExit('invalid responses: ' + json.dumps(v)[:2000])
        hq = sql(db, 'SELECT COUNT(*) AS n FROM messages WHERE room_id=%d' % write_room)[0]['n'] - initial_hq
        fts_missing = sql(db, 'SELECT COUNT(*) AS n FROM messages WHERE id NOT IN (SELECT rowid FROM message_search_index)')[0]['n']
        rt = sql(db, "SELECT COUNT(*) AS n FROM messages m JOIN action_text_rich_texts rt ON rt.record_type='Message' AND rt.record_id=m.id AND rt.name='body' "
                     "WHERE m.room_id=%d AND m.id>%d AND rt.body LIKE '%%bench write %%'" % (write_room, initial_max))[0]['n']
        audit = json.loads(sh('ruby', '-e', 'require "%s/bench/validate_acks"; db, room, n, *files = ARGV; puts JSON.generate(AcknowledgedWrites.verify(db, Integer(room), files, Integer(n)))' % VFY,
                              db, str(write_room), str(acked), *audits))
        summary = {'app': a.app, 'tag': a.tag, 'image': image_id, 'phase': 'audit', 'acknowledged': acked, 'hq_new_rows': hq, 'richtext_rows': rt, 'fts_missing': fts_missing, 'audit': audit,
                   'ok': hq == acked == rt and fts_missing == 0 and audit.get('verified') is True}
        with open(a.out, 'a') as out:
            out.write(json.dumps(summary) + '\n')
        print(json.dumps(summary))
    finally:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True)
        shutil.rmtree(data, ignore_errors=True)


if __name__ == '__main__':
    main()
