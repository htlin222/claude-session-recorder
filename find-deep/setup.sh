#!/usr/bin/env bash
# find-deep lesson environment: build a sample project tree `app/` in its INITIAL
# state. It exercises every predicate/action the lesson teaches: multi-depth .py
# (-name / -mindepth), mixed-case .JS (-iname), directories (-type d), a >1MB file
# (-size), an empty file + empty dir (-empty), a top-level layer (-maxdepth),
# backdated timestamps with a few "now" files (-mtime), a reference file .stamp
# (-newer), a logs/ subtree (-path), node_modules/ (-prune), .log files (-exec),
# and .tmp files (-delete). Idempotent: wipes and recreates app/ each run.
set -euo pipefail
DEMO="$(cd "$(dirname "$0")" && pwd)/intermediate"
mkdir -p "$DEMO"
cd "$DEMO"

rm -rf app

mkdir -p app/src/web app/src/lib app/docs app/data app/logs app/build \
         app/node_modules/leftpad app/cache

# ── top-level files (the -maxdepth 1 layer) ────────────────────────────────
printf 'const app = true;\n'          > app/app.js          # top-level .js
printf 'print("entry point")\n'       > app/main.py         # top-level .py (mindepth skips)
cat > app/README.md <<'X'
# app
the demo project.
X
printf 'lowercase readme\n'           > app/readme.txt
printf 'name: app\n'                  > app/config.yaml
printf 'time-reference marker\n'      > app/.stamp          # -newer baseline (non-empty)

# ── source: .py at varying depths (-name / -mindepth 2) ───────────────────
printf 'def core(): return 1\n'       > app/src/core.py
printf 'def util(): return 2\n'       > app/src/util.py
printf 'def deep(): return 3\n'       > app/src/lib/deep.py

# ── mixed-case .js (-iname '*.js') ────────────────────────────────────────
printf 'export const main = 1;\n'     > app/src/web/Main.JS
printf 'export const help = 2;\n'     > app/src/web/Helper.Js

# ── docs, incl. one EMPTY file (-empty) ───────────────────────────────────
printf '# Guide\n'                    > app/docs/guide.md
: >                                     app/docs/empty.md    # zero-byte file

# ── logs subtree (-path '*/logs/*') and .log files (-exec wc -l) ──────────
printf '[INFO] start\n[INFO] ready\n' > app/logs/debug.log
printf '[ERR] boom\n'                 > app/logs/error.log

# ── build artefacts: .tmp files (-delete) ─────────────────────────────────
printf 'scratch\n'                    > app/build/cache.tmp
printf 'more scratch\n'               > app/build/old.tmp

# ── a >1 MB data file (-size +1M) ─────────────────────────────────────────
head -c 2000000 /dev/urandom          > app/data/archive.bin

# ── a relied-upon dependency dir to -prune ────────────────────────────────
printf 'module.exports = s => s;\n'   > app/node_modules/leftpad/index.js

# app/cache/ is intentionally left empty (an empty DIR for -empty)

# Backdate the WHOLE tree to last year so -mtime -1 / -newer start out matching
# nothing, then bump a couple of files to "now" — exactly those become the
# recently-modified hits (and the files newer than .stamp).
find app -exec touch -t 202401010000 {} +
touch app/main.py app/src/core.py app/logs/error.log

echo "reset done (find-deep)."
