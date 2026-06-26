#!/usr/bin/env bash
# Dispatcher: run the ACTIVE lesson's setup.sh (lessons/<active>/setup.sh),
# which (re)creates that lesson's demo environment in intermediate/. The active
# lesson is read from config.toml ([lesson] active); defaults to rsync.
# Re-run this right before every `vhs demo.tape` render.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SRC/.." && pwd)"

# $LESSON env wins (matches build.py / the /clip workflow); else read config.
ACTIVE="${LESSON:-$(python3 - "$ROOT/config.toml" <<'PY'
import sys, tomllib
cfg = tomllib.load(open(sys.argv[1], "rb"))
print(cfg.get("lesson", {}).get("active", "rsync"))
PY
)}"

SETUP="$ROOT/lessons/$ACTIVE/setup.sh"
[ -f "$SETUP" ] || { echo "no setup.sh for lesson '$ACTIVE' ($SETUP)" >&2; exit 1; }
echo "setup: lesson '$ACTIVE'"
exec bash "$SETUP"
