#!/usr/bin/env python3
"""KLOC by upstream's rules (docs/performance-review.md in once-campfire-verification): cloc 2.10 --by-file --skip-uniqueness, backend code plus executable template code,
read from data/*.csv (the per-file cloc output of count-*.sh). Writes kloc.json and kloc.md.

Static-data modules are left out of the headline as upstream's rule says ("static data/SQL ... excluded"); the all-code count is beside it. The set was calibrated against
upstream's published figures at other revisions (kloc.md, "Calibration")."""
import csv, json, os
H = os.path.dirname(os.path.abspath(__file__))

def rows(name):
    out = {}
    for r in csv.reader(open(os.path.join(H, 'data', name))):
        if len(r) >= 5 and r[0] not in ('language', 'SUM'):
            out[r[1].lstrip('./')] = int(r[4])
    return out

def total(d, excl=()):
    return sum(v for k, v in d.items() if not any(k.endswith(e) for e in excl))

RUST_DATA = ('crates/storage/src/tables.rs', 'crates/campfire/src/integrations/search/word_ranges.rs', 'crates/db/src/fixtures.rs', 'crates/views/src/helpers/translations_table.rs')
C_DATA = ('src/storage/marcel_tables.h',)
FS_DATA = ('src/Campfire.Storage/Tables.fs', 'src/Campfire.Views/Helpers/UnicodeTables.fs', 'src/Campfire.Db/Fixtures.fs', 'src/Campfire.RichText/Unicode/WordRanges.fs',
           'src/Campfire.App/Integrations/SearchWordRanges.fs', 'src/Campfire.Views/Helpers/TranslationsTable.fs')
rails = open(os.path.join(H, 'data', 'rails-0aa339d.txt')).read().split()
rails_back, rails_tpl = int(rails[1]), int(rails[3])

res = {}
def add(name, rev, back, back_all, tpl, extra=None):
    res[name] = dict(revision=rev, backend_code=back, backend_code_with_static_data=back_all, template_code=tpl, total=back + tpl, kloc=round((back + tpl) / 1000, 1),
                     kloc_with_static_data=round((back_all + tpl) / 1000, 1), **(extra or {}))
add('Rails', '0aa339d', rails_back, rails_back, rails_tpl)
r = rows('rust-f9dca47-backend.csv'); t = rows('rust-f9dca47-templates.csv')
add('Rust', 'f9dca47', total(r, RUST_DATA), total(r), total(t))
c = rows('c-cd0cbe4.csv')
add('C', 'cd0cbe4', total(c, C_DATA), total(c), 0)
for name, f, rev in (('F# port', 'fsharp-port.csv', '2e6c08e (image campfire-fsharp:app; checkout 9954ad0 changes no src/)'), ('onCrack', 'oncrack-ee5a2e9.csv', 'ee5a2e9 (HEAD; src/ equals 6abc183)')):
    d = rows(f)
    h5 = sum(v for k, v in d.items() if '/Html5ever/' in k)
    add(name, rev, total(d, FS_DATA), total(d), 0, dict(files=len(d), html5ever_port_code=h5, kloc_without_html5ever=round((total(d, FS_DATA) - h5) / 1000, 1)))
calib = {}
r0 = rows('rust-6838ead-backend.csv'); t0 = rows('rust-6838ead-templates.csv'); c0 = rows('c-ddaafaf.csv')
calib['Rails 0aa339d'] = dict(published_backend=4443, mine_backend=rails_back, published_template=1054, mine_template=rails_tpl)
calib['Rust 6838ead'] = dict(published_backend=29784, mine_backend=total(r0, RUST_DATA), mine_backend_with_static_data=total(r0), published_template=873, mine_template=total(t0))
calib['C ddaafaf'] = dict(published_backend=94816, mine_backend=total(rows('c-ddaafaf.csv'), C_DATA), mine_backend_with_static_data=total(c0))
out = dict(cloc='2.10 (sha256 bf59272455172108072a0a106379f7509fd4349bdcfd85203bac038ccd286d83)', options='--by-file --skip-uniqueness',
           static_data_excluded=dict(rust=RUST_DATA, c=C_DATA, fsharp=FS_DATA), counts=res, calibration=calib)
json.dump(out, open(os.path.join(H, 'kloc.json'), 'w'), indent=1)
L = ['| Implementation | Revision | Backend code | Template code | Total | **KLOC** | KLOC with static data |', '|---|---|---:|---:|---:|---:|---:|']
for k, v in res.items():
    L.append('| %s | %s | %s | %s | %s | **%.1f** | %.1f |' % (k, v['revision'].split(' ')[0], format(v['backend_code'], ','), format(v['template_code'], ','), format(v['total'], ','), v['kloc'], v['kloc_with_static_data']))
open(os.path.join(H, 'kloc-table.md'), 'w').write('\n'.join(L) + '\n')
print('\n'.join(L)); print(json.dumps(calib, indent=1))
for k in ('F# port', 'onCrack'): print(k, 'html5ever', res[k]['html5ever_port_code'], 'KLOC without it', res[k]['kloc_without_html5ever'], 'files', res[k]['files'])
