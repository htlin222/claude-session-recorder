# awk — build provenance

Frozen 2026-06-27 01:05 from `clip/intermediate/` (shared scratch — overwritten by
the next build, which is why this snapshot exists).

## Verdict

`[awk] PASS: ok | J-cut 13/13 mean 0.35s, min gap 0.99s`

- structural sync: **OK** (13/13 clears, guided)
- narration fits: **True** (voice 289.1s ≤ final 306.84s)
- duration: final **306.84s**
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
- `build.log`
- `lesson/`
- `verify.json`

## Re-render from this bundle (no vhs)

```bash
# from repo root — restore the scratch this render needs, then re-composite
mkdir -p clip/intermediate/awk/audio
cp awk/build/timeline.json   clip/intermediate/awk/timeline.json
cp awk/build/terminal.mp4    clip/intermediate/awk/terminal.mp4
cp awk/build/narration.mp3   clip/intermediate/awk/audio/awk.mp3
rm -f clip/intermediate/awk/clears_override.json
( cd clip && LESSON=awk .venv/bin/python src/overlay.py )   # -> clip/dist/awk.mp4
```

Canonical lesson source (edit + full rebuild): `clip/lessons/awk/`.
