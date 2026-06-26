# grep — build provenance

Frozen 2026-06-27 01:09 from `clip/intermediate/` (shared scratch — overwritten by
the next build, which is why this snapshot exists).

## Verdict

`[grep] PASS: ok | J-cut 12/12 mean 0.35s, min gap 1.00s`

- structural sync: **OK** (12/12 clears, override)
- narration fits: **True** (voice 283.08s ≤ final 299.52s)
- duration: final **299.52s**
- J-cut: **12/12** transitions, mean 0.35s, 0 clips
- voice overruns: **0** (min gap 1.0s)

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
mkdir -p clip/intermediate/grep/audio
cp grep/build/timeline.json   clip/intermediate/grep/timeline.json
cp grep/build/terminal.mp4    clip/intermediate/grep/terminal.mp4
cp grep/build/narration.mp3   clip/intermediate/grep/audio/grep.mp3
rm -f clip/intermediate/grep/clears_override.json
( cd clip && LESSON=grep .venv/bin/python src/overlay.py )   # -> clip/dist/grep.mp4
```

Canonical lesson source (edit + full rebuild): `clip/lessons/grep/`.
