#!/usr/bin/env bash
# count-rails.sh REPO: backend Ruby (app models/controllers/helpers/jobs/channels, lib minus tasks, config minus ci/puma_dev/development/test/performance environments, db/migrate, config.ru)
# plus template code (ERB through bench/template_code.rb, Jbuilder as Ruby), cloc 2.10. Calibrated: 0aa339d gives 4,443 + 1,054, upstream's published figures.
repo=$1; V=/Users/clank/Desktop/projects/once-campfire-verification; CL=/Users/clank/Desktop/projects/upstream-campfire/tools/cloc-2.10.pl
cd $repo
back=$( { git ls-files app/models app/controllers app/helpers app/jobs app/channels lib config db/migrate config.ru | grep -E '\.(rb|rake|ru)$' | grep -v -E '^lib/tasks/|^config/(ci|puma_dev)\.rb$|^config/environments/(development|test|performance)\.rb$'; } | xargs perl $CL --by-file --skip-uniqueness --quiet --csv | awk -F, '$1=="SUM"{print $5}')
T=$(mktemp -d)
for f in $(git ls-files 'app/views/**/*.erb' 'app/views/*.erb'); do ruby $V/bench/template_code.rb erb $f > $T/$(echo $f | tr / _).rb; done
erb=$(cd $T && perl $CL --by-file --skip-uniqueness --quiet --csv *.rb | awk -F, '$1=="SUM"{print $5}')
jb=$(git ls-files 'app/views/*.jbuilder' | xargs perl $CL --by-file --skip-uniqueness --quiet --csv --force-lang=Ruby | awk -F, '$1=="SUM"{print $5}')
rm -rf $T
echo "backend $back template $((erb + jb)) (erb $erb jbuilder $jb)"
