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

## Files (v6)
| File | Role |
| --- | --- |
| `claude_sandbox.sh` | Stage an **isolated** Claude Code project: own `CLAUDE_CONFIG_DIR` (focus off, no dialogs, pinned model, credentials copied) + project hooks wiring `timelog.py` **and** the sentinel. |
| `vhs_stop_sentinel.sh` | Stop hook printing the on-screen `VHS_TURN_DONE_N` marker VHS waits on (gated on `$VHS_DEMO`). |
| `script.example.json` | The narration script: a `launch` block (the opening CLI lesson), per-turn `{prompt, intro, think, outro}`, and a `close`. |
| `run_v6.sh` | **The driver.** `run_v6.sh <demo> <script.json>` runs the whole pipeline below, launching `claude` exactly once (in the vhs step). |
| `ledger.py` | The single source of truth (`{beats, meta}`) + helpers (`beat_id`, `beat_start/end`, `serialization_violations`, `output_timeline`, `BREATH`). Every stage reads it; nobody re-derives a time it already holds. |
| `gen_capture_tape.py` | `script.json` → a **prompts-only** minimal VHS tape (no voice) + `capture.json`. |
| `detect_anchors.py` | Reused v5 `signals()` + peak-based `detect_turns()`: boot, per-turn `typing_start/submit/done`, soft-gap ranges, tool-event times — all in **raw-video time**. |
| `author.py` | Phase 1: synth + measure voice, compute each beat's soft length, apply tiers, fill the ledger's soft fields + `drop` flags → every beat's final start/end is KNOWN. |
| `splice.py` | Phase 2: ffmpeg freeze-frame re-time the soft segments of `terminal_raw.mp4` → `terminal.mp4`, and **reconcile** the ledger to the realized video (see below). |
| `overlay.py` | Phase 2: mux the voice clips at the ledger's computed onsets over `terminal.mp4` → `session.mp4` + `.srt`. |
| `panel.py` | Phase 2: build the explainshell-style right panel from the **same** ledger → `session_panel.mp4`. |
| `lint.py` | Phase 3: deterministic gate — the serialization invariant + internal relations on the finalized ledger (`--filmstrip` extracts a labelled eyeball strip). Failures are authoring errors, not detection noise. |

## Pipeline (claude runs **once**)
```bash
SR=engine/experimental/session-recorder
"$SR/live/run_v6.sh" /tmp/sess "$SR/live/script.example.json"
```
The driver runs five phases; `claude` launches **only** in the vhs step:

- **Phase 0 — capture.** Stage the sandbox (idempotent), generate a prompts-only
  minimal tape (`gen_capture_tape.py`), then `vhs session.tape` films the real TUI
  **once** → `terminal_raw.mp4` + `session-timeline.jsonl`. The driver exports `SR`
  and `HERE` (the claude-spawned hooks reference `$SR/timelog.py` and
  `$HERE/vhs_stop_sentinel.sh`) and scrubs the inherited prompt env (`PS1/PROMPT`,
  `_P9K_*`) so VHS's bash doesn't dump the p10k prompt full-screen.
- **Phase 1 — author** (`author.py`, runs detection in-process — no relaunch):
  synth + measure each voice clip, compute each beat's required soft length, apply
  the tiers, write the ledger's soft fields + `drop` flags. Every beat's final
  start/end is now known.
- **Phase 2 — splice/overlay/panel.** `splice.py` freeze-frame re-times the soft
  segments → `terminal.mp4` and **reconciles** the ledger to the realized video;
  `overlay.py` muxes the voice → `session.mp4` + `.srt`; `panel.py` builds the
  right panel → `session_panel.mp4`. All three read the **same** reconciled ledger.
- **Phase 3 — lint** (`lint.py --filmstrip`): the deterministic gate.

### The ledger (`ledger.json`) — single source of truth
`{"beats": [...], "meta": {...}}`. A **beat** is the atomic unit
(`narration-start / pane-switch → CLI input → execution → result`):

| field | meaning |
| --- | --- |
| `id` | `sha1(kind\|turn_idx\|payload)[:6]` — stable across re-authoring (a beat's identity survives editing its siblings). |
| `kind` | `launch_flag` \| `intro` \| `think` \| `outro` \| `close`. |
| `turn_idx` | which turn the beat belongs to. |
| `tier` | `1` must-keep \| `2`/`3` droppable (see table). |
| `mode` | `lead` (voice fully precedes the visual) \| `ride` (voice rides the hard visual `[visual.start, visual.end]`). |
| `voice` | `{clip, start, end}` — synthesized clip + its placed window. |
| `visual` | `{start, end}` — terminal action window (raw video time). |
| `panel` | `{switch_at}` — pane content swap (= `voice.start`). A switch at literal `0.0` is panel init, not beat activity. |
| `raw` | the beat's raw-video segment(s) before re-timing. |
| `drop` | set true by author/lint when a Tier-2/3 beat can't fit. |

`meta.segments` is the ordered cut list — each `{raw, out, out_dur}` (raw bound,
output window, output duration); hard/boot segments copy verbatim, soft segments
become a freeze held for `out_dur`. `meta.vtot_out` is the total output duration
of `terminal.mp4`.

### Priority tiers (what may be dropped)
| Tier | beats | guaranteed by | when too short |
| --- | --- | --- | --- |
| **1 must-keep** | the lead spine — `intro`, each `launch_flag`, `outro`/`close` | soft slot → freeze-frame **stretched** (host-frozen) to fit the voice | impossible → **never dropped** |
| **2 droppable** | `think` (rides the hard `[submit,done]` gap) | trimmed to fit the measured gap | trim at clause boundary; if the first clause still overruns → **drop** |

The spine is "the explanation before each command" — a *structural* guarantee in
v6 (stretch the static frame), not a hope.

### The one invariant
```
beat[i].end + BREATH ≤ beat[i+1].start
where beat.end = max(voice.end, visual.end, panel activity end)
```
Every channel of a beat quiesces (with a `BREATH = 0.5s` of silence) before the
next beat starts. Cross-beat overlap is forbidden; cross-channel overlap is
contained inside a beat. This single rule subsumes v5's separate
min-gap / no-overlap / outro-vs-next-intro checks (`serialization_violations`).

### splice RECONCILES the ledger
Freeze-frame re-timing produces slightly different realized durations than the
plan. `splice.py` measures the realized `terminal.mp4` and rewrites the ledger's
segment `out`/`out_dur`/`vtot_out` (and the dependent beat times) so that **every
downstream stage reads numbers that match the frames** — `overlay.py`'s voice mux,
`session.srt`, and `panel.py`'s keyframes are all driven off the same reconciled
ledger. No re-record.

### v5 retired
The v5 files (`gen_session_tape.py`, `session_overlay.py`, `session_panel.py`,
`verify_session.py`, `validate_sync.py`) have been **removed** — v6 passed the
end-to-end validation (lint PASS, `claude` launched once, left-terminal ==
right-panel == narration confirmed on the file-writing + text-Q&A + mixed
scenario in `script.mixed.json`). v6's `detect_anchors.py` carries a verbatim copy
of v5's `signals()`/`detect_turns()`, so nothing of the detection was lost.

## How detection survives response-heavy multi-turn sessions
Naively thresholding the input band breaks when a session has several file-writing
turns: response output lingers in the band and a turn's typing merges with the
previous turn's response, so a turn gets missed. The fix (stress-tested on a
3-turn file-writing session): a SUBMIT is a sharp PEAK — typing fills the input
box to near its global max, then Enter clears it; lingering response content only
sits MODERATELY bright. So `detect_turns` takes the contiguous runs where the
(tight, auto-located) band exceeds HALF its max — exactly the N submissions —
and derives `typing_start` from the tape's known typing duration. `done` is the
last full-frame content jump before the next submit (absorbs long think gaps).
Validated across text-Q&A, single-tool, and 3-turn file-writing recordings. This
logic lives verbatim in `detect_anchors.py` now; run `lint.py --demo <demo>`
(the deterministic gate) on anything new.

## The opening is a CLI lesson
The `launch` block treats starting `claude` like the repo's rsync/jq lessons:
the command is built **flag-by-flag**, and **the voice leads — each flag is
narrated FIRST, then the token appears** (the tape runs `Sleep(say) ->
Type(token) -> Sleep(breath)`). Since typing is instant, a token must not show
until it's been explained; never type-then-narrate. This is the core principle
in `docs/plans/2026-06-27-claude-session-voiceover-sync-design.md` and applies to
any instant output (command/flag/one-shot token), not just `claude`. What's
narrated is exactly what's typed and run (`base` + each flag's `arg`). Example:
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
