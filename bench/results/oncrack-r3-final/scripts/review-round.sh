#!/usr/bin/env bash
# review-round.sh TAG VARIANT...: runs INSIDE colima: review.py (room page, mixed, post; 15 s warm-up, 10 s window, 16 clients, server CPU from the
# cgroup) once per variant, in the order given, appending to review.jsonl. Variants: fresh (onCrack default), cached (CAMPFIRE_FRESH_AUTH=0), rust, c.
tag=$1; shift
R=/Users/clank/Desktop/projects/once-campfire-fsharp-oncrack/bench/results/oncrack-r3-final
for v in "$@"; do
  case $v in
    fresh)  a=oncrack; i=campfire-oncrack:app; e='{"CAMPFIRE_RESPONSE_CACHE_MB":"64"}'; t="fresh-$tag" ;;
    cached) a=oncrack; i=campfire-oncrack:app; e='{"CAMPFIRE_RESPONSE_CACHE_MB":"64","CAMPFIRE_FRESH_AUTH":"0"}'; t="cached-$tag" ;;
    rust)   a=rust; i=campfire-rust-upstream:f9dca47; e='{}'; t="r-$tag" ;;
    c)      a=c; i=campfire-c-upstream:cd0cbe4; e='{}'; t="c-$tag" ;;
  esac
  echo "== $v ($t) $(date +%T)"
  python3 $R/review.py $a $i $R/review.jsonl --env "$e" --tag "$t" --secs 10 --warmup 15 || echo "FAILED $v"
  docker ps -aq --filter name=cf-review | xargs -r docker rm -f >/dev/null
done
