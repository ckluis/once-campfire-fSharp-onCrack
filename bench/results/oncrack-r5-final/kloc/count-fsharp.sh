#!/usr/bin/env bash
# count-fsharp.sh REPO: handwritten src/**/*.fs (git ls-files), minus src/Campfire.Assets.Build (a build-time tool, as Rust's build.rs sits outside crates/*/src), cloc 2.10.
# Prints total code, the html5ever tokenizer port (src/Campfire.RichText/Html5ever, which Rust takes as a crate), and the largest static-data files.
cd $1; CL=/Users/clank/Desktop/projects/upstream-campfire/tools/cloc-2.10.pl
git ls-files 'src/**/*.fs' 'src/*.fs' | grep -v '^src/Campfire.Assets.Build/' | xargs perl $CL --by-file --skip-uniqueness --quiet --csv > ${2:-/dev/stdout}
