# live/ — film a real Claude Code session with VHS (Roadmap path #4)

The parent `session-recorder/` does **post-hoc** narration: you run a session,
the hooks log a timeline, `gen_voiceover.py` narrates it afterward. This folder
adds the **live** half from the README Roadmap: actually *filming* the `claude`
TUI with VHS, driving prompts and waiting on a turn-done **sentinel** so the
recording knows exactly when each response finished — no guessed `Sleep`.

It reuses the parent's `timelog.py` (timeline) and `gen_voiceover.py` (edge-tts
zh-TW narration). The only new pieces are the **clean-recording recipe** and the
**on-screen sentinel** — the two things that make a real `claude` run filmable.

## Files
| File | Role |
| --- | --- |
| `claude_sandbox.sh` | Stage an **isolated** Claude Code project: own `CLAUDE_CONFIG_DIR` (focus off, no dialogs, pinned model, credentials copied) + project `.claude/settings.json` wiring `timelog.py` **and** the sentinel. |
| `vhs_stop_sentinel.sh` | Stop hook that prints the on-screen `VHS_TURN_DONE_N` marker VHS waits on (gated on `$VHS_DEMO`). Complements `timelog.py`. |
| `gen_session_tape.py` | Prompts → a VHS tape that launches `claude` in the sandbox, types word-by-word, and `Wait`s on each turn's sentinel. |

## Pipeline
```bash
SR=engine/experimental/session-recorder
DEMO=/tmp/sess

# 1) stage the clean, isolated sandbox (idempotent)
"$SR/live/claude_sandbox.sh" "$DEMO"

# 2) author the session tape from your prompt list (one quoted arg = one turn)
python3 "$SR/live/gen_session_tape.py" --demo "$DEMO" -o "$DEMO/session.tape" \
  "write a Python function fizzbuzz(n) that prints FizzBuzz from 1 to n" \
  "now add a docstring and a simple test"

# 3) film the real TUI  -> terminal.mp4  (+ session-timeline.jsonl from the hooks)
cd "$DEMO" && vhs session.tape

# 4) narrate from the hook timecodes (reuses the parent tool; edge-tts zh-TW)
python3 "$SR/gen_voiceover.py" --audio    # -> session-voiceover.{srt,mp3}
```
Then pair `terminal.mp4` with the timecode-placed `session-voiceover.mp3`/`.srt`
(or feed both into overlay "session mode" once that lands). To sanity-check a
render, extract a frame near the end and confirm the response **and**
`Stop says: VHS_TURN_DONE_N` are both visible.

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
