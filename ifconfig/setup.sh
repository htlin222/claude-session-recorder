#!/usr/bin/env bash
# ifconfig lesson environment. ifconfig inspects the machine's LIVE network
# interfaces (lo0, en0, …) read-only, so there is no sample tree to fabricate —
# the "data" is the real interface table, which renders stably and is never
# modified by this lesson. We still honour the engine's setup contract: create
# intermediate/ so the render has a working directory, and drop a tiny note so
# the folder isn't empty. Idempotent: safe to run before every render.
set -euo pipefail
DEMO="$(cd "$(dirname "$0")" && pwd)/intermediate"
mkdir -p "$DEMO"
cd "$DEMO"

rm -rf scratch
mkdir -p scratch
cat > scratch/README.txt <<'TXT'
ifconfig lesson: read-only inspection of live interfaces (lo0/en0). No setup
needed beyond this directory; nothing here is consumed by the commands.
TXT

echo "reset done (ifconfig): inspecting live interfaces, nothing modified."
