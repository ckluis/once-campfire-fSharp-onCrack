#!/usr/bin/env python3
"""Host noise per cable part: for each "== APP rep N HH:MM:SS" marker of a session log, the host samples (host-load file, every 10 s, non-VM CPU sum)
between that marker and the next: samples, share with sum >= 150% (the plan's NOISY mark), median and max sum, max load average (1 min).
  python3 cable/noise.py SESSION_LOG HOST_LOAD_FILE [...]"""
import re, statistics as st, sys

def secs(t): h, m, s = map(int, t.split(":")); return h * 3600 + m * 60 + s

def samples(path):
    out = []
    for ln in open(path):
        m = re.match(r"(\d\d:\d\d:\d\d) load\s+([\d.]+).*?\| sum (\d+)", ln)
        if m: out.append((secs(m.group(1)), float(m.group(2)), int(m.group(3))))
    return out

def main(log, hl, end=None):
    marks = []
    for ln in open(log):
        m = re.match(r"== (\w+) (?:rep (\d)|(sends)) ?\S* ?(\d\d:\d\d:\d\d)?", ln)
        m2 = re.match(r"== (.+?) (\d\d:\d\d:\d\d)", ln)
        if m2: marks.append((m2.group(1), secs(m2.group(2))))
    sm = samples(hl)
    last = max(t for t, _, _ in sm)
    print("| part | samples | share >=150% | median sum | max sum | max load avg |")
    print("|---|---|---|---|---|---|")
    tot = []
    for i, (name, t0) in enumerate(marks):
        t1 = marks[i + 1][1] if i + 1 < len(marks) else last
        w = [s for s in sm if t0 <= s[0] < t1]
        if not w: continue
        tot += w
        n = sum(1 for s in w if s[2] >= 150)
        print(f"| {name} | {len(w)} | {100 * n / len(w):.0f}% | {st.median(s[2] for s in w):.0f} | {max(s[2] for s in w)} | {max(s[1] for s in w):.1f} |")
    n = sum(1 for s in tot if s[2] >= 150)
    print(f"| **whole session** | {len(tot)} | **{100 * n / len(tot):.0f}%** | {st.median(s[2] for s in tot):.0f} | {max(s[2] for s in tot)} | {max(s[1] for s in tot):.1f} |")

main(*sys.argv[1:3])
