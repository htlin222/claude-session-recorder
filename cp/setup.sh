#!/usr/bin/env bash
# cp lesson environment: build a small sample tree inside lab/ so every gcp / gls
# / gstat / gcat / tree command renders a stable, reproducible result. All lesson
# commands `cd lab` first, so the render dir's own scratch (audio/, demo.tape,
# timeline.json…) never pollutes the gls -l / tree output. The engine runs this
# right before every render. Idempotent: it wipes lab/ and recreates it, which
# also clears any copies a previous render produced (copy.txt, docs-backup, …).
set -euo pipefail
DEMO="$(cd "$(dirname "$0")" && pwd)/intermediate"
mkdir -p "$DEMO"
cd "$DEMO"

rm -rf lab
mkdir -p lab
cd lab

# plain source files used across the scenes
printf 'alpha file\n'                 > a.txt
printf 'bravo file\n'                 > b.txt
printf 'quarterly report body\n'      > report.txt
printf 'meeting notes for today\n'    > notes.txt

# a directory to copy files INTO (cp report.txt backup/ etc.)
mkdir -p backup

# a small directory tree for the recursive / archive demos (-r, -rv, -a)
mkdir -p docs
printf '# Guide\nthe guide.\n'        > docs/guide.md
printf 'changelog line 1\n'          > docs/CHANGELOG.txt

# a file with a backdated timestamp, to prove -p / -a preserve mtime
printf 'stamped in 2020\n'            > stamped.txt
touch -t 202001010000 stamped.txt

echo "reset done (cp): lab/ rebuilt."
