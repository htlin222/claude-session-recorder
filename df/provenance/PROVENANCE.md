# df — build provenance

Frozen 2026-06-27 02:47. A snapshot of this clip's `intermediate/` (regenerable
scratch) so the finished clip stays reproducible on its own.

## Verdict

`[df] PASS: ok | J-cut 11/11 mean 0.35s, min gap 0.99s`

- structural sync: **OK** (11/11 clears, guided)
- narration fits: **True** (voice 283.37s ≤ final 298.0s)
- duration: final **298.0s**
- J-cut: **11/11** transitions, mean 0.35s, 0 clips
- voice overruns: **0** (min gap 0.993s)

## Files

- `timeline.json`
- `sync_report.json`
- `jcut_report.json`
- `demo.tape`
- `terminal.mp4`
- `narration.mp3`
- `config.toml`
- `build.log`
- `lesson/`
- `verify.json`

## Re-render from this bundle (no vhs), from THIS folder

```bash
mkdir -p intermediate/audio
cp provenance/timeline.json   intermediate/timeline.json
cp provenance/terminal.mp4    intermediate/terminal.mp4
cp provenance/narration.mp3   intermediate/audio/df.mp3
rm -f intermediate/clears_override.json
.venv/bin/python src/overlay.py            # -> ./df.mp4
```

Full rebuild (edit lesson.py first) and handoff: see this folder's CLAUDE.md.
