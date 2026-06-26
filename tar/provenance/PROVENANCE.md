# tar — build provenance

Frozen 2026-06-27 01:04 from `clip/intermediate/` (shared scratch — overwritten by
the next build, which is why this snapshot exists).

## Verdict

`[tar] PASS: ok | J-cut 10/10 mean 0.35s, min gap 1.00s`

- structural sync: **OK** (10/10 clears, guided)
- narration fits: **True** (voice 272.59s ≤ final 286.32s)
- duration: final **286.32s**
- J-cut: **10/10** transitions, mean 0.35s, 0 clips
- voice overruns: **0** (min gap 0.998s)

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
mkdir -p clip/intermediate/tar/audio
cp tar/build/timeline.json   clip/intermediate/tar/timeline.json
cp tar/build/terminal.mp4    clip/intermediate/tar/terminal.mp4
cp tar/build/narration.mp3   clip/intermediate/tar/audio/tar.mp3
rm -f clip/intermediate/tar/clears_override.json
( cd clip && LESSON=tar .venv/bin/python src/overlay.py )   # -> clip/dist/tar.mp4
```

Canonical lesson source (edit + full rebuild): `clip/lessons/tar/`.
