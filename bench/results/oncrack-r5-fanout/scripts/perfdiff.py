#!/usr/bin/env python3
"""R5.3: python3 perfdiff.py A.perf.script.gz A_MSGS B.perf.script.gz B_MSGS CLIENTS [TOP]
Self and inclusive samples per delivery (a sample is 1/999 s of one core; per delivery = samples / (msgs/s x clients x 8 s)), A against B, largest differences first."""
import collections, gzip, re, sys
def load(path, msgs, clients):
    self_t, incl = collections.Counter(), collections.Counter()
    n = 0; stack = []
    def flush():
        nonlocal n
        if not stack: return
        n += 1; self_t[stack[0]] += 1
        for s in set(stack): incl[s] += 1
    for line in gzip.open(path, 'rt', errors='replace'):
        line = line.rstrip('\n')
        if not line.strip(): flush(); stack = []; continue
        if not line.startswith((' ', '\t')): flush(); stack = []; continue
        parts = line.strip().split(None, 1)
        sym = parts[1] if len(parts) > 1 else parts[0]
        sym = re.sub(r'\s*\(.*\)$', '', sym)
        sym = re.sub(r'\[Optimized\]|\[OptimizedTier1\]|\[Tier1\]|\[Tier0\]|\[PreJIT\]|\[QuickJitted\]|\+0x[0-9a-f]+', '', sym).strip()
        stack.append(sym[:110])
    flush()
    deliveries = float(msgs) * clients * 8
    us = 1e6 / 999.0 / deliveries   # microseconds of CPU per sample per delivery
    return ({k: v * us for k, v in self_t.items()}, {k: v * us for k, v in incl.items()}, n * us)
pa, ma, pb, mb, clients = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
top = int(sys.argv[6]) if len(sys.argv) > 6 else 25
sa, ia, ta = load(pa, ma, clients); sb, ib, tb = load(pb, mb, clients)
print(f"total CPU per delivery (us): A {ta:.2f}  B {tb:.2f}")
for title, a, b in (('SELF', sa, sb), ('INCLUSIVE', ia, ib)):
    print(f"\n{title}: us per delivery, A  B  A-B")
    keys = set(a) | set(b)
    for k in sorted(keys, key=lambda k: -abs(a.get(k, 0) - b.get(k, 0)))[:top]:
        print(f"  {a.get(k,0):6.3f} {b.get(k,0):6.3f} {a.get(k,0)-b.get(k,0):+7.3f}  {k}")
