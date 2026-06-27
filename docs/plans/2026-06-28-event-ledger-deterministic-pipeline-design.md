# Event-ledger deterministic pipeline (sync-model v6)

Date: 2026-06-28
Supersedes the placement core of `2026-06-27-claude-session-voiceover-sync-design.md`
(the hard-axis/soft-slot insight and voice-leads-typing principle carry over; the
*mechanism* changes from "size tape Sleeps to voice, then detect" to "record once,
then edit soft segments to fit voice").

## Why v6

v5 (`session_overlay.py`) places narration by **detecting anchors from the final
recording** and sizing the tape's soft Sleeps to the voice up front. Two problems
remain:

1. **The timeline you design against is not the one that airs.** claude's think
   gap is non-deterministic; a re-record drifts (38s one run, 30s the next), so a
   think clip sized to one run overruns another. v5 papers over this with
   fit-or-drop, but the *design target moves*.
2. **Two stages re-derive timing independently.** `session_overlay.py` and
   `session_panel.py` each detect/compute per-turn windows from the video +
   timeline. When they disagree by a frame, left-terminal and right-panel desync.
   This is the recurring "畫音亂套" bug class.

## The v6 idea: record once, then edit, never re-run claude

claude runs **exactly once**, in a *capture* pass with minimal pauses. That run's
**hard segments** (typing → submit → done, the think gap, tool execution) are the
ground-truth axis and are kept **verbatim**. The **soft segments** (the static
frames where nothing happens — before a prompt is typed, after a response settles)
are **re-timed by ffmpeg freeze-frame splice** to whatever the authored voice
needs. No second claude run ⇒ no run-to-run variance, no drift, deterministic lint.

Soft segments are static, so stretching/trimming them is invisible. Hard segments
cannot be stretched naturally (a frozen "thinking" spinner looks fake), so voice
that rides a hard segment is **fit-or-dropped** to the measured gap.

## The beat model

The atomic unit is a **beat**: `narration-start / pane-switch → CLI input →
execution → result`. A beat bundles three channels and has one of two modes:

```jsonc
{
  "id": "b7f3a1",                       // sha1(kind + turn_idx + payload)[:6] — stable across re-authoring
  "kind": "launch_flag|intro|think|outro|close",
  "tier": 1,                            // 1 must-keep, 2/3 droppable (see below)
  "mode": "lead" | "ride",
  "voice":  { "clip": "_voice/intro_1.mp3", "start": 12.40, "end": 15.10 },
  "visual": { "start": 15.40, "end": 18.90 },   // terminal action window (raw video time)
  "panel":  { "switch_at": 12.40 },             // pane content swap = voice.start
  "drop":   false                       // set by author phase when tier 2/3 can't fit
}
```

- **lead beat** (launch flag, intro, outro): voice **fully precedes** the visual
  (`voice.end ≤ visual.start`). Soft slot ⇒ length is *chosen*; realised by a
  freeze-frame hold of `voice.dur + gaps` before the visual.
- **ride beat** (think): voice **rides** the hard visual (`voice ⊆ [visual.start,
  visual.end]`). Length is *measured*; voice is trimmed/dropped to fit.

### Serialization invariant (the one rule)

```
beat[i].end + BREATH ≤ beat[i+1].start
where beat.end = max(voice.end, visual.end, panel activity end)
```

Every channel of a beat quiesces before the next beat starts. Cross-beat overlap
is **forbidden**; cross-channel overlap is **contained inside a beat** (voice leads
typing within the same beat; panel switches with voice within the same beat). This
one invariant subsumes v5's separate min-gap / no-overlap / outro-vs-next-intro
checks.

### Priority tiers (what may be dropped)

| Tier | beats | guaranteed by | when too short |
| --- | --- | --- | --- |
| **1 must-keep** | pre-command explanation: `intro`, each `launch_flag` | soft slot → freeze-frame stretched to fit voice | impossible (just stretch) → **never dropped** |
| **2 droppable** | `think` (rides hard gap) | fit into measured gap | trim at clause boundary; if first clause still overruns → **drop** |
| **3 droppable** | `outro` / `close` | soft slot, can stretch or drop | if it would crowd the next Tier-1 → **drop** |

The spine is "the explanation before each command". It is a *structural*
guarantee in v6 (stretch the static frame), not a hope.

## Pipeline (claude runs once)

```
Phase 0  CAPTURE   prompts-only minimal tape → vhs → terminal_raw.mp4 + timeline
                   detect hard anchors (boot, per-turn typing_start/submit/done,
                   tool events) → ledger.json HARD fields, FINAL.
Phase 1  AUTHOR    write voice + pane notes per beat (script.json) → synth voice,
                   measure each clip. Compute each beat's required soft length;
                   apply tiers (T1 stretch, T2/T3 fit-or-drop). Fill ledger SOFT
                   fields + drop flags → every beat's final start/end is KNOWN.
Phase 2  SPLICE    ffmpeg freeze-frame re-time the soft segments of terminal_raw
                   → terminal.mp4 (final timeline, no re-record). Mux voice at the
                   computed onsets → session.mp4 + .srt. Build panel from the SAME
                   ledger → session_panel.mp4.
Phase 3  LINT      serialization invariant + internal relations on the finalized
                   ledger → deterministic pass (failures are authoring errors,
                   not detection noise).
```

### Phase 0 anchors → ledger hard fields

Reuses v5's `signals()` + `detect_turns()` (peak-based; survives multi-turn
file-writing). Per turn we record, in **raw-video time**:
- `typing_start`, `submit`, `done` (hard segment bounds),
- the surrounding **soft gap ranges** (raw frame intervals that are static and
  therefore stretchable): `[prev_done … typing_start]` and `[done … next_typing]`.
- launch boot window; tool-event raw times (from the timeline, mapped into
  `[submit, done]` by wall-clock fraction — unchanged from v5's panel logic, but
  computed **once** here and stored).

### Phase 2 splice mechanics

`terminal_raw.mp4` is cut at every soft/hard boundary. Hard segments are copied
verbatim. Each soft segment is replaced by a **hold** of its boundary frame for
the authored duration (`ffmpeg trim + tpad/loop` on a single frame, or
`select+setpts` freeze). Concatenated → `terminal.mp4`. Because every segment's
output length is known, the ledger's beat start/end are **computed**, not detected
— `session.srt`, the voice mux, and the panel keyframes all read the same numbers.

## File refactor (live/ — refactor, not rewrite)

| now | v6 |
| --- | --- |
| `gen_session_tape.py` (tape + voice-sized Sleeps + plan.json) | **`gen_capture_tape.py`** — minimal tape: type prompts, sentinel waits, fixed tiny pads. No voice sizing. |
| `session_overlay.py` `signals`/`detect_turns` | **`detect_anchors.py`** — run once on raw → ledger HARD fields + soft gap ranges. |
| (new) | **`author.py`** — synth voice from script.json, compute soft lengths, apply tiers → ledger SOFT fields + drops. |
| (new) | **`splice.py`** — freeze-frame re-time raw → terminal.mp4 (v6 core). |
| `session_overlay.py` muxing | **`overlay.py`** — mux voice onto spliced video from ledger (no detection). |
| `session_panel.py` (re-derives windows) | **`panel.py`** — read ledger only (kills the desync bug class). |
| `verify_session.py` + `validate_sync.py` | **`lint.py`** — serialization + internal relations on finalized ledger; keep the filmstrip eyeball. |
| (new) | **`ledger.json`** — single source of truth, schema above. |

## Migration & validation

v5 files stay until v6 passes an end-to-end validation recording (the same 3
stress scenarios: 3-turn file-writing, 2-turn text Q&A, mixed). Done when:
- `lint.py` passes the serialization invariant + every Tier-1 present,
- the filmstrip confirms left-terminal == right-panel == narrated moment,
- claude was launched **once** (capture only).

## Open question parked for implementation

Freezing a frame mid-soft-segment must land on a **truly static** frame (cursor
blink can flicker the input line). Pick the freeze source frame as the soft
segment's *median* frame, or the frame with minimal delta to its neighbours.
