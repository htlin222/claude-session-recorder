# jq — build provenance

Frozen 2026-06-27 01:14 from `clip/intermediate/` (shared scratch — overwritten by
the next build, which is why this snapshot exists).

## Verdict

`[jq] PASS: ok | J-cut 13/13 mean 0.35s, min gap 0.99s`

- structural sync: **OK** (13/13 clears, detect)
- narration fits: **True** (voice 280.68s ≤ final 298.56s)
- duration: final **298.56s**
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
mkdir -p clip/intermediate/jq/audio
cp jq/provenance/timeline.json   clip/intermediate/jq/timeline.json
cp jq/provenance/terminal.mp4    clip/intermediate/jq/terminal.mp4
cp jq/provenance/narration.mp3   clip/intermediate/jq/audio/jq.mp3
rm -f clip/intermediate/jq/clears_override.json
( cd clip && LESSON=jq .venv/bin/python src/overlay.py )   # -> clip/dist/jq.mp4
```

Canonical lesson source (edit + full rebuild): `clip/lessons/jq/`.
