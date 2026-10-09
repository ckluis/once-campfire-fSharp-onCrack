#!/usr/bin/env python3
"""R2.5's tables, printed from the raw runs.  python3 bench/results/oncrack-r2-mem/review/table.py

  1. the realistic workloads at c=16, the image before (campfire-oncrack:r24, R2.4's, 4e12ec8) and after (campfire-oncrack:app, 64a714d),
     median of the reps [min-max], against the Rust and F# port medians of bench/results/oncrack-r2-bench/ (R2.0's session);
     series B is the reported one (images alternating), series A the first run (see the write-up), `new` rep 3 of B is the recheck run
  2. the memory suites (mem-t3.jsonl): per phase peak anon and Pss, the whole run, Rust, the F# port, onCrack before, after, AOT
"""
import glob, json, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)
BASE = os.path.join(os.path.dirname(RES), "oncrack-r2-bench")


def load(d, app="oncrack"):
    return [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, f"{app}-[0-9].json")))]


def cell(runs, route):
    reads, posts, cpu = [], [], []
    for r in runs:
        for h in r["http"]:
            if h["route"] == route and h["conc"] == 16:
                lanes = h.get("lanes") or {}
                reads.append(lanes.get("reads", {}).get("rps", h["rps"]))
                if "posts" in lanes:
                    posts.append(lanes["posts"]["rps"])
                cpu.append(h["cost"]["server_cpu_us_per_req"])
    med = lambda xs: statistics.median(xs) if xs else None
    return med(reads), med(posts), med(cpu), (min(reads), max(reads)) if reads else None, len(reads)


def fmt(x, nd=0):
    return "-" if x is None else f"{x:,.{nd}f}"


def ratio(a, b):
    return "-" if not a or not b else f"{a / b:.2f}x"


def realistic(title, old, new):
    rust, port = load(BASE, "rust"), load(BASE, "fsharp")
    print(title)
    print(f"{'workload':<14}{'before':>30}{'after':>30}{'after/before':>13}{'Rust':>9}{'port':>9}{'after/Rust':>11}{'after/port':>11}")
    for route in ("mixed", "spread", "spread_mixed", "search_spread"):
        o, n, ru, po = cell(old, route), cell(new, route), cell(rust, route), cell(port, route)
        rng = lambda c: f"{fmt(c[0])} [{fmt(c[3][0])}-{fmt(c[3][1])}] x{c[4]}" if c[0] else "-"
        print(f"{route:<14}{rng(o):>30}{rng(n):>30}{ratio(n[0], o[0]):>13}{fmt(ru[0]):>9}{fmt(po[0]):>9}{ratio(n[0], ru[0]):>11}{ratio(n[0], po[0]):>11}")
        if n[1] or o[1]:
            print(f"{'  posts/s':<14}{fmt(o[1]):>30}{fmt(n[1]):>30}{ratio(n[1], o[1]):>13}{fmt(ru[1]):>9}{fmt(po[1]):>9}{ratio(n[1], ru[1]):>11}{ratio(n[1], po[1]):>11}")
        print(f"{'  cpu us/req':<14}{fmt(o[2], 1):>30}{fmt(n[2], 1):>30}{'':>13}{fmt(ru[2], 1):>9}{fmt(po[2], 1):>9}")
    print("  memory over the four workloads, peak anon / peak current MB (container):")
    for name, runs in (("before", old), ("after", new), ("Rust", rust), ("F# port", port)):
        a = [r["memory"]["peak_anon_mb"] for r in runs]
        c = [r["memory"]["peak_current_mb"] for r in runs]
        print(f"    {name:<8} anon {fmt(statistics.median(a))} [{min(a)}-{max(a)}]  current {fmt(statistics.median(c))}")
    print()


def memory():
    rows = [json.loads(l) for l in open(os.path.join(RES, "mem-t3.jsonl")) if l.strip()]
    by = {}
    for r in rows:
        by[r["label"]] = r
    names = [("Rust", "t3-classic-rust"), ("F# port", "t3-classic-fsharp"), ("onCrack before", "t3-classic-old"), ("onCrack after", "t3-classic-new"), ("after, AOT", "t3-classic-aot")]
    print("Classic memory suite, one container, phases in order: peak anon MB per phase (Pss peak in brackets where it matters)")
    phases = [p["phase"] for p in by["t3-classic-new"]["phases"]]
    print(f"{'phase':<22}" + "".join(f"{n:>16}" for n, _ in names))
    for i, ph in enumerate(phases):
        cells = []
        for _, label in names:
            ps = by.get(label, {"phases": []})["phases"]
            cells.append(f"{ps[i]['anon_peak_mb']} ({ps[i]['pss_peak_mb']})" if i < len(ps) and ps[i]["phase"] == ph else "-")
        print(f"{ph:<22}" + "".join(f"{c:>16}" for c in cells))
    print(f"{'whole run':<22}" + "".join(f"{by[l]['whole']['anon_peak_mb']} ({by[l]['whole']['pss_peak_mb']}){'':>0}".rjust(16) if l in by else "-".rjust(16) for _, l in names))
    print(f"{'peak current':<22}" + "".join(f"{by[l]['whole']['cur_peak_mb']}".rjust(16) if l in by else "-".rjust(16) for _, l in names))
    print()
    names = [("onCrack before", "t3-real-old"), ("onCrack after", "t3-real-new")]
    print("Realistic memory suite (crowd seed, each workload from the one before): peak anon MB (Pss) per phase")
    phases = [p["phase"] for p in by["t3-real-new"]["phases"]]
    print(f"{'phase':<22}" + "".join(f"{n:>16}" for n, _ in names))
    for i, ph in enumerate(phases):
        cells = []
        for _, label in names:
            ps = by[label]["phases"]
            cells.append(f"{ps[i]['anon_peak_mb']} ({ps[i]['pss_peak_mb']})" if i < len(ps) and ps[i]["phase"] == ph else "-")
        print(f"{ph:<22}" + "".join(f"{c:>16}" for c in cells))
    print(f"{'whole run':<22}" + "".join(f"{by[l]['whole']['anon_peak_mb']} ({by[l]['whole']['pss_peak_mb']})".rjust(16) for _, l in names))
    print()
    print("Cold start (bench/boot, docker run to the first /up, median of 7 [min-max]) and idle:")
    for r in (json.loads(l) for l in open(os.path.join(RES, "boot.jsonl")) if l.strip()):
        if r["label"].startswith("t3-boot"):
            print(f"  {r['label']:<18} up {r['median']['up_ms']:g} [{r['range']['up_ms'][0]}-{r['range']['up_ms'][1]}] ms   idle current {r['median']['idle_mb']:g} MB, anon {r['median']['idle_anon_mb']:g}, rss {r['median']['rss_mb']:g}")


if __name__ == "__main__":
    realistic("Series B (reported): the two images alternating, 22:36-22:55 (new rep 3 is the recheck run of 22:33)", load(os.path.join(RES, "t3b-real-old")), load(os.path.join(RES, "t3b-real-new")))
    realistic("Series A (the first run, 21:53-22:14; kept for the record, see the write-up)", load(os.path.join(RES, "t3-real-old")), load(os.path.join(RES, "t3-real-new")))
    memory()
