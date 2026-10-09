# R3.1: the full pixel gate on the final code, 2026-10-09

Round 2's final review (`oncrack-r2-final.md`, item 12) ran only a 252-screenshot targeted gate after the verifier's fixes changed `src/`,
while the page still showed the 940/940 of round one's gate on the code before those fixes. This is the full gate on the final code.

- **Image:** `campfire-candidate-oncrack` on `campfire-oncrack:app`, rebuilt with `parity/bin/candidate build` from HEAD `d708910`
  (label `org.opencontainers.image.revision` = `d708910d3d29`). `git diff 2ea9ae9 HEAD -- src` is empty: `2ea9ae9` is the last commit
  that touched `src/`, so the image is the code of the benchmark's `f5352d0`, too. Docker's layer cache served every build stage (9 s),
  which is right: the inputs were the same bytes.
- **Gate:** `bin/pixel-parity`, the lean matrix (every state on Chromium desktop and phone, light and dark; the smoke states on Firefox and
  WebKit; the breakpoint sweep), against the Rails reference `90b3300`, screenshot layer only.
- **Result: 940/940 screenshots pixel-equal, 0 different, 0 not captured, 0 flaky.**

| Seed | Equal | Screenshots |
|---|---:|---:|
| default | 860 | 860 |
| crowd | 24 | 24 |
| custom_styles | 32 | 32 |
| first_run | 16 | 16 |
| restricted | 8 | 8 |
| all | 940 | 940 |

  Per engine the counts equal round one's in every seed (`pixel-parity.json` against `oncrack-round1-final/review/pixel-parity.json`), so the
  same cells ran. The room page capture (`rooms/show/busy/last_page`, Chromium desktop light) is byte-identical on both sides, and equal to
  round one's hash `ac7420e6d0a8`.
- **How it ran:** the four small seeds in one call (263 s). The default seed in twelve `--only` slices (A-L, the globs are `SLICES` in
  `bench/results/oncrack-r3-pixels/pixel_parity.py`), each one foreground call, 76 s to 27 min (`realtime/**` is the long one, 1,603 s).
  `pixel_parity.py` checks that no cell ran in two slices and that the slices add up to 860. Logs are in `oncrack-r3-pixels/logs/`.
- **The only state the harness had trouble capturing:** `auth/sign_in/error`. On freshly started servers its page waited 30 s for stylesheets
  and gave up ("not ready after 30000ms ... settling [GET /assets/*.css]"), as in round one and unit C0: desktop dark in the slice's
  run, then desktop dark and phone light in the first re-run, phone light in the second. Every one of its four cells captured in some attempt and was equal;
  a cell counts by its last attempt that captured it, as `bin/pixel-parity` counts it. No other state needed a re-run. This is the
  harness's wait, not a pixel difference, and it is not new with this code.
- **Guards:** no core dump appeared (`parity/core` checked after every slice; the capture containers run with `--ulimit core=0`).
  `bin/pixel-parity` now checks after every compare, deletes any `parity/core*` and prints the VM's free space.
  `bin/clean-docker` (with `fstrim`) ran after every slice. The Mac's free space started at 14 GB, fell to 11 GB by the end of the
  first default slice (A, 5 minutes; below the 12 GB floor) and was back to 14 GB after the trim; the run paused there until the trim was done.
  Later slices ended at 13-16 GB after the trim. The VM's growth is transient (containers' layers and logs), so trim between slices.
- **The page** (`index.html`) now takes its pixel-parity numbers and its room-page capture check from
  `bench/results/oncrack-r3-pixels/pixel-parity.json`; `site/build.py` fails unless every number is sourced there. The count did not change
  (940 of 940), and the claim now matches the code it is about.

Reproduce (inside colima, from the repository root):

```sh
CAMPFIRE_REVISION=$(git rev-parse HEAD) parity/bin/candidate build
bin/pixel-parity --seeds crowd,custom_styles,first_run,restricted --out parity/out/pixel-parity-r3-final/small
bin/pixel-parity --seeds default --only 'realtime/**' --out parity/out/pixel-parity-r3-final/I   # ... the other eleven slices
python3 bench/results/oncrack-r3-pixels/pixel_parity.py && python3 site/same_pixels.py && python3 site/build.py
```
