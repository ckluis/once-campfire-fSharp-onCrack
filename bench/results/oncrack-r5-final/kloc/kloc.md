# KLOC by upstream's rules, round 5 final (2026-10-12)

Upstream's rule (`once-campfire-verification/docs/performance-review.md`, "Application source size"): 1,000 nonblank, noncomment lines of backend application code, executable
template code included, `cloc 2.10 --by-file --skip-uniqueness`. Tests, vendored code, generated files, benchmark and parity tooling, static data/SQL and build scripts are out.
`cloc` is upstream's own `cloc-2.10.pl` (`/Users/clank/Desktop/projects/upstream-campfire/tools/cloc-2.10.pl`, sha256 `bf592724...`, the same file round 3 used), run on the Mac.

Counted revisions: Rails `0aa339d`, Rust `f9dca47`, C `cd0cbe4` (the checkouts under `/Users/clank/Desktop/projects/upstream-campfire/`, all clean), the F# port at its image's
source (`2e6c08e`; its checkout `9954ad0` changes no `src/`), onCrack at `ee5a2e9` (HEAD; `src/` equals the verifier's last code commit `6abc183`).

| Implementation | Revision | Backend code | Template code | Total | **KLOC** | KLOC with static data left in |
|---|---|---:|---:|---:|---:|---:|
| Rails | `0aa339d` | 4,443 | 1,054 | 5,497 | **5.5** | 5.5 |
| Rust | `f9dca47` | 30,090 | 873 | 30,963 | **31.0** | 35.1 |
| C | `cd0cbe4` | 94,910 | 0 | 94,910 | **94.9** | 108.4 |
| F# port | `2e6c08e` | 38,180 | in the code | 38,180 | **38.2** | 42.5 |
| onCrack | `ee5a2e9` | 41,898 | in the code | 41,898 | **41.9** | 46.2 |

- **Both F# counts include the html5ever tokenizer port** (`src/Campfire.RichText/Html5ever`, 3,582 lines), first-party F# where Rust takes `html5ever` as a vendored crate (not counted
  in Rust). Without it the port is 34.6 and onCrack 38.3.
- **F# templates are F# modules** (rendering code, as Rust's views are Rust), so they sit in the backend column; there is no separate template language to extract.
- **onCrack is 3.7 KLOC (9.7%) larger than the port** (41.9 against 38.2): the caches, the writer, the Cable log and its bounds, the fresh-check pool. It is 35% more than Rust's 31.0 and 44% of C's 94.9.
  Against the previous count (round 3: 44.6 and 42.5, nothing excluded) the all-code column is 46.2 for onCrack: +1.6 KLOC in rounds 4 and 5.
- **Static data left out of the headline** (upstream's rule, and what the calibration below needs), per language; the right-hand column leaves it in:
  Rust `crates/storage/src/tables.rs` (2,987), `campfire/src/integrations/search/word_ranges.rs` (773), `db/src/fixtures.rs` (272), `views/src/helpers/translations_table.rs` (119);
  C `src/storage/marcel_tables.h` (13,461); F# `Campfire.Storage/Tables.fs` (2,701), `Campfire.Views/Helpers/UnicodeTables.fs` (741), `Campfire.Db/Fixtures.fs` (319),
  `Campfire.RichText/Unicode/WordRanges.fs` (203), `Campfire.App/Integrations/SearchWordRanges.fs` (197), `Campfire.Views/Helpers/TranslationsTable.fs` (134).

## Method, file by file

- **Rails**: `app/{models,controllers,helpers,jobs,channels}`, `lib` without `lib/tasks`, `config` without `ci.rb`, `puma_dev.rb` and the development, test and performance environments,
  `db/migrate`, `config.ru` (Ruby): 4,443. Templates: `app/views/**/*.erb` through `bench/template_code.rb erb` (1,020) and the Jbuilder files as Ruby (34): 1,054.
- **Rust**: `crates/*/src/**/*.rs` without `tests/`, `benches/`, `examples/`, `vendor/`, `tests.rs`, `test_support.rs`, `testing.rs` and `*_test.rs`; `#[cfg(test)]` and `#[test]` items removed with
  `syn 2.0.119` (`stripcfg/`: it parses each file and blanks the line range of every gated item, so every other line is byte for byte upstream's). `build.rs` is not counted (the port's build-time
  tool is left out the same way). Templates: `crates/views/templates/**` (but the browser service worker) through `template_code.rb askama`: 873.
- **C**: `src/**/*.[ch]` and the first-party libvips adapter `vendor/media/cf-vips.c`.
- **F#**: `git ls-files 'src/**/*.fs'` without `src/Campfire.Assets.Build` (a build-time tool).
- Reproduce: `kloc/count-rails.sh`, `count-rust.sh`, `count-c.sh`, `count-fsharp.sh` (they write the per-file cloc output kept in `kloc/data/`), then `python3 kloc/kloc.py` (writes `kloc.json`).

## Calibration: does this method reproduce upstream's published numbers?

Upstream's table counts other revisions for Rust (`6838ead`) and C (`ddaafaf`), so I ran the same method on those:

| | upstream published | this method | |
|---|---:|---:|---|
| Rails `0aa339d` backend / template | 4,443 / 1,054 | 4,443 / 1,054 | exact |
| Rust `6838ead` template | 873 | 873 | exact |
| Rust `6838ead` backend | 29,784 | 30,085 (34,236 with static data) | +301, +1.0% |
| C `ddaafaf` | 94,816 | 94,910 (108,371 with static data) | +94, +0.1% |

Rails and the Rust templates reproduce to the line. Upstream does not publish its file lists for Rust and C, so which data files it leaves out is inferred: leaving out the four Rust data modules and
C's Marcel table lands within 1.0% and 0.1%; leaving them in is 15% and 14% over. **Read Rust's 31.0 and C's 94.9 as within 1% of what upstream's own tooling would print, not exact.** The F# counts apply the
same exclusions to the same kinds of file; they are my selection and carry the same caveat.
