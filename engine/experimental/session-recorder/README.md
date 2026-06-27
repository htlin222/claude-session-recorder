# session-recorder — timecode-matched voiceover for a Claude Code session

Record a real Claude Code session via **hooks**, then post-hoc generate a
narration where each line is timed to the moment its event happened — so playing
the narration explains the session as it unfolds.

## How it works
1. `.claude/settings.json` wires `timelog.py` to the high-signal hook events
   (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Notification,
   SubagentStart/Stop, Stop, SessionEnd). Claude Code has ~31 hook events; these
   are the ones worth narrating.
2. On each event, `timelog.py` captures the wall-clock time (Claude Code provides
   no timestamp itself) + the event name + a concise detail (tool + command/file,
   prompt snippet…) and appends one JSON line to `session-timeline.jsonl`.
3. `gen_voiceover.py` reads that log, computes each event's time RELATIVE to the
   first, and writes a voiceover line per event at that timecode.

## Use it
```bash
# 1) start fresh (one timeline per recording)
rm -f engine/experimental/session-recorder/session-timeline.jsonl
# 2) run a normal Claude Code session in this repo — the hooks log automatically
# 3) generate the timecode-matched voiceover
python3 engine/experimental/session-recorder/gen_voiceover.py            # -> session-voiceover.srt
python3 engine/experimental/session-recorder/gen_voiceover.py --audio    # + session-voiceover.mp3 (edge-tts, each line placed at its timecode)
#    --all narrates every logged event (default narrates a curated subset)
```

`session-voiceover.srt` is the script (timecode → line); `session-voiceover.mp3`
is the same lines synthesized and placed at their timecodes on one track. Pair the
mp3/srt with a screen recording of the session for a fully explained replay.

## Live filming (VHS) — `live/`
This folder narrates a session you ran yourself (post-hoc). To instead **film**
a real `claude` TUI on a script — launch it, drive prompts, wait on a turn-done
sentinel, record `terminal.mp4` — use **`live/`**, which reuses `timelog.py` and
`gen_voiceover.py` and adds the clean-recording sandbox + on-screen sentinel.
Filming a real session is impossible without that sandbox (focus mode hides the
sentinel, dialogs block startup); `live/README.md` documents every trap.

## Notes
- Non-blocking & safe: `timelog.py` always exits 0; remove the `hooks` block from
  `.claude/settings.json` to stop recording.
- `session-timeline.jsonl`, `session-voiceover.*` and `_seg/` are gitignored scratch.
- No timestamp is in the hook payload by design — we capture our own (epoch ms).
