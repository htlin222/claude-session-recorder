# rg — a self-contained CLI-education clip

This folder is **portable and self-contained**: it has its own copy of the render
engine (`src/`), its content (`lesson.py`), its knobs (`config.toml`), and its
demo environment builder (`setup.sh`). Move it anywhere; it still builds. You
(the next agent/human) can take it over with just this file.

## What it is
A 1920×1080 teaching video: left = a VHS terminal running the commands, right =
an explainshell-style panel that dissects each command token by token, one
continuous zh-TW narration, J-cut scene transitions, sidecar `.srt` subtitles.
Topic + title live in `lesson.py` (`SLUG` / `TITLE`).

## Layout
```
rg/
  CLAUDE.md          # this file
  lesson.py          # THE CONTENT — the only file you normally edit
  setup.sh           # builds the throwaway demo env this clip's commands need
  config.toml        # knobs: voice / size / timing / colours
  src/               # vendored engine (do not edit per-clip unless porting a fix)
    clipkit.py  build.py  overlay.py  verify_sync.py  bundle.py  envcheck.py
  intermediate/      # scratch (terminal.mp4, demo.tape, timeline.json…) — gitignored
  rg.mp4 .srt .html   # the product
  provenance/        # frozen record: verify.json (the 5 gates), reports, lesson copy
```

## Requirements
`vhs`, `ttyd`, `ffmpeg` (libx264), the CLI tool being taught, `edge-tts`, `tree`,
Python 3.11+, and a venv with `pillow`+`numpy` for the panel renderer.

## Build / rebuild (run from THIS folder)
```bash
# one-time: venv for the panel renderer
uv venv .venv && uv pip install --python .venv/bin/python pillow numpy

python3 src/build.py                          # narration + demo.tape + timeline.json
bash   setup.sh                               # (re)create the demo env in intermediate/
( cd intermediate && vhs demo.tape )          # -> intermediate/terminal.mp4
.venv/bin/python src/overlay.py               # -> ./rg.mp4 + .srt  (panel + J-cut)
.venv/bin/python src/verify_sync.py --target-sec 300 --tol-sec 60   # 5-gate sync check
.venv/bin/python src/bundle.py                # freeze provenance/
# optional offline player:
python3 ~/.claude/skills/agent-demo-recorder/scripts/gen_html.py rg.mp4 -o rg.html
```
Only changed narration/timing? You can re-run just `overlay.py` (no vhs) if
`terminal.mp4` is still valid; otherwise rebuild from `build.py`.

## Editing the content (`lesson.py`)
Build the `SCRIPT` list from three builders (`from clipkit import S, R, CLR`):
- `S("一句旁白")` — one continuous-narration sentence (zh-TW).
- `R("command")` — a command typed + run on screen.
- `CLR(key=…, hero=…, toks=[(substr, "註解", role)])` — opens a scene + its panel.
  role → colour: `ord` ordinary flag, `star` the scene's KEY flag, `path` operands.

**Hard rules** (the build rejects / mis-syncs otherwise):
1. `toks` are listed left-to-right as they appear in `hero`.
2. every `star`/`ord` token's flag text must appear VERBATIM in one of that
   scene's `S()` sentences (so the panel reveal lands in typing-sync).
3. each `S()` is one complete sentence ending in 。！？ (edge-tts splits 1:1).

**Platform**: this renders on macOS where some tools are BSD variants that differ
from Linux/GNU (e.g. `sed`→use `gsed`, `awk`→`gawk`, `date`→`gdate`). Probe with
`python3 src/envcheck.py <tool>` and teach the GNU variant or the strict POSIX
subset, noting the split in the intro.

## Verify before you ship
`verify_sync.py` gates five things, none silently skipped: structural sync (every
scene locked to a real terminal clear), narration-not-cut, duration (≈5±1 min),
J-cut clips, and voice-overruns. `PASS` ⇒ good. A `FAIL_FIXABLE` writes
`intermediate/clears_override.json`; just re-run `overlay.py` then re-verify.

## Provenance
`provenance/` is the frozen record of the last render (verify verdict, timeline,
reports, narration, terminal.mp4, a copy of lesson.py). `provenance/PROVENANCE.md`
shows how to re-composite from it without re-running vhs.
