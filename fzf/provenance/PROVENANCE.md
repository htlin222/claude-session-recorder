# fzf — build provenance

Frozen 2026-06-26 23:52 from `clip/intermediate/` (shared scratch — overwritten by
the next build, which is why this snapshot exists).

## Verdict

`[fzf] PASS: ok | J-cut 13/13 mean 0.35s, min gap 1.00s`

- structural sync: **OK** (13/13 clears, guided)
- narration fits: **True** (voice 277.54s ≤ final 297.56s)
- duration: final **297.56s**
- J-cut: **13/13** transitions, mean 0.35s, 0 clips
- voice overruns: **0** (min gap 1.003s)

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

## Re-render from this bundle (no vhs)

```bash
# from repo root — restore the scratch this render needs, then re-composite
cp fzf/provenance/timeline.json   clip/intermediate/timeline.json
cp fzf/provenance/terminal.mp4    clip/intermediate/terminal.mp4
cp fzf/provenance/narration.mp3   clip/intermediate/audio/fzf.mp3
rm -f clip/intermediate/clears_override.json
( cd clip && .venv/bin/python src/overlay.py )   # -> clip/dist/fzf.mp4
```

Canonical lesson source (edit + full rebuild): `clip/lessons/fzf/`.
