#!/usr/bin/env bash
# count-c.sh TREE: C and headers under src/ plus the first-party libvips adapter (vendor/media/cf-vips.c), cloc 2.10; the static Marcel MIME table (src/storage/marcel_tables.h) is data and is left out.
cd $1 && { find src -name '*.[ch]' ! -name marcel_tables.h; echo vendor/media/cf-vips.c; } | xargs perl /Users/clank/Desktop/projects/upstream-campfire/tools/cloc-2.10.pl --by-file --skip-uniqueness --quiet --csv | awk -F, '$1=="SUM"{print "code", $5}'
