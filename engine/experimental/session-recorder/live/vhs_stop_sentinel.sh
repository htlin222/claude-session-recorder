#!/bin/sh
# vhs_stop_sentinel.sh — Stop hook that prints an on-screen, incrementing marker
# (VHS_TURN_DONE_1, _2, ...) so a VHS tape can `Wait+Screen@<t> /VHS_TURN_DONE_N/`
# on a SPECIFIC turn instead of guessing a Sleep. Complements timelog.py (which
# logs the JSONL timeline but emits nothing on screen).
#
# CRITICAL: this marker is a hook `systemMessage`, which Claude Code's FOCUS MODE
# HIDES. If you film outside claude_sandbox.sh (i.e. with your normal config and
# focus on), the marker never renders and every Wait times out. The sandbox's
# fresh CLAUDE_CONFIG_DIR starts with focus OFF, so the marker shows. Do not
# record live sessions without the sandbox.
#
# Gated on $VHS_DEMO so it is inert in normal (non-recording) sessions.
[ -n "$VHS_DEMO" ] || exit 0

sid=$(jq -r '.session_id // "default"' 2>/dev/null)
sid="${sid:-default}"
f="${TMPDIR:-/tmp}/vhs-session-${sid}.count"
n=$(( $(cat "$f" 2>/dev/null || echo 0) + 1 ))
echo "$n" > "$f"
printf '{"systemMessage": "VHS_TURN_DONE_%d"}\n' "$n"
