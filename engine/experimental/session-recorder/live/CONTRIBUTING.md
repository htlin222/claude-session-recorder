# Contributing

Thanks for your interest in the Claude session recorder. This is the developer
guide; for what the tool does, see [`README.md`](./README.md).

## Setup

```bash
git clone https://github.com/htlin222/claude-session-recorder
cd claude-session-recorder            # → engine/experimental/session-recorder/live

# Python deps (editable install + dev extras)
pip install -e ".[dev]"

# External CLI tools (NOT pip-installable) — macOS:
brew install vhs ffmpeg tmux imagemagick
pipx install edge-tts
```

`vhs`, `ffmpeg`/`ffprobe`, `tmux` and `magick` are only needed to *record*; the
unit tests run without them.

## Running tests

```bash
pytest tests/          # 88 pure-logic unit tests, no external tools required
```

CI (`.github/workflows/test.yml`) runs exactly this on Python 3.11 and 3.12. The
recording pipeline needs macOS + a real Claude Code TUI and is not run in CI.

## Architecture (3 lines)

1. **Capture once** — drive a real Claude TUI under `vhs`/`tmux`, recording the
   raw terminal video plus a Stop-hook sentinel that marks each turn boundary.
2. **Author → freeze-frame splice → mux/panel** — derive anchors, author the
   narration, splice freeze frames so video and voiceover stay in sync, then mux
   audio and composite the side panel.
3. **Lint** — verify the result against the ledger. A single **`ledger.json`** is
   the source of truth that every stage reads and writes.

## Testing ethos (loop engineering)

Every new failure mode becomes a regression test. When the pipeline mis-syncs,
drops a turn, or mislays a frame in the real world, reproduce it as a small
deterministic case in `tests/` first, then fix it. The test suite is the memory
of every bug we've already paid for.

## Code style

- **Pure logic is unit-tested.** Anchor math, splice timing, overlay/panel
  layout and question parsing are pure functions with no I/O — keep them that
  way so they stay testable.
- **I/O stays thin.** Subprocess calls to `vhs`/`ffmpeg`/`tmux`, file reads and
  writes live in thin wrappers at the edges, separate from the logic they feed.

## Adding a new demo scenario

A demo is described by a `script.*.json` (see `script.example.json`,
`script.question.json`, `script.robust.json` in this directory). To add one:

1. Copy an existing `script.*.json` and edit the prompts / narration / answers.
2. Run it through the recorder CLI (`record-session`, see README).
3. If it exposes a new failure mode, add a regression test in `tests/` before
   fixing.

Producing a large batch of clips (a whole course, not one demo)? See
[`docs/batch-production-pipeline.md`](./docs/batch-production-pipeline.md) for
a reusable research → syllabus → script-writing → production pipeline.

## Design docs

The deterministic-pipeline and interactive-question designs live in the repo at
`docs/plans/`:

- `2026-06-27-claude-session-voiceover-sync-design.md`
- `2026-06-28-event-ledger-deterministic-pipeline-design.md`
- `2026-06-28-event-ledger-deterministic-pipeline-plan.md`
- `2026-06-28-interactive-askuserquestion-recording-plan.md`
