#!/usr/bin/env python3
"""Make the "Same software." images from the parity harness's own captures, and record what they prove.

The page shows the signed-in room page (the request bench/run measures as room_show) once, because Rails, Rust, the F# port and
onCrack render it to the same pixels. Two of the four captures are the full pixel gate on the final code (Rails on the reference side, onCrack on the
candidate side of parity/out/pixel-parity-r3-final, the cell bench/results/oncrack-r3-pixels/pixel-parity.json names);
the other two are the port's own check (Rust and the F# port against Rails, recorded in the port's site/data.json "same_pixels" and
committed as its thumbnails). All of them are Chromium at 1440x900, light scheme, the default seed with the clock frozen.

This checks onCrack's and Rails' PNGs byte for byte and decoded pixel for pixel, and against the port's recorded hashes. When all four
agree it writes the page's full-size image (onCrack's own capture, lossless WebP, so still the same pixels) and one thumbnail per app
under site/assets/same-pixels/, and the facts under "oncrack.same_pixels" in site/data.json. site/build.py shows the "Same pixels"
badge only if those facts and the committed thumbnails still agree. parity/out/ is not committed: run this in a checkout that has
round 1's captures. Needs Pillow with WebP and the port's checkout (PORT_CHECKOUT, default ../once-campfire-fsharp, ref side-by-side).

    python3 site/same_pixels.py [--thumb 640]
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

SITE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SITE)
DATA = os.path.join(SITE, 'data.json')
ASSETS = 'site/assets/same-pixels'
PIXELS = 'bench/results/oncrack-r3-pixels/pixel-parity.json'
PORT = os.environ.get('PORT_CHECKOUT', os.path.join(os.path.dirname(REPO), 'once-campfire-fsharp'))
PORT_REF = os.environ.get('PORT_REF', 'side-by-side')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def git_show(path):
    return subprocess.run(['git', '-C', PORT, 'show', '%s:%s' % (PORT_REF, path)], capture_output=True, check=True).stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--thumb', type=int, default=640)
    a = ap.parse_args()
    from PIL import Image, features
    if not features.check('webp'):
        sys.exit('same_pixels: this Pillow has no WebP support')

    room = json.load(open(os.path.join(REPO, PIXELS)))['room_capture']
    report_dir = os.path.dirname(os.path.join(REPO, room['report']))
    port_commit = subprocess.run(['git', '-C', PORT, 'rev-parse', '--short', PORT_REF], capture_output=True, text=True, check=True).stdout.strip()
    port_sp = json.loads(git_show('site/data.json'))['same_pixels']
    os.makedirs(os.path.join(REPO, ASSETS), exist_ok=True)

    apps, pixels = [], set()
    for key, name, side in (('rails', 'Rails', 'reference'), ('oncrack', 'onCrack', 'candidate')):
        png = os.path.join(report_dir, side, room['state'], room['cell'] + '.png')
        raw = open(png, 'rb').read()
        im = Image.open(png).convert('RGB')
        pixels.add(sha(im.tobytes()))
        out = os.path.join(ASSETS, key + '.webp')
        im.resize((a.thumb, round(im.height * a.thumb / im.width)), Image.LANCZOS).save(os.path.join(REPO, out), format='WEBP', lossless=True, quality=100, method=6)
        if key == 'oncrack':
            full, size = im, im.size
        apps.append({'key': key, 'name': name, 'capture_sha256': sha(raw), 'thumb': out, 'harness_verdict': room['status'],
                     'source': '%s (%s side)' % (room['report'], side)})
    for key, name in (('rust', 'Rust'), ('fsharp', 'F# port')):
        rec = next(x for x in port_sp['apps'] if x['key'] == key)
        out = os.path.join(ASSETS, key + '.webp')
        with open(os.path.join(REPO, out), 'wb') as f:
            f.write(git_show(rec['thumb']))
        apps.append({'key': key, 'name': name, 'capture_sha256': rec['capture_sha256'], 'thumb': out, 'harness_verdict': rec['harness_verdict'],
                     'source': "the port's check, parity/out/%s (%s side), recorded in the port's site/data.json at %s" % (rec['run'], rec['side'], port_commit)})
    order = {'rails': 0, 'rust': 1, 'fsharp': 2, 'oncrack': 3}
    apps.sort(key=lambda x: order[x['key']])

    captures = {x['capture_sha256'] for x in apps}
    same = len(captures) == 1 and len(pixels) == 1 and port_sp.get('pixels_sha256') in pixels
    image = None
    if same:
        image = os.path.join(ASSETS, 'room.webp')
        full.save(os.path.join(REPO, image), format='WEBP', lossless=True, quality=100, method=6)
    d = json.load(open(DATA, encoding='utf-8'))
    d.setdefault('oncrack', {})['same_pixels'] = {
        'state': room['state'], 'cell': room['cell'], 'viewport': '%d×%d' % size, 'image': image,
        'page': 'All Talk, the busy room, signed in as David: the page the room_show benchmark requests',
        'identical': same, 'pixels_sha256': sorted(pixels)[0] if len(pixels) == 1 else None,
        'round1_layers_equal': room['layers_equal'], 'port_ref': '%s (%s)' % (PORT_REF, port_commit),
        'checked': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'apps': apps,
    }
    with open(DATA, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write('\n')
    for x in apps:
        print('%-8s png sha256 %s…  %s' % (x['name'], x['capture_sha256'][:16], x['source']))
    print('all four captures byte-identical: %s; decoded pixels identical (and the port\'s): %s' % (len(captures) == 1, same))
    if not same:
        sys.exit('same_pixels: the captures differ; the page will say so instead of "same pixels"')


if __name__ == '__main__':
    main()
