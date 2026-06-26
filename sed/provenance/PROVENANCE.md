# sed — build provenance

Frozen 2026-06-27 01:32 from `clip/intermediate/` (shared scratch — overwritten by
the next build, which is why this snapshot exists).

## Verdict

`[sed] PASS: ok | J-cut 11/11 mean 0.35s, min gap 0.99s`

- structural sync: **OK** (11/11 clears, guided)
- narration fits: **True** (voice 282.24s ≤ final 297.68s)
- duration: final **297.68s**
- J-cut: **11/11** transitions, mean 0.35s, 0 clips
- voice overruns: **0** (min gap 0.992s)

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
mkdir -p clip/intermediate/sed/audio
cp sed/build/timeline.json   clip/intermediate/sed/timeline.json
cp sed/build/terminal.mp4    clip/intermediate/sed/terminal.mp4
cp sed/build/narration.mp3   clip/intermediate/sed/audio/sed.mp3
rm -f clip/intermediate/sed/clears_override.json
( cd clip && LESSON=sed .venv/bin/python src/overlay.py )   # -> clip/dist/sed.mp4
```

Canonical lesson source (edit + full rebuild): `clip/lessons/sed/`.
