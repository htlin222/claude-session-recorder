# Downstream reuse of `ledger.json`

`ledger.json` (written by `author.py`, reconciled by `splice.py`) is the pipeline's
one source of truth for *when everything happens* — every internal stage
(`overlay.py`, `panel.py`, `lint.py`) reads it rather than re-deriving a time it
already holds (see `ledger.py`'s module docstring and the
[event-ledger design doc](../../../../docs/plans/2026-06-28-event-ledger-deterministic-pipeline-design.md)).

It turns out `ledger.json` is *also* useful to tools that live entirely outside
this repo, once a batch of clips has been recorded: an SFX overlay pass and an
auto-generated title-card pass, both contributed as a
["show & tell"](https://github.com/htlin222/claude-session-recorder/issues/3)
after producing 124 clips. Neither reaches into the recorder — both just read
the finished `ledger.json` off disk. This doc writes down the slice of the
schema they depend on, so it can be treated (and kept stable) as a small public
output surface rather than a purely internal implementation detail.

## The relevant schema slice

A ledger is `{"beats": [...], "meta": {...}}`. Downstream consumers care about
`meta`, specifically:

```jsonc
{
  "beats": [ /* per-narration-beat timing; not needed for these patterns */ ],
  "meta": {
    "vtot_out": 87.4,          // total output-timeline duration, seconds
    "demo": "/abs/path/to/demo",
    "segments": [
      // one entry per raw-video partition, in chronological order.
      // every segment carries "raw" (position in terminal_raw.mp4) and,
      // once output_timeline() has run, "out" (position in the final
      // spliced session.mp4 / session_panel.mp4).
      {"kind": "boot", "raw": [0.0, 4.2], "role": "boot",
       "out_dur": 6.1, "out": [0.0, 6.1]},

      {"kind": "soft", "raw": [4.2, 5.0], "role": "pre", "turn_idx": 0,
       "out_dur": 3.4, "out": [6.1, 9.5]},

      {"kind": "hard", "raw": [5.0, 38.7], "turn_idx": 0,
       "submit": 6.3,             // raw-time moment Enter was pressed
       "out": [9.5, 43.2]},

      {"kind": "soft", "raw": [38.7, 39.1], "role": "tail",
       "out_dur": 2.0, "out": [43.2, 45.2]}
    ]
  }
}
```

Field notes, verified against current `ledger.py` / `detect_anchors.py` /
`author.py` (not just transcribed from the issue):

- **`kind`** is one of three values, not two: **`"boot"`** (the opening launch
  animation, always the first segment), **`"soft"`** (a static stretch of dead
  air the splice stage freeze-frame stretches or trims to fit narration —
  `role` is `"pre"` for the gap before a turn's typing starts, or `"tail"` for
  the trailing gap after the last turn), and **`"hard"`** (a turn's real
  `typing → submit → answer` window, captured 1:1, never freeze-frame
  re-timed).
- **`raw`** — `[start, end]` seconds in the original single `claude` capture
  (`terminal_raw.mp4`).
- **`out`** — `[start, end]` seconds in the final spliced/output timeline
  (`session.mp4` / `session_panel.mp4`), added by `ledger.output_timeline()`.
  This is what's on screen in the shipped video.
- **`out_dur`** — present on `"boot"`/`"soft"` segments only: the authored
  duration `author.py` sized this segment to (soft segments are
  freeze-extended/trimmed to exactly this many seconds). `"hard"` segments have
  no `out_dur` because they're copied verbatim — their output length always
  equals their raw length.
- **`turn_idx`** — present on `"hard"` segments and `"soft"` segments with
  `role == "pre"`; the 0-based index into the script's `turns` list.
- **`submit`** — present **only** on `"hard"` segments, in **raw** time: the
  moment the prompt's Enter keypress was detected (clamped into
  `[raw[0], raw[1]]` by `detect_anchors.raw_segments`). In the current code a
  `"hard"` segment always has a non-null `submit`, but guarding with
  `seg.get("submit") is not None` (as the original write-up does) is cheap
  insurance against a future segment shape that doesn't set it.

> **Schema discrepancy vs. the issue write-up:** the issue describes segments
> as only `kind == "hard"` or `"soft"`. The current pipeline also emits a third
> kind, `"boot"` (the launch/opening segment) — it just never carries `submit`,
> so it's invisible to a `kind == "hard"` filter and doesn't change the
> formulas below. Called out here so anyone iterating over *all* segments
> (rather than filtering to `"hard"`) doesn't assume only two kinds exist.

## Why `hard` segments give an exact linear raw→out mapping

`"hard"` segments are copied into the output verbatim by the splice stage —
never freeze-frame stretched like `"soft"` segments — so for any raw-time
moment `t` inside a hard segment, its position in the output timeline is an
affine map with slope 1:

```
out_t = seg["out"][0] + (t - seg["raw"][0])
```

Applied to the two moments that matter for a turn — the submit keypress and
the turn's end (`raw[1]`, already equal to `out[1]` under this mapping) — this
is exactly `panel.py`'s own internal formula (`_tool_events`, and the near-
identical `sub_out` computation in `author.py`), which is a good sign the
downstream pattern isn't a reverse-engineered guess:

```python
for seg in ledger["meta"]["segments"]:
    if seg["kind"] == "hard" and seg.get("submit") is not None:
        submit_out = seg["out"][0] + (seg["submit"] - seg["raw"][0])
        stop_out   = seg["out"][1]     # the turn's "done" moment, already output-time
```

`submit_out` is when the user's prompt was submitted, on the *shipped*
timeline; `stop_out` is when Claude's reply finished (the Stop-equivalent
moment) on the same timeline. No re-detection against the rendered video is
needed — the ledger already computed both.

## Pattern 1: SFX overlay from `meta.segments`

Goal: an intro chime, a "submit" click, and a "done" completion sound per clip,
placed at frame-accurate moments in the final video.

1. Walk `ledger["meta"]["segments"]`, filter to `kind == "hard"`.
2. For each turn compute `submit_out` and `stop_out` with the formula above.
3. Build one ffmpeg input per SFX occurrence, each delayed to its timestamp
   with `adelay=<ms>|<ms>` (stereo needs the delay twice, comma-separated).
4. Mix all SFX inputs with the narration/original audio track using:

   ```
   amix=inputs=N:duration=first:normalize=0
   ```

   **The `normalize=0` is load-bearing.** `amix`'s default behavior applies
   loudness normalization *across all inputs*, which quietens the narration
   track right along with the SFX — not what you want when the SFX are meant
   to sit under the voice, not compete with it. Omitting `normalize=0` is the
   most likely way to silently regress narration volume in a batch run.
5. Validate every output afterward, not just spot-check one: `ffprobe`
   video-vs-audio stream duration match (tolerant of ~1s drift), and an
   `ffprobe`/`ffmpeg -af volumedetect` peak check confirming no clipping and
   that SFX peaks stay comfortably under the narration level.

## Pattern 2: auto-generated title cards from a small `meta.toml`

Goal: a 1920×1080 title card per clip (module/position numbering, title,
subtitle, difficulty badge, estimated time, prev/next nav) for platform
upload — generated straight from data, no manual design pass per clip.

- Each clip carries a small `meta.toml` (title, subtitle, module/position,
  difficulty, estimated time).
- The card is built as an SVG directly in Python (no template engine) at
  1920×1080, then rasterized with `rsvg-convert`. CJK text renders with
  **Noto Sans CJK TC**, and long titles are line-wrapped using a
  character-width estimate (CJK glyphs are roughly square; Latin glyphs are
  narrower) since SVG has no built-in text reflow.
- **Prev/next navigation is resolved without an external index:** the
  generator looks up the *neighboring* clip's own `meta.toml` to pull its
  title for the "next up" / "previously" strip. Every clip is
  self-describing, so the whole series forms a linked list purely through
  sibling metadata files — no central manifest to keep in sync.

Note this pattern doesn't touch `ledger.json` at all — it's included here
because it's the second half of the same "downstream consumer of this
pipeline's already-computed output" story, and shares the same core lesson:
small, stable, self-describing per-clip data (a `meta.toml` here, `ledger.json`
there) is what makes post-production tooling easy to bolt on later.

## Both patterns are pure downstream consumers

Neither the SFX overlay nor the title-card generator imports from or modifies
anything under this package. They run as a separate post-processing step
*after* `record-session`'s own pipeline has finished producing
`session.mp4` / `session_panel.mp4`, treating `ledger.json` purely as a
read-only artifact on disk. If `ledger.json`'s segment schema changes, this
doc (and the two source-of-truth modules it's grounded in — `ledger.py`,
specifically `output_timeline()`, and `author.py`'s `build_ledger()`) should be
the first things checked and updated.
