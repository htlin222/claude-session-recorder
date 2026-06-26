#!/usr/bin/env bash
# rsync lesson environment: (re)create the source/dest folders in their INITIAL
# state. The engine runs this (via src/setup_dirs.sh) right before every render.
set -euo pipefail
DEMO="$(cd "$(dirname "$0")/../../intermediate" && pwd)"
cd "$DEMO"

rm -rf A B C

# ---- Source folder A (a small "project") ----
mkdir -p A/src A/docs A/data A/.cache A/logs
cat > A/README.md <<'X'
# MyProject
The single source of truth.
X
printf 'print("hello from app")\n'      > A/src/app.py
printf 'def helper(): return 42\n'       > A/src/utils.py
cat > A/docs/guide.md <<'X'
# Guide
Step 1. Read.
Step 2. Sync.
X
printf 'name: myproject\nversion: 2\n'  > A/config.yaml
# a 6 MB binary so -z / --progress are meaningful
head -c 6000000 /dev/urandom            > A/data/archive.bin
# noise we will later EXCLUDE
printf 'cached junk\n'                   > A/.cache/build.cache
printf '[INFO] build ok\n'               > A/logs/debug.log

# ---- Dest folder B (already exists, slightly out of date) ----
mkdir -p B/src
cat > B/README.md <<'X'
# MyProject (OLD)
outdated copy
X
printf 'print("OLD app")\n'              > B/src/app.py
# a stale file that does NOT exist in A (mirror/--delete will remove it)
printf 'last year notes\n'               > B/obsolete.txt

echo "reset done (rsync)."
