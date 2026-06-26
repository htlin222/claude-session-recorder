# jq — build provenance

Frozen 2026-06-27 01:55. A snapshot of this clip's `intermediate/` (regenerable
scratch) so the finished clip stays reproducible on its own.

## Verdict

`[jq] PASS: ok | J-cut 13/13 mean 0.35s, min gap 0.99s`

- structural sync: **OK** (13/13 clears, detect)
- narration fits: **True** (voice 280.68s ≤ final 298.64s)
- duration: final **298.64s**
- J-cut: **13/13** transitions, mean 0.35s, 0 clips
- voice overruns: **0** (min gap 0.995s)

## Files

- `timeline.json`
- `sync_report.json`
- `jcut_report.json`
- `demo.tape`
- `terminal.mp4`
- `narration.mp3`
- `config.toml`
- `lesson/`
- `verify.json`

## Re-render from this bundle (no vhs), from THIS folder

```bash
mkdir -p intermediate/audio
cp provenance/timeline.json   intermediate/timeline.json
cp provenance/terminal.mp4    intermediate/terminal.mp4
cp provenance/narration.mp3   intermediate/audio/jq.mp3
rm -f intermediate/clears_override.json
.venv/bin/python src/overlay.py            # -> ./jq.mp4
```

Full rebuild (edit lesson.py first) and handoff: see this folder's CLAUDE.md.
