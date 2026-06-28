# Event-ledger deterministic pipeline (v6) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the live session-recorder from v5 (size soft Sleeps to voice, then detect anchors from the final cut) to v6 (capture once with minimal pauses, then ffmpeg freeze-frame splice the soft segments to fit the authored voice), with a single `ledger.json` as the source of truth that every downstream stage reads — killing run-to-run drift and the panel/terminal desync bug class.

**Architecture:** `claude` runs **once** (Phase 0 CAPTURE) producing `terminal_raw.mp4` + a timeline. Hard segments (typing→submit→done, the think gap) are kept verbatim; soft segments (static frames where nothing happens) are re-timed by freeze-frame splice to whatever the authored voice needs. The pipeline is four phases — CAPTURE → AUTHOR → SPLICE → LINT — each reading/writing one `ledger.json`. All timing math lives in pure, unit-tested functions; ffmpeg/edge-tts/vhs are thin I/O wrappers exercised by the end-to-end stress recordings.

**Tech Stack:** Python 3 (repo `.venv`), numpy, Pillow, ffmpeg/ffprobe, edge-tts, vhs, ImageMagick (`magick`). Tests: pytest. Full design rationale: `docs/plans/2026-06-28-event-ledger-deterministic-pipeline-design.md`.

---

## Conventions for every task

- **Work dir:** all v6 files live in `engine/experimental/session-recorder/live/` **alongside** the v5 files (the design says v5 stays until v6 passes end-to-end validation — do **not** delete v5 yet). Tests live in `engine/experimental/session-recorder/live/tests/`.
- **Run tests with the repo venv:** `cd /Users/htlin/vhs-demo && .venv/bin/python -m pytest engine/experimental/session-recorder/live/tests/ -v`
- **Absolute paths** in code (the codebase rule). Reuse v5 constants where noted.
- **Time bases:** `detect_anchors` emits **raw-video** time (`terminal_raw.mp4`). `author` computes the **output-video** timeline (after splice). The ledger stores output time in `voice`/`visual`/`panel`; raw ranges live under a `raw` block per beat for splice to consume.
- **One ledger, one schema** (`ledger.py`). Never re-derive a time that the ledger already holds.
- **Commit after every task** with the message shown in that task's final step.

---

## Task 0: Test harness + dependency

**Files:**
- Create: `engine/experimental/session-recorder/live/tests/__init__.py` (empty)
- Create: `engine/experimental/session-recorder/live/tests/conftest.py`
- Modify: repo `.venv` (install pytest)

**Step 1: Install pytest into the repo venv**

Run: `cd /Users/htlin/vhs-demo && .venv/bin/python -m pip install pytest`
Expected: `Successfully installed pytest-...`

**Step 2: Create the test package + a shared path fixture**

`tests/__init__.py`: empty file.

`tests/conftest.py`:
```python
import os
import sys

# make the live/ modules importable as top-level (ledger, author, splice, …)
LIVE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if LIVE not in sys.path:
    sys.path.insert(0, LIVE)
```

**Step 3: Smoke-test the harness**

Create `tests/test_smoke.py`:
```python
def test_harness_runs():
    assert True
```
Run: `cd /Users/htlin/vhs-demo && .venv/bin/python -m pytest engine/experimental/session-recorder/live/tests/test_smoke.py -v`
Expected: `1 passed`.

**Step 4: Commit**
```bash
git add engine/experimental/session-recorder/live/tests/
git commit -m "test(live): pytest harness for v6 deterministic pipeline"
```

---

## Task 1: `ledger.py` — schema, beat id, beat-end

The ledger is the single source of truth. This task builds its pure core. Schema (from the design doc) per beat:

```jsonc
{
  "id": "b7f3a1",                  // sha1(kind + turn_idx + payload)[:6]
  "kind": "launch_flag|intro|think|outro|close",
  "turn_idx": 0,                   // -1 for launch/close beats
  "tier": 1,                       // 1 must-keep, 2/3 droppable
  "mode": "lead" | "ride",
  "voice":  {"clip": "_voice/intro_1.mp3", "start": 12.40, "end": 15.10},  // OUTPUT time
  "visual": {"start": 15.40, "end": 18.90},   // OUTPUT time (terminal action window)
  "panel":  {"switch_at": 12.40},             // OUTPUT time (= voice.start for leads)
  "raw":    {"soft": [a, b], "hard": [c, d]}, // RAW terminal_raw.mp4 ranges (splice input)
  "drop":   false
}
```

**Files:**
- Create: `engine/experimental/session-recorder/live/ledger.py`
- Test: `engine/experimental/session-recorder/live/tests/test_ledger.py`

**Step 1: Write the failing test**
```python
import ledger

def test_beat_id_is_stable_6_hex():
    a = ledger.beat_id("intro", 0, "先請 Claude 寫 FizzBuzz")
    b = ledger.beat_id("intro", 0, "先請 Claude 寫 FizzBuzz")
    assert a == b and len(a) == 6
    assert all(c in "0123456789abcdef" for c in a)

def test_beat_id_changes_with_payload():
    assert ledger.beat_id("think", 1, "x") != ledger.beat_id("think", 1, "y")
    assert ledger.beat_id("intro", 0, "x") != ledger.beat_id("intro", 1, "x")

def test_beat_end_is_max_of_active_channels():
    beat = {"voice": {"start": 1.0, "end": 3.0},
            "visual": {"start": 3.2, "end": 5.0},
            "panel": {"switch_at": 1.0}}
    assert ledger.beat_end(beat) == 5.0

def test_beat_end_ignores_dropped_voice():
    beat = {"voice": None,
            "visual": {"start": 2.0, "end": 4.0},
            "panel": {"switch_at": 2.0}}
    assert ledger.beat_end(beat) == 4.0
```
Run: `... -m pytest .../tests/test_ledger.py -v` → Expected: FAIL (`No module named 'ledger'`).

**Step 2: Implement `ledger.py` core**
```python
#!/usr/bin/env python3
"""ledger.py — the v6 single source of truth.

A ledger is {"beats": [...], "meta": {...}}. Every downstream stage (splice,
overlay, panel, lint) reads it; nobody re-derives a time it already holds. See
docs/plans/2026-06-28-event-ledger-deterministic-pipeline-design.md.
"""
import hashlib
import json

BREATH = 0.5     # min silence between consecutive beats (== v5 MIN_GAP)


def beat_id(kind, turn_idx, payload):
    """sha1(kind|turn_idx|payload)[:6] — stable across re-authoring so a beat's
    identity survives editing its sibling beats."""
    h = hashlib.sha1(f"{kind}|{turn_idx}|{payload}".encode("utf-8"))
    return h.hexdigest()[:6]


def beat_end(beat):
    """The moment every channel of this beat has quiesced (design's
    `beat.end = max(voice.end, visual.end, panel activity end)`). A channel that
    is None/absent contributes nothing."""
    ends = []
    v = beat.get("voice")
    if v:
        ends.append(v["end"])
    vis = beat.get("visual")
    if vis:
        ends.append(vis["end"])
    p = beat.get("panel")
    if p and "switch_at" in p:
        ends.append(p["switch_at"])
    return max(ends) if ends else 0.0


def beat_start(beat):
    """The earliest active moment of a beat — min over present channel starts."""
    starts = []
    v = beat.get("voice")
    if v:
        starts.append(v["start"])
    vis = beat.get("visual")
    if vis:
        starts.append(vis["start"])
    p = beat.get("panel")
    if p and "switch_at" in p:
        starts.append(p["switch_at"])
    return min(starts) if starts else 0.0


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, led):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(led, f, ensure_ascii=False, indent=2)
```
Run the test → Expected: PASS (4 passed).

**Step 3: Commit**
```bash
git add engine/experimental/session-recorder/live/ledger.py engine/experimental/session-recorder/live/tests/test_ledger.py
git commit -m "feat(live): ledger schema core — stable beat ids + beat-end"
```

---

## Task 2: `ledger.py` — the serialization invariant (the one rule)

Design's single rule: `beat[i].end + BREATH ≤ beat[i+1].start`, where active (non-dropped) beats are ordered by start. This subsumes v5's separate min-gap / no-overlap / outro-vs-next-intro checks.

**Files:**
- Modify: `engine/experimental/session-recorder/live/ledger.py`
- Test: `engine/experimental/session-recorder/live/tests/test_invariant.py`

**Step 1: Write the failing test**
```python
import ledger

def _beat(start, end, drop=False):
    return {"voice": {"start": start, "end": end},
            "visual": {"start": start, "end": end},
            "panel": {"switch_at": start}, "drop": drop}

def test_clean_sequence_has_no_violations():
    beats = [_beat(0, 2), _beat(2.5, 4), _beat(4.5, 6)]
    assert ledger.serialization_violations(beats) == []

def test_overlap_is_a_violation():
    beats = [_beat(0, 2), _beat(1.5, 3)]   # second starts before first ends
    v = ledger.serialization_violations(beats)
    assert len(v) == 1 and v[0]["gap"] < 0

def test_too_tight_gap_is_a_violation():
    beats = [_beat(0, 2), _beat(2.2, 4)]   # 0.2s < BREATH(0.5)
    assert len(ledger.serialization_violations(beats)) == 1

def test_dropped_beats_are_skipped():
    beats = [_beat(0, 2), _beat(2.1, 3, drop=True), _beat(2.6, 5)]
    assert ledger.serialization_violations(beats) == []
```
Run → Expected: FAIL (`serialization_violations` undefined).

**Step 2: Implement**
```python
def serialization_violations(beats, breath=BREATH):
    """Return one record per adjacent pair that breaks
    `beat[i].end + breath <= beat[i+1].start`. Dropped beats are excluded.
    Active beats are ordered by their start time before checking."""
    active = sorted((b for b in beats if not b.get("drop")), key=beat_start)
    out = []
    for i in range(1, len(active)):
        gap = round(beat_start(active[i]) - beat_end(active[i - 1]), 3)
        if gap < breath - 0.05:
            out.append({"prev": active[i - 1].get("id"),
                        "next": active[i].get("id"), "gap": gap})
    return out
```
Run → Expected: PASS (4 passed).

**Step 3: Commit**
```bash
git add engine/experimental/session-recorder/live/ledger.py engine/experimental/session-recorder/live/tests/test_invariant.py
git commit -m "feat(live): serialization invariant — the one cross-beat rule"
```

---

## Task 3: `ledger.py` — output-timeline builder (raw→output map)

Soft segments are author-chosen lengths; hard segments are fixed from raw. Given the ordered list of raw segments (each `{"kind": "hard"|"soft", "raw": [a,b], "out_dur": d}`) this returns the **output** start/end of each segment by accumulating. Splice realizes it; overlay/panel read it. Pure ⇒ unit-tested.

**Files:**
- Modify: `engine/experimental/session-recorder/live/ledger.py`
- Test: `engine/experimental/session-recorder/live/tests/test_timeline.py`

**Step 1: Write the failing test**
```python
import ledger

def test_output_timeline_accumulates_durations():
    segs = [
        {"kind": "soft", "raw": [0.0, 2.0], "out_dur": 3.0},   # stretched 2->3
        {"kind": "hard", "raw": [2.0, 6.0], "out_dur": 4.0},   # verbatim
        {"kind": "soft", "raw": [6.0, 7.0], "out_dur": 0.5},   # trimmed 1->0.5
    ]
    out = ledger.output_timeline(segs)
    assert out[0]["out"] == [0.0, 3.0]
    assert out[1]["out"] == [3.0, 7.0]
    assert out[2]["out"] == [7.0, 7.5]

def test_hard_segment_out_dur_defaults_to_raw_length():
    segs = [{"kind": "hard", "raw": [1.0, 4.0]}]   # no out_dur -> raw length
    out = ledger.output_timeline(segs)
    assert out[0]["out"] == [0.0, 3.0]
```
Run → Expected: FAIL.

**Step 2: Implement**
```python
def output_timeline(segments):
    """Map ordered raw segments to output time. A hard segment defaults to its
    raw length (copied verbatim); a soft segment uses its chosen out_dur. Returns
    each segment with an added `out: [start, end]` in output time."""
    out, cursor = [], 0.0
    for s in segments:
        if "out_dur" in s and s["out_dur"] is not None:
            d = s["out_dur"]
        else:
            d = s["raw"][1] - s["raw"][0]
        seg = dict(s)
        seg["out"] = [round(cursor, 3), round(cursor + d, 3)]
        out.append(seg)
        cursor += d
    return out
```
Run → Expected: PASS.

**Step 3: Commit**
```bash
git add engine/experimental/session-recorder/live/ledger.py engine/experimental/session-recorder/live/tests/test_timeline.py
git commit -m "feat(live): raw->output timeline builder (splice math, pure)"
```

---

## Task 4: `detect_anchors.py` — Phase 0 anchors → ledger HARD fields

Reuse v5's `signals` / `detect_ready` / `detect_turns` **verbatim** (they survive multi-turn file-writing). New work: turn the detected per-turn `(typing_start, submit, done)` into the ledger's HARD fields **plus the surrounding soft gap ranges** in raw time.

**Files:**
- Create: `engine/experimental/session-recorder/live/detect_anchors.py`
- Test: `engine/experimental/session-recorder/live/tests/test_detect_anchors.py`

**Step 1: Write the failing test (pure mapping only — no ffmpeg)**
```python
import detect_anchors as da

def test_raw_segments_alternate_soft_hard_and_cover_video():
    # boot ends at 2.0; two turns; video total 20.0
    turns = [{"typing_start": 4.0, "submit": 6.0, "done": 9.0},
             {"typing_start": 12.0, "submit": 13.0, "done": 17.0}]
    segs = da.raw_segments(ready=2.0, turns=turns, vtot=20.0)
    kinds = [s["kind"] for s in segs]
    # boot(soft) | type+gap(hard) | settle(soft) | type+gap(hard) | tail(soft)
    assert kinds == ["soft", "hard", "soft", "hard", "soft"]
    # contiguous + covers [0, vtot]
    assert segs[0]["raw"][0] == 0.0 and segs[-1]["raw"][1] == 20.0
    for a, b in zip(segs, segs[1:]):
        assert a["raw"][1] == b["raw"][0]

def test_hard_segment_spans_typing_start_to_done():
    turns = [{"typing_start": 4.0, "submit": 6.0, "done": 9.0}]
    segs = da.raw_segments(ready=2.0, turns=turns, vtot=12.0)
    hard = [s for s in segs if s["kind"] == "hard"][0]
    assert hard["raw"] == [4.0, 9.0]
    assert hard["turn_idx"] == 0
```
Run → Expected: FAIL.

**Step 2: Implement**

Copy `signals`, `detect_ready`, `detect_turns`, `dur`, `FF`, `FPS` from `session_overlay.py` into `detect_anchors.py` **unchanged** (they are the validated detection core). Add:

```python
def raw_segments(ready, turns, vtot):
    """Partition raw-video time into alternating SOFT (static, stretchable) and
    HARD (typing->submit->done, kept verbatim) segments.

      [0 .. ready]                 soft  (boot/settle before the first prompt)
      [typing_start_i .. done_i]   hard  (turn i — the uncontrollable axis)
      [done_i .. typing_start_i+1] soft  (post-response settle)
      [done_last .. vtot]          soft  (tail)
    """
    segs = [{"kind": "soft", "raw": [0.0, ready], "role": "boot"}]
    for i, t in enumerate(turns):
        prev_end = segs[-1]["raw"][1]
        if t["typing_start"] > prev_end:
            segs.append({"kind": "soft", "raw": [prev_end, t["typing_start"]],
                         "role": "pre", "turn_idx": i})
        segs.append({"kind": "hard", "raw": [t["typing_start"], t["done"]],
                     "turn_idx": i, "submit": t["submit"]})
    segs.append({"kind": "soft", "raw": [segs[-1]["raw"][1], vtot],
                 "role": "tail"})
    return segs


def detect(demo, video, plan):
    """I/O entry: run signals/detect on <demo>/<video>, return
    {ready, turns:[{typing_start,submit,done}], vtot, segments}. Writes nothing —
    author.py owns the ledger. Reuses the v5 detection verbatim."""
    import os
    path = os.path.join(demo, video)
    vtot = dur(path)
    full, inp = signals(path)
    ready = detect_ready(full)
    det = detect_turns(full, inp, len(plan["turns"]), plan["turns"],
                       plan.get("pre_enter", 0.4))
    return {"ready": ready, "turns": det, "vtot": round(vtot, 3),
            "segments": raw_segments(ready, det, vtot)}
```
Add an `argparse` `main()` that runs `detect(...)` against `terminal_raw.mp4` + `capture.json` and prints the segments (used for manual Phase-0 inspection).

Run → Expected: PASS (2 passed).

**Step 3: Commit**
```bash
git add engine/experimental/session-recorder/live/detect_anchors.py engine/experimental/session-recorder/live/tests/test_detect_anchors.py
git commit -m "feat(live): detect_anchors — reuse v5 detection, emit raw soft/hard segments"
```

---

## Task 5: `gen_capture_tape.py` — Phase 0 minimal capture tape

A minimal tape: type the launch command + prompts, wait on sentinels, use **fixed tiny pads** (no voice sizing). Emits `capture.json` (the structure detect_anchors needs: n turns, per-turn `type_dur`, prompts, launch token list). Adapt from `gen_session_tape.py` but strip all `synth()` calls and voice-sized Sleeps.

**Files:**
- Create: `engine/experimental/session-recorder/live/gen_capture_tape.py`
- Test: `engine/experimental/session-recorder/live/tests/test_capture_tape.py`

**Step 1: Write the failing test (string/golden assertions on the emitted tape)**
```python
import gen_capture_tape as g

SPEC = {
    "launch": {"base": "claude", "flags": [{"arg": "--model opus"}]},
    "turns": [{"prompt": "write fizzbuzz"}, {"prompt": "add a test"}],
}

def test_tape_has_minimal_fixed_pads_and_no_voice(tmp_path):
    tape, plan = g.render(SPEC, demo=str(tmp_path), width=1200, height=1080,
                          font_size=26, word_delay=220)
    # one sentinel wait per turn, in order
    assert "VHS_TURN_DONE_1" in tape and "VHS_TURN_DONE_2" in tape
    # launch typed token-by-token: base then each flag
    assert 'Type "claude"' in tape and 'Type " --model opus"' in tape
    # NO voice-sized sleeps: pads are the fixed PAD constant only
    assert f"Sleep {g.PAD:.3f}s" in tape
    # capture.json carries type_dur per turn for typing_start derivation
    assert plan["turns"][0]["type_dur"] > 0
    assert plan["turns"][0]["prompt"] == "write fizzbuzz"
    assert len(plan["turns"]) == 2

def test_capture_plan_lists_launch_tokens(tmp_path):
    _tape, plan = g.render(SPEC, demo=str(tmp_path), width=1200, height=1080,
                           font_size=26, word_delay=220)
    assert plan["launch"]["tokens"] == ["claude", "--model opus"]
```
Run → Expected: FAIL.

**Step 2: Implement `gen_capture_tape.py`**

Structure mirrors `gen_session_tape.py:emit` but:
- Module constants: `PAD = 0.4` (fixed tiny soft pad), `PRELUDE = 2.0`, `PRE_ENTER = 0.4`, `VOICE`/`synth` **removed**.
- `render(spec, demo, width, height, font_size, word_delay, startup_to=60, turn_to=120)` returns `(tape_str, plan)` and is pure w.r.t. the filesystem except writing nothing (the `main()` wrapper writes `<demo>/session.tape` + `<demo>/capture.json`). This keeps it unit-testable.
- Launch: type `base`, then each flag with a fixed `Sleep PAD` between tokens (no `say`, no synth). Record `tokens = [base] + [f["arg"] for f in flags]` into `plan["launch"]`.
- Per turn: `Sleep PAD` (pre), type prompt word-by-word at `word_delay`, `Sleep PRE_ENTER`, `Enter`, `Wait+Screen@{turn_to}s /VHS_TURN_DONE_{i}/`, `Sleep PAD` (settle). Record `type_dur = round(len(words) * word_delay / 1000, 3)`, `prompt`, `sentinel`.
- Output target `terminal_raw.mp4` (not `terminal.mp4`).
- Keep the sandbox env block (`VHS_DEMO`, `CLAUDE_CONFIG_DIR`, `VHS_TIMELINE`) and the trailing `Ctrl+C` teardown verbatim from v5.

Run → Expected: PASS (2 passed).

**Step 3: Commit**
```bash
git add engine/experimental/session-recorder/live/gen_capture_tape.py engine/experimental/session-recorder/live/tests/test_capture_tape.py
git commit -m "feat(live): gen_capture_tape — minimal prompts-only tape + capture.json"
```

---

## Task 6: `author.py` — Phase 1 voice + tiers → ledger SOFT fields

The heart of v6's determinism. Given `capture.json`, the detected segments, and `script.json`, synth the voice, measure each clip, compute each soft segment's output length, apply the priority tiers, and emit the finalized ledger with every beat's output start/end **computed** (via `ledger.output_timeline`). Split pure logic (tiers, soft-length, timeline) from I/O (`synth`).

Priority tiers (from the design):

| Tier | beats | rule |
| --- | --- | --- |
| 1 must-keep | `intro`, each `launch_flag` | soft slot stretched to fit voice → **never dropped** |
| 2 droppable | `think` (rides hard gap) | trim at clause boundary; if first clause still overruns → **drop** |
| 3 droppable | `outro` / `close` | soft slot; stretch or, if it would crowd the next Tier-1, **drop** |

**Files:**
- Create: `engine/experimental/session-recorder/live/author.py`
- Test: `engine/experimental/session-recorder/live/tests/test_author.py`

**Step 1: Write the failing tests (pure tier/soft-length logic)**
```python
import author

def test_tier1_soft_length_holds_voice_plus_gaps():
    # a lead beat: soft slot must be >= voice_dur + INTRO_GAP + BREATH
    out = author.soft_len_lead(voice_dur=2.7)
    assert out >= 2.7 + author.INTRO_GAP

def test_tier2_think_kept_when_it_fits_the_measured_gap():
    d = author.fit_ride(voice_dur=2.0, gap=4.0)
    assert d["drop"] is False and d["dur"] <= 4.0

def test_tier2_think_dropped_when_even_trimmed_overruns():
    # measured gap tiny; first-clause synth still longer than the gap
    d = author.fit_ride(voice_dur=5.0, gap=1.0, first_clause_dur=2.0)
    assert d["drop"] is True

def test_tier3_outro_dropped_when_it_would_crowd_next_tier1():
    # only 0.3s of room before the next intro -> cannot fit a breath -> drop
    d = author.fit_soft_droppable(voice_dur=2.0, room=0.3)
    assert d["drop"] is True

def test_tier3_outro_kept_when_room_is_enough():
    d = author.fit_soft_droppable(voice_dur=2.0, room=5.0)
    assert d["drop"] is False and d["dur"] == 2.0
```
Run → Expected: FAIL.

**Step 2: Implement the pure core**
```python
#!/usr/bin/env python3
"""author.py — Phase 1: synth voice, measure, size soft segments, apply tiers,
write the finalized ledger (every beat start/end computed). v6 core math.
"""
import os
import re
import subprocess

from ledger import BREATH, beat_id, output_timeline, save

VOICE = "zh-TW-HsiaoChenNeural"
RATE = "+0%"
INTRO_GAP = 0.3       # silence between a lead voice end and the visual it leads
THINK_GUARD = 0.6     # free gap kept after a ride (think) voice


def synth(text, out_mp3):           # I/O boundary
    subprocess.run(["edge-tts", "--voice", VOICE, "--rate", RATE,
                    "--text", text, "--write-media", out_mp3],
                   check=True, capture_output=True)
    return _dur(out_mp3)


def _dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout or 0)


def soft_len_lead(voice_dur):
    """Tier-1 lead beat: the soft slot must hold the voice plus the lead gap and a
    breath before the next beat — never dropped, always stretched."""
    return round(voice_dur + INTRO_GAP + BREATH, 3)


def fit_ride(voice_dur, gap, first_clause_dur=None):
    """Tier-2 think rides the measured hard gap. Keep if it fits gap-THINK_GUARD;
    else trim (caller does the clause synth); drop only if even the first clause
    overruns."""
    budget = max(0.5, gap - THINK_GUARD)
    if voice_dur <= budget + 0.1:
        return {"drop": False, "dur": round(voice_dur, 3)}
    if first_clause_dur is not None and first_clause_dur > budget + 0.1:
        return {"drop": True, "dur": 0.0}
    return {"drop": False, "dur": round(budget, 3)}   # trimmed to budget


def fit_soft_droppable(voice_dur, room):
    """Tier-3 outro/close: keep at full length if `room` (until the next Tier-1)
    holds it plus a breath; otherwise drop (don't crowd the spine)."""
    if room >= voice_dur + BREATH:
        return {"drop": False, "dur": round(voice_dur, 3)}
    return {"drop": True, "dur": 0.0}
```

Then add the orchestrator `build_ledger(demo, script, anchors)`:
- For each launch flag + intro: `kind`, `tier=1`, `mode="lead"`, synth voice, set the owning soft segment's `out_dur = soft_len_lead(voice_dur)`.
- For each think: `tier=2`, `mode="ride"`; the hard segment's gap = `submit..done`; `fit_ride(...)`; on overrun, do the clause-trim synth (reuse v5 `fit_think` logic — copy it in) before deciding drop.
- For each outro + close: `tier=3`, `mode="lead"` (soft); `fit_soft_droppable(voice_dur, room)` where `room` is until the next Tier-1 beat.
- Build the ordered raw `segments` (from `anchors["segments"]`) with each soft segment's `out_dur` filled, call `ledger.output_timeline(...)`, then place each beat's `voice`/`visual`/`panel` in **output** time from the segment's `out` window. For a lead beat: `voice = [seg.out.start, seg.out.start+voice_dur]`, `visual.start = voice.end + INTRO_GAP`, `panel.switch_at = voice.start`. For a ride beat: `visual = hard seg.out`, `voice.start = visual.start (submit mapped)`, `panel.switch_at = intro voice.start of that turn`.
- Set `beat["id"] = beat_id(kind, turn_idx, text)`, `beat["raw"]` from the segment.
- `save(os.path.join(demo, "ledger.json"), {"beats": beats, "meta": {...}})`.

Run → Expected: PASS (5 passed).

**Step 3: Add a ledger-level integration test**

`tests/test_author_ledger.py`: feed a synthetic `anchors` dict + a tiny `script` with **`synth` monkeypatched** to return fixed durations (no edge-tts in tests), assert the produced ledger:
- passes `ledger.serialization_violations(...) == []`,
- has every Tier-1 beat present (`drop=False`),
- beats are ordered and non-overlapping in output time.
```python
import author, ledger

def test_built_ledger_satisfies_the_invariant(monkeypatch):
    monkeypatch.setattr(author, "synth", lambda text, out: 2.0)   # 2s per clip
    monkeypatch.setattr(author, "_dur", lambda p: 2.0)
    anchors = {"ready": 2.0, "vtot": 30.0,
               "turns": [{"typing_start": 4.0, "submit": 6.0, "done": 12.0}],
               "segments": None}  # author rebuilds segments from turns+ready+vtot
    script = {"launch": {"base": "claude",
                         "flags": [{"arg": "--model opus", "say": "用 opus"}],
                         "intro": "啟動", "outro": "進入畫面"},
              "turns": [{"prompt": "x", "intro": "請它寫", "think": "思考中",
                         "outro": "完成了"}],
              "close": "結束"}
    led = author.build_ledger(demo="/tmp/ignored", script=script, anchors=anchors,
                              write=False)
    assert ledger.serialization_violations(led["beats"]) == []
    t1 = [b for b in led["beats"] if b["tier"] == 1]
    assert t1 and all(not b["drop"] for b in t1)
```
(Implement `build_ledger(..., write=True)` so tests can pass `write=False` to skip disk + synth-to-disk; have it call `detect_anchors.raw_segments` when `anchors["segments"]` is None.)

Run → Expected: PASS.

**Step 4: Commit**
```bash
git add engine/experimental/session-recorder/live/author.py engine/experimental/session-recorder/live/tests/test_author.py engine/experimental/session-recorder/live/tests/test_author_ledger.py
git commit -m "feat(live): author — synth voice, apply tiers, emit finalized ledger"
```

---

## Task 7: `splice.py` — Phase 2 freeze-frame re-time (v6 core)

Cut `terminal_raw.mp4` at every soft/hard boundary; copy hard segments verbatim; replace each soft segment with a **freeze-frame hold** of its chosen `out_dur`. Concatenate → `terminal.mp4`. Two pure pieces (tested) + one ffmpeg exec.

The open question from the design: the freeze source frame must be **truly static** (cursor blink flickers the input line) — pick the soft segment's frame with **minimal delta to its neighbours** (fallback: the median frame).

**Files:**
- Create: `engine/experimental/session-recorder/live/splice.py`
- Test: `engine/experimental/session-recorder/live/tests/test_splice.py`

**Step 1: Write the failing tests (pure)**
```python
import numpy as np
import splice

def test_freeze_source_picks_minimal_delta_frame():
    # frame deltas over a soft range; index 2 is the calmest
    deltas = np.array([5.0, 4.0, 0.1, 3.0])
    assert splice.calmest_frame(deltas) == 2

def test_plan_marks_hard_copy_and_soft_freeze():
    segs = [
        {"kind": "soft", "raw": [0.0, 2.0], "out_dur": 3.0},
        {"kind": "hard", "raw": [2.0, 6.0]},
        {"kind": "soft", "raw": [6.0, 7.0], "out_dur": 0.5},
    ]
    plan = splice.plan(segs)
    assert plan[0]["op"] == "freeze" and abs(plan[0]["out_dur"] - 3.0) < 1e-9
    assert plan[1]["op"] == "copy"
    assert plan[2]["op"] == "freeze" and abs(plan[2]["out_dur"] - 0.5) < 1e-9
```
Run → Expected: FAIL.

**Step 2: Implement**
```python
#!/usr/bin/env python3
"""splice.py — Phase 2 core: freeze-frame re-time the SOFT segments of
terminal_raw.mp4 to their authored lengths; copy HARD segments verbatim;
concat -> terminal.mp4. Output lengths are all known from the ledger, so no
re-detection is ever needed downstream.
"""
import os
import subprocess

import numpy as np

FF = "/opt/homebrew/bin/ffmpeg"
FPS = 12.5


def calmest_frame(deltas):
    """Index of the frame with the least change vs its neighbour — the truly
    static frame to freeze (cursor blink flickers the input line, so never just
    take an endpoint). Ties resolve to the earliest (np.argmin)."""
    return int(np.argmin(deltas))


def plan(segments):
    """Per raw segment: HARD -> copy verbatim; SOFT -> freeze a single static
    frame for out_dur. Returns ops in order for the ffmpeg builder."""
    ops = []
    for s in segments:
        if s["kind"] == "hard":
            ops.append({"op": "copy", "raw": s["raw"]})
        else:
            ops.append({"op": "freeze", "raw": s["raw"],
                        "out_dur": s.get("out_dur",
                                         s["raw"][1] - s["raw"][0])})
    return ops
```

Then the exec wrapper `splice(demo, raw="terminal_raw.mp4", out="terminal.mp4", led=...)`:
- Build `plan(led's segments)`.
- For each `copy`: `ffmpeg -ss a -to b -i raw -c copy seg_k.mp4` (or stream-select; re-encode if copy can't cut on non-keyframes — prefer `-c:v libx264 -an` for frame-accuracy).
- For each `freeze`: pick the source frame time = `raw[0] + calmest_frame(deltas)/FPS` where `deltas` come from a small grayscale probe of that raw range (reuse `signals`-style raw read, per-frame mean abs diff). Extract one frame (`-ss t -frames:v 1`), then hold it for `out_dur` via `-loop 1 -t out_dur` (or `tpad`). Encode to `seg_k.mp4` matching the copy segments' codec/fps/size.
- Concat all `seg_k.mp4` via the concat demuxer → `terminal.mp4`.
- Assert `dur(terminal.mp4) ≈ sum(out_dur)` within 0.2s; print the realized total.

**Step 3: Add a tiny real-ffmpeg integration test (guarded)**

`tests/test_splice_io.py`: skip if `ffmpeg` missing; generate a 3s `testsrc` raw clip, run a 2-segment plan (1 copy + 1 freeze), assert the output duration matches the planned total within 0.2s. Mark with `@pytest.mark.skipif(shutil.which("ffmpeg") is None, ...)`.

Run both test files → Expected: PASS.

**Step 4: Commit**
```bash
git add engine/experimental/session-recorder/live/splice.py engine/experimental/session-recorder/live/tests/test_splice.py engine/experimental/session-recorder/live/tests/test_splice_io.py
git commit -m "feat(live): splice — freeze-frame re-time soft segments to ledger lengths"
```

---

## Task 8: `overlay.py` — Phase 2 mux voice from ledger (no detection)

Strip ALL detection from v5's `session_overlay.py`; keep only the muxing. Read voice onsets straight from the ledger (`voice.start` per non-dropped beat), build the `.srt`, and `amix` the clips onto `terminal.mp4` → `session.mp4`.

**Files:**
- Create: `engine/experimental/session-recorder/live/overlay.py`
- Test: `engine/experimental/session-recorder/live/tests/test_overlay.py`

**Step 1: Write the failing test (srt builder is pure)**
```python
import overlay

def test_srt_cues_come_straight_from_ledger_voice_windows():
    beats = [
        {"voice": {"clip": "_voice/intro_1.mp3", "start": 1.0, "end": 3.0},
         "text": "請它寫", "drop": False},
        {"voice": None, "text": "", "drop": True},          # dropped -> no cue
        {"voice": {"clip": "_voice/outro_1.mp3", "start": 5.0, "end": 7.0},
         "text": "完成了", "drop": False},
    ]
    srt = overlay.build_srt(beats)
    assert "00:00:01,000 --> 00:00:03,000" in srt
    assert "請它寫" in srt and "完成了" in srt
    assert srt.count("-->") == 2     # the dropped beat produced no cue
```
Run → Expected: FAIL.

**Step 2: Implement**
- Copy `srt_ts` from v5. `build_srt(beats)` iterates non-dropped beats with a voice, ordered by `voice.start`, emitting numbered cues from `beat["text"]`.
- `mux(demo, led)`: collect `(onset=voice.start, mp3=os.path.join(demo, voice.clip))` for non-dropped voiced beats; build the v5 `adelay`/`amix` filter (copy that block verbatim — input 0 is the video, clip j is input j+1); write `session.srt` + `session.mp4` (`-c:v copy`).
- No `signals`, no `detect_*`, no `fit_think` — those moved to detect_anchors / author.

Run → Expected: PASS.

**Step 3: Commit**
```bash
git add engine/experimental/session-recorder/live/overlay.py engine/experimental/session-recorder/live/tests/test_overlay.py
git commit -m "feat(live): overlay — mux voice from ledger onsets, no detection"
```

---

## Task 9: `panel.py` — Phase 2 panel from the SAME ledger

Refactor `session_panel.py` to read **the ledger** for all timing (launch flag reveals = each launch_flag beat's `panel.switch_at`; per-turn header = that turn's intro beat `panel.switch_at`; conclusion = the turn's think/outro `visual.end`). The timeline is still read only to **label** tool events, mapped into each turn's `[visual.start, visual.end]` output window by wall-clock fraction (copy v5's fraction logic, but feed it ledger output times — this is what kills the desync bug class).

**Files:**
- Create: `engine/experimental/session-recorder/live/panel.py`
- Test: `engine/experimental/session-recorder/live/tests/test_panel.py`

**Step 1: Write the failing test (keyframe-time derivation is pure)**
```python
import panel

def test_keyframe_times_read_from_ledger_not_redetected():
    led = {"beats": [
        {"kind": "launch_flag", "turn_idx": -1, "panel": {"switch_at": 0.5}},
        {"kind": "launch_flag", "turn_idx": -1, "panel": {"switch_at": 2.0}},
        {"kind": "intro", "turn_idx": 0, "panel": {"switch_at": 6.0}},
        {"kind": "think", "turn_idx": 0, "visual": {"start": 9.0, "end": 14.0}},
    ]}
    keys = panel.keyframe_times(led)
    # two launch reveals, one turn header, one conclusion (= think visual.end)
    assert [round(k["t"], 1) for k in keys if k["type"] == "launch"] == [0.5, 2.0]
    assert any(k["type"] == "turn_header" and abs(k["t"] - 6.0) < 1e-9 for k in keys)
    assert any(k["type"] == "conclusion" and abs(k["t"] - 14.0) < 1e-9 for k in keys)
```
Run → Expected: FAIL.

**Step 2: Implement**
- `keyframe_times(led)`: walk beats → launch reveals (`panel.switch_at`), per-turn header (`intro.panel.switch_at`), tool-event slots (mapped into the turn's hard `visual` window), conclusion (turn's `visual.end`).
- Reuse v5's PIL rendering (`launch_panel`, `turn_panel`, `draw_icon`, `_wrap`, `last_session`, the concat + hstack composite) **verbatim** — only the timing source changes from `session_sync.json` to `keyframe_times(led)`.
- Tool-event labels: keep v5's `frac = (ev.t - ups.t) / span_w` then `ev_v = visual.start + frac*(visual.end - visual.start)`, but `visual.*` now come from the ledger.

Run → Expected: PASS.

**Step 3: Commit**
```bash
git add engine/experimental/session-recorder/live/panel.py engine/experimental/session-recorder/live/tests/test_panel.py
git commit -m "feat(live): panel — read ledger only, kills terminal/panel desync"
```

---

## Task 10: `lint.py` — Phase 3 deterministic gate

Replace `verify_session.py` + `validate_sync.py` with one `lint.py` over the **finalized ledger**: the serialization invariant + internal relations (every Tier-1 present; ride beats `voice ⊆ visual`; lead beats `voice.end ≤ visual.start`; anchors ordered). Keep the filmstrip eyeball (reuse v5's `grab`/montage). Deterministic ⇒ failures are authoring errors, not detection noise.

**Files:**
- Create: `engine/experimental/session-recorder/live/lint.py`
- Test: `engine/experimental/session-recorder/live/tests/test_lint.py`

**Step 1: Write the failing tests**
```python
import lint

def _led(beats):
    return {"beats": beats, "meta": {}}

def test_lint_passes_clean_ledger():
    beats = [
        {"id": "a", "kind": "intro", "tier": 1, "mode": "lead", "drop": False,
         "voice": {"start": 0.0, "end": 2.0}, "visual": {"start": 2.3, "end": 4.0},
         "panel": {"switch_at": 0.0}},
        {"id": "b", "kind": "think", "tier": 2, "mode": "ride", "drop": False,
         "voice": {"start": 4.6, "end": 6.0}, "visual": {"start": 4.5, "end": 8.0},
         "panel": {"switch_at": 0.0}},
    ]
    report = lint.check(_led(beats))
    assert report["ok"] is True and report["violations"] == []

def test_lint_flags_ride_voice_outside_visual():
    beats = [{"id": "b", "kind": "think", "tier": 2, "mode": "ride", "drop": False,
              "voice": {"start": 4.5, "end": 9.0},          # ends after visual.end
              "visual": {"start": 4.5, "end": 8.0}, "panel": {"switch_at": 4.5}}]
    report = lint.check(_led(beats))
    assert report["ok"] is False
    assert any("ride" in v for v in report["violations"])

def test_lint_flags_missing_tier1():
    # a dropped Tier-1 is structurally illegal
    beats = [{"id": "a", "kind": "intro", "tier": 1, "mode": "lead", "drop": True,
              "voice": None, "visual": {"start": 2.0, "end": 4.0},
              "panel": {"switch_at": 2.0}}]
    report = lint.check(_led(beats))
    assert report["ok"] is False
    assert any("tier-1" in v.lower() for v in report["violations"])

def test_lint_flags_lead_voice_not_leading():
    beats = [{"id": "a", "kind": "intro", "tier": 1, "mode": "lead", "drop": False,
              "voice": {"start": 0.0, "end": 3.0},          # ends after visual.start
              "visual": {"start": 2.0, "end": 4.0}, "panel": {"switch_at": 0.0}}]
    report = lint.check(_led(beats))
    assert report["ok"] is False
    assert any("lead" in v.lower() for v in report["violations"])
```
Run → Expected: FAIL.

**Step 2: Implement**
```python
#!/usr/bin/env python3
"""lint.py — Phase 3: deterministic gate over the finalized ledger. Failures are
AUTHORING errors (the timeline is computed, not detected). Exit 0 PASS / 1 FAIL.
"""
import argparse

from ledger import beat_end, load, serialization_violations


def check(led):
    beats = led["beats"]
    violations = []
    # the one cross-beat rule
    for s in serialization_violations(beats):
        violations.append(f"serialization: {s['prev']}->{s['next']} gap {s['gap']}s")
    for b in beats:
        if b.get("drop"):
            if b["tier"] == 1:
                violations.append(f"tier-1 beat {b['id']} ({b['kind']}) was dropped — "
                                  f"the spine must never drop")
            continue
        v, vis = b.get("voice"), b.get("visual")
        if b["mode"] == "lead" and v and vis and v["end"] > vis["start"] + 0.05:
            violations.append(f"lead beat {b['id']}: voice does not lead "
                              f"(voice.end {v['end']} > visual.start {vis['start']})")
        if b["mode"] == "ride" and v and vis and (
                v["start"] < vis["start"] - 0.05 or v["end"] > vis["end"] + 0.05):
            violations.append(f"ride beat {b['id']}: voice not contained in visual "
                              f"[{vis['start']},{vis['end']}]")
        if vis and vis["start"] > vis["end"] + 0.001:
            violations.append(f"beat {b['id']}: visual anchors out of order")
    return {"ok": not violations, "violations": violations}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    args = ap.parse_args()
    import os
    led = load(os.path.join(os.path.abspath(args.demo), "ledger.json"))
    report = check(led)
    for v in report["violations"]:
        print("  FAIL:", v)
    print("PASS: ledger satisfies the serialization invariant + all internal relations."
          if report["ok"] else f"\nFAIL ({len(report['violations'])} violation(s)).")
    raise SystemExit(0 if report["ok"] else 1)
```
Add the optional `--filmstrip` path that reuses v5's `grab`/`magick montage` against `session_panel.mp4` at each beat's `panel.switch_at` (copy from `validate_sync.py`), keeping the human eyeball.

Run → Expected: PASS (4 passed).

**Step 3: Commit**
```bash
git add engine/experimental/session-recorder/live/lint.py engine/experimental/session-recorder/live/tests/test_lint.py
git commit -m "feat(live): lint — deterministic gate over the finalized ledger"
```

---

## Task 11: End-to-end driver + README pipeline

Wire the five stages into one runnable pipeline and document it. No new logic — just orchestration so a recording can be produced and validated.

**Files:**
- Create: `engine/experimental/session-recorder/live/run_v6.sh`
- Modify: `engine/experimental/session-recorder/live/README.md`

**Step 1: Write the driver**

`run_v6.sh <demo> <script.json>`:
```bash
#!/usr/bin/env bash
set -euo pipefail
SR="$(cd "$(dirname "$0")" && pwd)"
DEMO="${1:?demo dir}"; SCRIPT="${2:?script.json}"
PY="$(cd "$SR/../../../.." && pwd)/.venv/bin/python"

"$SR/claude_sandbox.sh" "$DEMO"                                   # isolated sandbox (reuse v5)
python3 "$SR/gen_capture_tape.py" --demo "$DEMO" --script "$SCRIPT" \
        --width 1200 --height 1080 --font-size 26 -o "$DEMO/session.tape"
( cd "$DEMO" && vhs session.tape )                               # -> terminal_raw.mp4 + timeline
"$PY" "$SR/author.py" --demo "$DEMO" --script "$SCRIPT"          # detect + author -> ledger.json
"$PY" "$SR/splice.py" --demo "$DEMO"                             # -> terminal.mp4
"$PY" "$SR/overlay.py" --demo "$DEMO"                            # -> session.mp4 + .srt
"$PY" "$SR/panel.py" --demo "$DEMO"                              # -> session_panel.mp4
"$PY" "$SR/lint.py" --demo "$DEMO"                               # deterministic gate
echo "v6 pipeline complete: $DEMO/session_panel.mp4"
```
(`author.py --demo --script` runs `detect_anchors.detect(...)` then `build_ledger(...)` — Phase 0 detection happens **inside** author so claude is launched exactly once, in the vhs step only.)

**Step 2: Verify the driver wiring without a real recording**

Run: `bash -n engine/experimental/session-recorder/live/run_v6.sh` (syntax check) and `shellcheck` it.
Expected: no errors.

**Step 3: Rewrite the README pipeline section**

Replace the v5 pipeline block with the v6 five-stage flow + the `ledger.json` schema, the tier table, and the one serialization invariant. Note v5 files remain until validation passes (Task 12). Keep the sandbox + sentinel sections verbatim.

**Step 4: Commit**
```bash
git add engine/experimental/session-recorder/live/run_v6.sh engine/experimental/session-recorder/live/README.md
git commit -m "feat(live): v6 end-to-end driver + README (capture-once, ledger-driven)"
```

---

## Task 12: Stress-scenario validation + v5 retirement

The design's done-criteria: lint passes the invariant + every Tier-1 present, the filmstrip confirms left-terminal == right-panel == narrated moment, and claude was launched **once**. Validate on the three stress scenarios, then retire v5.

**Files:**
- Create: `engine/experimental/session-recorder/live/script.qa.json`, `script.mixed.json` (2-turn text Q&A; mixed) — reuse `script.example.json` as the 3-turn-ish file-writing case.
- Possibly Modify: any v6 module that the real recordings reveal a bug in (fix at the pure-core + add a regression test, per the loop-engineering rule in `engine/context/sync-model.md`).

**Step 1: Run scenario A (file-writing, the existing script)**
```bash
bash engine/experimental/session-recorder/live/run_v6.sh /tmp/v6a \
     engine/experimental/session-recorder/live/script.example.json
```
Expected: `lint` exits 0; `/tmp/v6a/session_panel.mp4` exists.

**Step 2: Confirm claude launched exactly once**

Run: `grep -c UserPromptSubmit /tmp/v6a/session-timeline.jsonl` and confirm it equals the turn count, and there is exactly one `SessionStart` for the take. (No second claude run anywhere in the pipeline — only the vhs step starts it.)

**Step 3: Eyeball the filmstrip**

Run: `engine/.../lint.py --demo /tmp/v6a --filmstrip` then open `/tmp/v6a/lint_filmstrip.png`.
Confirm: at each beat, left terminal == right panel == the narrated line.

**Step 4: Run scenarios B (text Q&A) and C (mixed)**

Author `script.qa.json` (2 text-only turns, no tool calls) and `script.mixed.json` (one tool turn + one text turn). Run the driver on each into `/tmp/v6b`, `/tmp/v6c`. Each must lint-pass and eyeball-pass. Any failure → fix the offending pure function, add a regression test asserting the new invariant (do not patch around it), re-run.

**Step 5: Retire v5**

Once all three scenarios pass lint + eyeball with claude launched once:
- `git rm` the v5-only files superseded by v6: `gen_session_tape.py`, `session_overlay.py`, `session_panel.py`, `verify_session.py`, `validate_sync.py`.
- Update `engine/experimental/session-recorder/live/README.md` to drop the v5 references.

**Step 6: Final test sweep + commit**
```bash
cd /Users/htlin/vhs-demo && .venv/bin/python -m pytest engine/experimental/session-recorder/live/tests/ -v
git add -A engine/experimental/session-recorder/live/
git commit -m "feat(live): v6 validated on 3 stress scenarios; retire v5 pipeline"
```

---

## Done criteria (from the design doc)

- `lint.py` passes the serialization invariant + every Tier-1 present (deterministic).
- The filmstrip confirms left-terminal == right-panel == narrated moment on all three scenarios.
- claude was launched **once** (capture only) per recording.
- All unit tests green: `pytest engine/experimental/session-recorder/live/tests/ -v`.
