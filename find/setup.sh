#!/usr/bin/env bash
# find lesson environment: build a sample project tree `proj/` in its INITIAL
# state. Most files are backdated so `-mtime -1` is meaningful; a couple are
# bumped to "now" so exactly those show up as recently modified. Run via
# src/setup_dirs.sh right before every `vhs` render.
set -euo pipefail
DEMO="$(cd "$(dirname "$0")" && pwd)/intermediate"
mkdir -p "$DEMO"
cd "$DEMO"

rm -rf proj

mkdir -p proj/src/lib proj/docs proj/data proj/logs proj/build

# source (some .py at varying depths, for -name '*.py')
printf 'print("hello")\n'            > proj/src/app.py
printf 'def helper(): return 42\n'   > proj/src/utils.py
printf 'def deep(): return 1\n'      > proj/src/lib/helper.py

# two README spellings, for -iname 'readme*' (case-insensitive)
cat > proj/README.md <<'X'
# proj
the project.
X
printf 'lowercase readme\n'          > proj/readme.txt

# docs / logs / build artefacts
printf '# Guide\n'                   > proj/docs/guide.md
printf 'misc notes\n'                > proj/docs/notes.md
printf '[INFO] ok\n'                 > proj/logs/debug.log
printf 'tmp junk\n'                  > proj/build/cache.tmp
printf 'name: proj\n'                > proj/config.yaml

# a >1 MB data file, for -size +1M
head -c 2000000 /dev/urandom         > proj/data/archive.bin

# backdate the WHOLE tree to last year, so -mtime -1 starts out matching nothing
find proj -exec touch -t 202401010000 {} +
# then bump a couple of files to "now" — these are the -mtime -1 hits
touch proj/src/app.py proj/docs/notes.md

echo "reset done (find)."
