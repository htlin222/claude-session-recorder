# live/ — film a real Claude Code session with VHS (Roadmap path #4)

The parent `session-recorder/` does **post-hoc** narration placed at raw event
times — so the voice always *trails* the typing (sync-model v1's failure). This
folder *films* the `claude` TUI with VHS and places a **voice-leads-typing**
narration: you hear what each prompt will do BEFORE it's typed. Full rationale:
`docs/plans/2026-06-27-claude-session-voiceover-sync-design.md`.

Key idea — **hard axis vs soft slots**. claude's think gap (Enter→sentinel) is
non-controllable; the pre-prompt pause, typing, and post-output hold are ours. So
the intro voice lives in the pre-prompt slot (leads typing, deterministic), the
outro in the post-output hold, and only the *think* voice must fit the real gap
(loop-until-align). Anchors are read from the video's own pixels (the input line
lights up while typing, clears on submit) — not tape arithmetic, which drifts.

## Files
| File | Role |
| --- | --- |
| `claude_sandbox.sh` | Stage an **isolated** Claude Code project: own `CLAUDE_CONFIG_DIR` (focus off, no dialogs, pinned model, credentials copied) + project hooks wiring `timelog.py` **and** the sentinel. |
| `vhs_stop_sentinel.sh` | Stop hook printing the on-screen `VHS_TURN_DONE_N` marker VHS waits on (gated on `$VHS_DEMO`). |
| `script.example.json` | The narration script: a `launch` block (the opening CLI lesson), per-turn `{prompt, intro, think, outro}`, and a `close`. |
| `gen_session_tape.py` | `script.json` → a VHS tape with deterministic intro/outro voice slots (sized to the synthesized clips), plus `plan.json` + `_voice/*.mp3`. |
| `session_overlay.py` | Detects the real per-turn typing/submit frames, places each clip (intro leads typing, think rides the gap, outro/open/close in their slots), muxes the narration over `terminal.mp4` → `session.mp4` + `.srt`. |
| `verify_session.py` | Gate: voice-leads-typing, think fits the gap, no overlap. Exit 0 PASS / 1 fixable / 2 structural. |

## Pipeline
```bash
SR=engine/experimental/session-recorder
DEMO=/tmp/sess
rm -f "$SR/session-timeline.jsonl"          # one recording per timeline

# 1) clean isolated sandbox (idempotent)
"$SR/live/claude_sandbox.sh" "$DEMO"

# 2) author tape + voice slots + plan.json from the narration script
python3 "$SR/live/gen_session_tape.py" --demo "$DEMO" \
        --script "$SR/live/script.example.json" -o "$DEMO/session.tape"

# 3) film the real TUI -> terminal.mp4 (+ session-timeline.jsonl from the hooks)
cd "$DEMO" && vhs session.tape

# 4) place the narration (needs numpy -> repo venv) -> session.mp4 + .srt
.venv/bin/python "$SR/live/session_overlay.py" --demo "$DEMO"

# 5) gate the sync (loop until it passes)
python3 "$SR/live/verify_session.py" --demo "$DEMO"
```
If step 5 reports a turn whose **think voice overruns** its real gap (claude
answered too fast), shorten that turn's `think` line in the script and re-record
(the outer loop). voice-leads-typing and overlaps are structural and should never
fail; if they do it's a placement bug.

## The opening is a CLI lesson
The `launch` block treats starting `claude` like the repo's rsync/jq lessons:
the command is typed **token-by-token**, each flag **held on screen while its own
narration plays** (sync-model v5 hero-command pacing), and what's narrated is
exactly what's typed and run (`base` + each flag's `arg`). Example:
```json
"launch": {
  "base": "claude",
  "flags": [
    {"arg": "--model opus", "say": "加上 model opus 指定模型，"},
    {"arg": "--permission-mode bypassPermissions", "say": "再用 permission mode bypass，讓示範自動執行、不問權限。"}
  ],
  "intro": "我們用 claude 啟動，", "outro": "稍候就進入互動畫面。"
}
```
The open clip is placed at the deterministic `prelude` (the launch is the FIRST
thing in the tape, so no detection needed); it leads the typing and plays through
boot into the entry screen. Keep `bypassPermissions`/`--dangerously-skip-permissions`
in the launch — the recording needs it (the sandbox pre-accepts the mode).

## Why the sandbox is non-negotiable (hard-won)
Filming `claude` with your **normal** config fails in four ways — the sandbox
fixes all four:

1. **Focus mode hides the sentinel.** The `VHS_TURN_DONE_N` marker is a hook
   `systemMessage`, and **focus mode hides system/hook messages** → the marker
   never renders → every `Wait+Screen /sentinel/` times out. This was the first
   and most confusing failure. A fresh `CLAUDE_CONFIG_DIR` starts with focus
   **off**, so the marker shows. **Never record live without the sandbox.**
2. **Chrome-extension dialog** ("Claude in Chrome extension detected") blocks
   startup. There is **no** documented `settings.json` key to disable it — the
   sandbox seeds `cachedChromeExtensionInstalled:false` in the isolated
   `.claude.json` so it's never detected.
3. **Unavailable-model banner.** A fresh config defaults to a model that may be
   unavailable, painting a banner over the UI → sandbox pins `model:opus`.
4. **`acceptEdits` isn't enough.** A turn that runs the test it just wrote hits a
   **Bash** permission prompt and hangs. The tape launches with
   `--dangerously-skip-permissions` (safe in a throwaway dir); the sandbox
   pre-accepts the bypass-mode warning (`skipDangerousModePermissionPrompt`).

Plus: isolation drops MCP-auth warnings and your global `CLAUDE.md` from the
frame, leaving a Catppuccin-clean capture.

## Notes
- Auth on this machine is a **file** (`~/.claude/.credentials.json`), not the
  keychain, so the sandbox copies it in to skip login. Override the source with
  `CLAUDE_CONFIG_DIR_GLOBAL`, the model with `SANDBOX_MODEL`.
- `<demo>/.cfg/` holds real credentials → keep demo dirs in `/tmp` (gitignored,
  ephemeral); never commit a sandbox.
- The sentinel counter lives at `$TMPDIR/vhs-session-<sid>.count`; `cleanup` it
  between takes so numbering restarts at `_1`.
