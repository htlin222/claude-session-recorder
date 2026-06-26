#!/usr/bin/env bash
# grep lesson environment: build a fixed sample of log files (logs/) and a small
# source tree (src/) so every R() command produces stable, non-interactive,
# self-terminating output. Run via src/setup_dirs.sh right before each `vhs`
# render. Idempotent: wipes and recreates its own dirs.
set -euo pipefail
# per-slug workspace: dispatcher exports CLIP_DEMO; fallback derives it from this
# lesson's folder name so the script still works run standalone.
DEMO="${CLIP_DEMO:-$(cd "$(dirname "$0")/../../intermediate" && pwd)/$(basename "$(dirname "$0")")}"
mkdir -p "$DEMO"
cd "$DEMO"

rm -rf logs src

mkdir -p logs src/lib

# ---- logs/app.log : mixed-level lines crafted for every grep flag ----
# INFO / WARN / ERROR levels (basic, -i lowercase error, -v, -E ERROR|WARN),
# user=<name> fields (-o), standalone `id` vs idle/identifier (-w), and an
# indented follow-up line after each ERROR (-A / -C context).
cat > logs/app.log <<'X'
2026-06-26 08:00:01 INFO  starting service user=alice
2026-06-26 08:00:02 DEBUG loaded config id=42 user=bob
2026-06-26 08:01:10 WARN  cache miss for user=carol
2026-06-26 08:02:00 ERROR failed to connect user=dave
2026-06-26 08:02:00 ERROR   retrying connection now
2026-06-26 08:03:15 INFO  request id=1001 served ok
2026-06-26 08:04:20 error lowercase error sample user=erin
2026-06-26 08:05:00 WARN  high latency on identifier lookup
2026-06-26 08:06:30 ERROR timeout while reading user=frank
2026-06-26 08:06:30 ERROR   closing socket cleanly
2026-06-26 08:07:00 INFO  the id is valid, idle workers ready
2026-06-26 08:08:45 INFO  shutdown complete user=grace
X

# ---- logs/access.log : a second file so logs/ is a believable tree ----
cat > logs/access.log <<'X'
127.0.0.1 - GET /health 200 user=alice
127.0.0.1 - GET /login 200 user=bob
127.0.0.1 - POST /pay 500 user=dave
X

# ---- src/ : a small source tree with TODO markers (for -r / -rl) ----
cat > src/main.py <<'X'
def main():
    # TODO: refactor this entrypoint
    print("hello")
X
cat > src/utils.py <<'X'
def helper():
    return 42  # TODO handle the error case
X
cat > src/lib/cache.py <<'X'
CACHE = {}


def get(k):
    return CACHE.get(k)
X

echo "reset done (grep)."
