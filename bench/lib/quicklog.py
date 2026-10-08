#!/usr/bin/env python3
"""onCrack's results against the stored Rust and F# port medians, and onCrack's progress log.

  quicklog.py compare DIR                 table of the onCrack runs in DIR (oncrack-N.json) against bench/results/phase7-final: the stored Rust
                                          medians and the stored F# port medians (same session, 3 reps each), with the validity checks
  quicklog.py log DIR --unit U --tier N --change "..." --kept true|false [--build mounted|DIGEST] [--commit SHA] [--description TEXT]
                                          append one line to bench/results/oncrack-log.jsonl (raw onCrack numbers per workload), then rebuild
                                          index.html (the climb chart) with bench/progress/build.py

Neither Rust nor the port is measured here: their numbers are the medians of bench/results/phase7-final/{rust,fsharp}-*.json (the same
warm-up and harness). Every ratio this prints is "vs stored Rust baseline" or "vs stored F# port baseline", and never a like-for-like port result
(plans/oncrack.md rule 4). The port-era log, bench/results/phase7-log.jsonl, is history and is not appended to.
"""
import argparse
import glob
import json
import os
import statistics
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STORED = os.path.join(ROOT, "bench/results/phase7-final")   # Rust and the F# port, measured in one session
# The realistic workloads (bench/lib/realistic.py, unit R2.0): Rails, Rust, the F# port and onCrack measured in one session.
STORED_REAL = os.path.join(ROOT, "bench/results/oncrack-r2-bench")
REALISTIC = ["mixed", "spread", "spread_mixed", "search_spread"]
LOG = os.path.join(ROOT, "bench/results/oncrack-log.jsonl")
APP = "oncrack"
WORKLOADS = ["room_show", "messages_page", "sidebar", "search", "post_message"]
LABEL = {"room_show": "room page", "messages_page": "messages page", "sidebar": "sidebar", "search": "search", "post_message": "post a message"}


def load(directory, app):
    runs = []
    for p in sorted(glob.glob(os.path.join(directory, f"{app}-[0-9].json"))):
        with open(p) as f:
            runs.append(json.load(f))
    return runs


def cells(runs):
    """{(route, conc): {"rps": [..], "cpu": [..], "runs": [..]}} over the gzip runs of every rep."""
    out = {}
    for r in runs:
        for h in r["http"]:
            if not h.get("gzip"):
                continue
            c = out.setdefault((h["route"], h["conc"]), {"rps": [], "cpu": [], "runs": [], "lanes": {}})
            c["rps"].append(h["rps"])
            for name, lane in h.get("lanes", {}).items():
                c["lanes"].setdefault(name, []).append(lane["rps"])
            cpu = h.get("cost", {}).get("server_cpu_us_per_req")
            if cpu is not None:
                c["cpu"].append(cpu)
            c["runs"].append(h)
    return out


def med(v):
    return statistics.median(v) if v else None


def spread(v):
    return "" if len(v) < 2 else f" [{min(v):,.0f}-{max(v):,.0f}]"


def fmt(x, d=0):
    return "-" if x is None else f"{x:,.{d}f}"


def compare(directory):
    mine = cells(load(directory, APP))
    if not mine:
        sys.exit(f"no {APP}-N.json in {directory}")
    rust = cells(load(STORED, "rust"))
    port = cells(load(STORED, "fsharp"))
    classic = any(w in WORKLOADS for w, _ in mine)
    if classic:
        print(f"onCrack in {directory} against the stored Rust and F# port medians (bench/results/phase7-final, 3 reps each, one session)\n")
        print("| Workload | c | onCrack req/s | F# port stored | **onCrack / F# port** | Rust stored | **onCrack / Rust (vs stored Rust baseline)** | onCrack CPU us/req | F# port | Rust |")
        print("|---|---|---|---|---|---|---|---|---|---|")
    for w in WORKLOADS:
        for c in (16, 1):
            m = mine.get((w, c))
            if not m:
                continue
            r, s = rust.get((w, c)), port.get((w, c))
            mr, rr, sr = med(m["rps"]), med(r["rps"]) if r else None, med(s["rps"]) if s else None
            print(f"| {LABEL[w]} | {c} | {fmt(mr)}{spread(m['rps'])} | {fmt(sr)} | **{mr / sr:.3f}x** | {fmt(rr)} | **{mr / rr:.3f}x** | "
                  f"{fmt(med(m['cpu']), 1)}{spread(m['cpu']) if len(m['cpu']) > 1 else ''} | {fmt(med(s['cpu']), 1) if s else '-'} | {fmt(med(r['cpu']), 1) if r else '-'} |")
    real_table(mine)
    # validity: statuses, errors, response bytes, rows written, warm-up, host noise
    print("\nChecks:")
    bad = 0
    for (w, c), m in sorted(mine.items()):
        for h in m["runs"]:
            non2xx = {k: v for k, v in h["statuses"].items() if not k.startswith("2")}
            if non2xx or h["errors"]:
                bad += 1
                print(f"  FAIL {w} c={c}: statuses {h['statuses']} errors {h['errors']}")
            if not h.get("warmup", {}).get("settled", True):
                print(f"  note {w} c={c}: warm-up did not settle ({h['warmup'].get('reason')})")
            ratio = h.get("host_probe_after", {}).get("ratio")
            if ratio and ratio > 1.10:
                print(f"  note {w} c={c}: host probe {ratio} after the window (noisy host)")
    print(f"  responses: every one 2xx with 0 connection errors in {sum(len(m['runs']) for m in mine.values())} runs" if not bad else f"  {bad} run(s) with errors")
    rust_probe = {p["route"]: p["gzip"]["decoded_bytes"] for p in (load(STORED, "rust") or [{"probe": []}])[0]["probe"]}
    for r in load(directory, APP):
        for p in r["probe"]:
            want = rust_probe.get(p["route"])
            if want is not None and p["gzip"]["decoded_bytes"] != want:
                print(f"  FAIL decoded bytes {p['route']}: {p['gzip']['decoded_bytes']} vs Rust {want}")
                bad += 1
        for row in r["post_rows"]:
            if row["rows"] != sum(v for k, v in row["statuses"].items() if int(k) < 400):
                print(f"  FAIL post rows {row}")
                bad += 1
    if not bad:
        print("  decoded bytes equal Rust's on every probed route; post rows written equal the 2xx answers in every phase")
    return bad


def real_table(mine):
    """The realistic workloads in a run, against the same-session baseline of STORED_REAL (every app's median there)."""
    if not any(w in REALISTIC for w, _ in mine):
        return
    stored = {a: cells(load(STORED_REAL, a)) for a in ("reference", "rust", "fsharp", "oncrack")}
    print(f"\nRealistic workloads against the same-session baseline of {os.path.relpath(STORED_REAL, ROOT)} (medians; reads/s and posts/s apart)\n")
    print("| Workload | c | lane | onCrack req/s | onCrack stored | Rails | F# port | Rust | **/ F# port** | **/ Rust** | onCrack CPU us/req (all lanes) | stored |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for (w, c), m in sorted(mine.items(), key=lambda kv: (REALISTIC.index(kv[0][0]) if kv[0][0] in REALISTIC else 99, kv[0][1])):
        if w not in REALISTIC:
            continue
        for lane, vals in sorted(m["lanes"].items()):
            ref = {a: med(stored[a].get((w, c), {}).get("lanes", {}).get(lane, [])) for a in stored}
            mr = med(vals)
            ratio = lambda b: f"**{mr / b:.2f}x**" if b else "-"
            st = stored["oncrack"].get((w, c))
            print(f"| {w} | {c} | {lane} | {fmt(mr)}{spread(vals)} | {fmt(ref['oncrack'])} | {fmt(ref['reference'])} | {fmt(ref['fsharp'])} | {fmt(ref['rust'])} | "
                  f"{ratio(ref['fsharp'])} | {ratio(ref['rust'])} | {fmt(med(m['cpu']), 1)} | {fmt(med(st['cpu']), 1) if st else '-'} |")


def source_commit(build):
    """The commit the measured build was made from, not whatever HEAD is when the run is logged (other commits,
    such as the page's, land in between). Mounted builds: the REVISION file bin/publish-mounted writes. Image builds:
    campfire-oncrack:app's org.opencontainers.image.revision label (SOURCE_REVISION). Otherwise HEAD."""
    def run(*cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    if build == "mounted":
        for d in (os.environ.get("MOUNTED_DIR", "/var/tmp/campfire-mounted"),):
            path = os.path.join(d, "REVISION")
            if os.path.exists(path):
                with open(path) as f:
                    rev = f.read().strip()
                if rev:
                    return rev[:7]
    else:
        # Not GIT_REVISION: that is the reference's pinned commit, which the app echoes for parity.
        rev = run("docker", "image", "inspect", "-f", '{{index .Config.Labels "org.opencontainers.image.revision"}}', "campfire-oncrack:app")
        if rev and rev != "<no value>":
            return rev[:7]
    return run("git", "-C", ROOT, "rev-parse", "--short", "HEAD")


def log(args):
    mine = cells(load(args.dir, APP))
    if not mine:
        sys.exit(f"no {APP}-N.json in {args.dir}")
    workloads = {}
    for (w, c), m in mine.items():
        workloads.setdefault(w, {})[f"c{c}"] = {"rps": round(med(m["rps"]), 1), "cpu_us": round(med(m["cpu"]), 1) if m["cpu"] else None, "reps": len(m["rps"]),
                                                **{f"{lane}_rps": round(med(v), 1) for lane, v in m["lanes"].items()}}
    commit = args.commit or source_commit(args.build)
    entry = {"time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "unit": args.unit, "tier": args.tier, "change": args.change, "app": APP,
             **({"description": args.description} if args.description else {}),
             "commit": commit, "build": args.build, "kept": args.kept == "true", "workloads": workloads}
    with open(LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print("logged:", json.dumps(entry))
    subprocess.run([sys.executable, os.path.join(ROOT, "bench/progress/build.py")], check=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare"); c.add_argument("dir")
    l = sub.add_parser("log"); l.add_argument("dir"); l.add_argument("--unit", required=True, help="the unit's topic, e.g. c0, readcache, groupcommit")
    l.add_argument("--tier", type=int, required=True, choices=[2, 3]); l.add_argument("--change", required=True)
    l.add_argument("--kept", required=True, choices=["true", "false"]); l.add_argument("--build", default="mounted"); l.add_argument("--commit")
    l.add_argument("--description", help="what was done, for a dot of its own (the card's \"What was done\"); otherwise the card lists the app commits since the previous dot")
    a = ap.parse_args()
    if a.cmd == "compare":
        sys.exit(1 if compare(a.dir) else 0)
    log(a)
