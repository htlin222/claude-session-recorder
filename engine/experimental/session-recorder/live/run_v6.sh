#!/usr/bin/env bash
set -euo pipefail
LIVE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SR="$(dirname "$LIVE")"
REPO="$(cd "$SR/../../.." && pwd)"
PY="$REPO/.venv/bin/python"
DEMO="${1:?usage: run_v6.sh <demo-dir> <script.json>}"
SCRIPT="${2:?usage: run_v6.sh <demo-dir> <script.json>}"

echo "== v6 pipeline =="
# Phase 0a — isolated sandbox (idempotent)
bash "$LIVE/claude_sandbox.sh" "$DEMO"
# Phase 0b — minimal capture tape + capture.json (no voice)
"$PY" "$LIVE/gen_capture_tape.py" --demo "$DEMO" --script "$SCRIPT" \
      --width 1200 --height 1080 --font-size 26 -o "$DEMO/session.tape"
# Phase 0c — film the real TUI ONCE (claude launches here, and ONLY here).
#   Export SR/HERE so the sandbox's claude-spawned project hooks resolve
#   $SR/timelog.py and $HERE/vhs_stop_sentinel.sh.
export SR HERE="$LIVE"
rip -f "$SR/session-timeline.jsonl" 2>/dev/null || true
#   Sanitize the inherited prompt env (defense-in-depth): VHS defaults to bash
#   and would otherwise inherit an exported p10k PS1, dumping ${_p9k_…} full-screen.
unset PS1 PROMPT _P9K_TTY _P9K_SSH_TTY 2>/dev/null || true
( cd "$DEMO" && env -u PS1 -u PROMPT -u _P9K_TTY -u _P9K_SSH_TTY vhs session.tape )
# Phase 1 — detect anchors + author voice/ledger (detection runs in-process here,
#           so claude is NOT relaunched)
"$PY" "$LIVE/author.py" --demo "$DEMO" --script "$SCRIPT"
# Phase 2 — freeze-frame splice (reconciles the ledger to the realized video)
"$PY" "$LIVE/splice.py" --demo "$DEMO"
# Phase 2 — mux voice from the ledger
"$PY" "$LIVE/overlay.py" --demo "$DEMO"
# Phase 2 — build the right-side panel from the SAME ledger
"$PY" "$LIVE/panel.py" --demo "$DEMO"
# Phase 3 — deterministic gate (+ eyeball filmstrip)
"$PY" "$LIVE/lint.py" --demo "$DEMO" --filmstrip
echo "== done: $DEMO/session_panel.mp4 =="
