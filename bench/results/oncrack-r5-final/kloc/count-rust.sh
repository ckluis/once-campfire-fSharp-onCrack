#!/usr/bin/env bash
# count-rust.sh TREE OUTDIR: strips #[cfg(test)] / #[test] items (syn 2.0.119, stripcfg) from TREE/crates/*/src/**/*.rs minus external test files and vendored code,
# in a container, then cloc 2.10. TREE is a `git archive REV crates` extract. Prints code lines and files.
tree=$1; out=$2; rm -rf $out; mkdir -p $out
files=$(cd $tree && find crates -name '*.rs' -path '*/src/*' | grep -v -E '/(tests?|benches|examples|testing|vendor)/' | grep -v -E '(/tests\.rs|/test_support\.rs|/testing\.rs|_test\.rs)$' | sort)
echo "$files" > $out/files.txt
colima ssh -- docker run --rm -v $tree:/tree:ro -v $out:/out -v /Users/clank/Desktop/projects/.r5-kloc-target/release/stripcfg:/stripcfg:ro -w /tree rust:1.98.1-trixie sh -c 'while read f; do mkdir -p /out/s/$(dirname $f); /stripcfg $f > /out/s/$f || echo FAIL $f; done < /out/files.txt'
(cd $out/s && find . -name '*.rs' | xargs perl /Users/clank/Desktop/projects/upstream-campfire/tools/cloc-2.10.pl --by-file --skip-uniqueness --quiet --csv > $out/cloc.csv)
awk -F, '$1=="SUM"{print "code", $5}' $out/cloc.csv
echo "files $(grep -c '^Rust' $out/cloc.csv)"
