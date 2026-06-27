#!/usr/bin/env bash
# claude_sandbox.sh — stage a CLEAN, ISOLATED Claude Code project for VHS recording.
#
# Why this exists: filming a real `claude` TUI fails the moment the recording
# inherits your normal user config. The traps we actually hit (in order):
#   1. FOCUS MODE hides hook systemMessages  -> the VHS_TURN_DONE_N sentinel
#      never renders -> every `Wait+Screen /sentinel/` times out. THE killer.
#   2. "Claude in Chrome extension detected" dialog blocks startup.
#   3. Fresh config defaults to an unavailable model -> a banner covers the UI.
#   4. MCP-auth warnings + your global CLAUDE.md leak into the frame (ugly).
# Fix: give the inner session its OWN user-config dir via CLAUDE_CONFIG_DIR,
# seeded so it skips every dialog, and keep ONLY the project-level hooks.
#
# Result: a sandbox where focus is OFF by default (sentinel shows), no dialogs,
# Catppuccin-clean frame. The tape just does `Env CLAUDE_CONFIG_DIR "<cfg>"`.
#
# Usage:  ./claude_sandbox.sh /path/to/demo-dir
# Produces:  <demo-dir>/.cfg/         isolated user config (credentials, no dialogs)
#            <demo-dir>/.claude/settings.json   project hooks: timelog + sentinel
set -euo pipefail

DEMO="${1:?usage: claude_sandbox.sh <demo-dir>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SR="$(dirname "$HERE")"                         # session-recorder/
GLOBAL_CFG="${CLAUDE_CONFIG_DIR_GLOBAL:-$HOME/.claude}"
MODEL="${SANDBOX_MODEL:-opus}"

mkdir -p "$DEMO/.cfg" "$DEMO/.claude"

# --- auth: on this machine it's a FILE (not keychain) -> copy it in to skip login
if [ -f "$GLOBAL_CFG/.credentials.json" ]; then
  command cp "$GLOBAL_CFG/.credentials.json" "$DEMO/.cfg/.credentials.json"
else
  echo "WARN: $GLOBAL_CFG/.credentials.json not found — sandbox will prompt for login" >&2
fi

# --- isolated user config: skip onboarding/theme/trust + kill the chrome dialog
#     (cachedChromeExtensionInstalled:false => it never detects the extension;
#      there is NO documented settings.json key for this — it lives in .claude.json)
#     Trust is keyed by the path claude actually runs in: on macOS /tmp is a
#     symlink to /private/tmp, so seed BOTH the logical and realpath forms or the
#     trust dialog still fires.
python3 - "$DEMO/.cfg/.claude.json" "$DEMO" <<'PY'
import json, os, sys
out, demo = sys.argv[1], sys.argv[2]
proj = {"hasTrustDialogAccepted": True, "projectOnboardingSeenCount": 5,
        "hasClaudeMdExternalIncludesApproved": True}
paths = {os.path.abspath(demo), os.path.realpath(demo), demo}   # logical, physical, raw
d = {
    "hasCompletedOnboarding": True,
    "theme": "dark",
    "cachedChromeExtensionInstalled": False,   # <- suppresses the Chrome dialog
    "claudeInChromeDefaultEnabled": False,
    "bypassPermissionsModeAccepted": True,
    "projects": {p: dict(proj) for p in paths},
}
json.dump(d, open(out, "w"), indent=2)
print("seeded", out, "for", sorted(paths))
PY

# --- isolated user settings: pin model (avoids the unavailable-model banner) +
#     pre-accept bypass mode (the tape launches with --dangerously-skip-permissions)
python3 - "$DEMO/.cfg/settings.json" "$MODEL" <<'PY'
import json, sys
json.dump({"model": sys.argv[2], "skipDangerousModePermissionPrompt": True},
          open(sys.argv[1], "w"), indent=2)
PY

# --- project hooks: reuse the repo's timelog.py (timeline) + the on-screen sentinel.
#     Both fire on Stop; timelog logs JSONL, the sentinel prints VHS_TURN_DONE_N.
cat > "$DEMO/.claude/settings.json" <<JSON
{
  "_comment": "Live Claude Code recording: timelog.py logs the event timeline; vhs_stop_sentinel.sh prints the on-screen turn-done marker VHS waits on.",
  "hooks": {
    "SessionStart":     [ { "matcher": "*", "hooks": [ { "type": "command", "command": "python3 \"$SR/timelog.py\"" } ] } ],
    "UserPromptSubmit": [ { "matcher": "*", "hooks": [ { "type": "command", "command": "python3 \"$SR/timelog.py\"" } ] } ],
    "PreToolUse":       [ { "matcher": "*", "hooks": [ { "type": "command", "command": "python3 \"$SR/timelog.py\"" } ] } ],
    "PostToolUse":      [ { "matcher": "*", "hooks": [ { "type": "command", "command": "python3 \"$SR/timelog.py\"" } ] } ],
    "Stop":             [ { "matcher": "*", "hooks": [
                            { "type": "command", "command": "python3 \"$SR/timelog.py\"" },
                            { "type": "command", "command": "\"$HERE/vhs_stop_sentinel.sh\"" } ] } ],
    "SessionEnd":       [ { "matcher": "*", "hooks": [ { "type": "command", "command": "python3 \"$SR/timelog.py\"" } ] } ]
  }
}
JSON

echo "sandbox ready: $DEMO"
echo "  CLAUDE_CONFIG_DIR=$DEMO/.cfg   model=$MODEL"
echo "  launch (in tape): claude --dangerously-skip-permissions"
