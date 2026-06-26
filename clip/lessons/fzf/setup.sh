#!/usr/bin/env bash
# fzf lesson environment: (re)create the deterministic datasets the commands read
# from stdin, so every `fzf -f` prints a stable, reproducible result. The engine
# runs this (via src/setup_dirs.sh) right before every render. Idempotent.
set -euo pipefail
# per-slug workspace: dispatcher exports CLIP_DEMO; fallback derives it from
# this lesson's folder name so the script still works run standalone.
DEMO="${CLIP_DEMO:-$(cd "$(dirname "$0")/../../intermediate" && pwd)/$(basename "$(dirname "$0")")}"
mkdir -p "$DEMO"
cd "$DEMO"

rm -rf pool.txt data.csv proj

# ---- pool.txt: words + paths, in a DELIBERATE order (so --tac / --no-sort show) ----
cat > pool.txt <<'X'
apple
sap
soap
README.md
readme.txt
src/main.py
src/app.py
src/utils.py
main.go
test_app.py
test_utils.py
build.log
server.log
changelog.md
guide.md
notes.txt
X

# ---- data.csv: comma-separated, for -d , --nth 2 (column 2 = name) ----
# row 3's THIRD column also contains "alice", so --nth 2 visibly narrows the match
# to the name column only (just row 1).
cat > data.csv <<'X'
1,alice,frontend
2,bob,backend
3,carol,alice-team
4,alfred,backend
5,dave,frontend
X

# ---- proj/: small file tree, for the find ... | fzf pipeline ----
mkdir -p proj/src proj/docs proj/build
printf 'print("hello")\n'          > proj/src/main.py
printf 'def helper(): return 42\n' > proj/src/app.py
cat > proj/README.md <<'X'
# proj
the project.
X
printf '# Guide\n'                 > proj/docs/guide.md
printf '[INFO] build ok\n'         > proj/build/cache.log

echo "reset done (fzf)."
