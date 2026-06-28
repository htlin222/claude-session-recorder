#!/usr/bin/env bash
# superseded by record.py (record-session CLI); kept for reference.
# run_v6_tmux.sh — the v6 pipeline, but claude is filmed INSIDE a dedicated-socket
# tmux that VHS renders, while a BACKGROUND qmonitor.py answers ANY on-screen
# AskUserQuestion (a robustness safety net for UNKNOWN questions, keeping the VHS
# visual). Everything after capture is identical to run_v6.sh.
#
# Hard-won SPIKE findings baked in here (REQUIREMENTS, not options):
#   * VHS tape `Env` cannot escape quotes -> the answer policy `{"*":0}` is passed
#     via the REAL process env when launching vhs, NEVER as a tape Env line.
#   * a DEDICATED tmux socket `-L vhsq` (not the default server) avoids colliding
#     with the user's tmux and keeps env inheritance working — every tmux call
#     here AND in qmonitor uses `-L vhsq`.
#   * tmux is visually invisible via a status-off config (tmux.conf, written here).
set -euo pipefail
LIVE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SR="$(dirname "$LIVE")"
REPO="$(cd "$SR/../../.." && pwd)"
PY="$REPO/.venv/bin/python"
DEMO="${1:?usage: run_v6_tmux.sh <demo-dir> <script.json>}"
SCRIPT="${2:?usage: run_v6_tmux.sh <demo-dir> <script.json>}"
SOCKET="vhsq"
NAME="vhsq"

echo "== v6 tmux pipeline =="
# Phase 0a — isolated sandbox (idempotent)
bash "$LIVE/claude_sandbox.sh" "$DEMO"
# Phase 0a' — status-off tmux config so the rendered pane shows NO tmux chrome.
cat > "$DEMO/tmux.conf" <<'CONF'
# invisible tmux for VHS recording: no status bar, no mouse capture.
set -g status off
set -g mouse off
CONF
# Phase 0b — tmux-mode capture tape (the whole session runs inside tmux -L vhsq)
"$PY" "$LIVE/gen_capture_tape.py" --demo "$DEMO" --script "$SCRIPT" \
      --tmux --tmux-socket "$SOCKET" \
      --width 1200 --height 1080 --font-size 26 -o "$DEMO/session.tape"

# Phase 0c — film the real TUI ONCE inside tmux. claude launches here, ONLY here.
#   Export SR/HERE so the sandbox's claude-spawned project hooks resolve
#   $SR/timelog.py and $HERE/vhs_stop_sentinel.sh.
export SR HERE="$LIVE"
rip -f "$SR/session-timeline.jsonl" 2>/dev/null || true
# Clean slate on our PRIVATE socket (never touches the user's default server).
tmux -L "$SOCKET" kill-server 2>/dev/null || true
# Background safety net: qmonitor drives the on-screen selector for ANY question
# (it polls the same dedicated socket the tape's tmux runs on).
"$PY" "$LIVE/qmonitor.py" --session "$NAME" --socket "$SOCKET" \
      --signal-dir "$DEMO" --max-wait 90 &
MON=$!
#   Sanitize the inherited prompt env (defense-in-depth) and pass the answer
#   policy + question mode via the REAL process env (tape Env can't escape quotes).
#   VHS_ANSWERS default {"*":0} == always pick the FIRST option for unknown Qs.
unset PS1 PROMPT _P9K_TTY _P9K_SSH_TTY 2>/dev/null || true
( cd "$DEMO" && env -u PS1 -u PROMPT -u _P9K_TTY -u _P9K_SSH_TTY \
    VHS_QUESTION_MODE=render VHS_SIGNAL_DIR="$DEMO" \
    VHS_ANSWERS="${VHS_ANSWERS:-{\"*\":0}}" vhs session.tape )
# Stop the monitor and tear down our private tmux server.
touch "$DEMO/.qmonitor_stop"
kill "$MON" 2>/dev/null || true
wait "$MON" 2>/dev/null || true
tmux -L "$SOCKET" kill-server 2>/dev/null || true

# Phase 1 — detect anchors + author voice/ledger (in-process; claude NOT relaunched)
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
