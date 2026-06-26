# engine/ — the clip render engine (template / source-of-truth)

This is the canonical engine. It is **not rendered directly**. Each finished clip
is a **portable, self-contained `<slug>/` folder** that vendors a COPY of this
engine plus its own `lesson.py` / `config.toml` / `CLAUDE.md`. The `/clip`
workflow scaffolds a new slug by copying this folder.

## What's here
```
engine/
  src/            clipkit.py (S/R/CLR + load_lesson), build.py, overlay.py,
                  verify_sync.py, bundle.py, envcheck.py
  config.toml     default knobs (voice / render / timing / panel colours)
  lesson.skel.py  skeleton content → becomes <slug>/lesson.py
  CLAUDE.tmpl.md  per-slug handoff doc → becomes <slug>/CLAUDE.md
  context/        design notes + the hard-won sync-model evolution
```

## Scaffold a new clip by hand
```bash
command cp -R engine <slug>
command mv <slug>/lesson.skel.py <slug>/lesson.py
command mv <slug>/CLAUDE.tmpl.md <slug>/CLAUDE.md
sed -i '' "s/{{SLUG}}/<slug>/g" <slug>/CLAUDE.md
# write <slug>/lesson.py (SLUG/TITLE/SCRIPT) and <slug>/setup.sh, then build
# (steps in <slug>/CLAUDE.md). The /clip workflow automates all of this.
```
A slug's `lesson.py` imports the builders from the vendored lib:
`from clipkit import S, R, CLR`. A slug's `setup.sh` builds its demo env into
`intermediate/`; start it with:
```bash
DEMO="$(cd "$(dirname "$0")" && pwd)/intermediate"; mkdir -p "$DEMO"; cd "$DEMO"
```

## Fixing an engine bug
Fix it HERE (`engine/src/…`), then propagate to existing slugs (each vendors its
own `src/`). New clips copied after the fix get it automatically. This is the
trade-off for portability: one canonical source, N self-contained copies.

Sync model + every trap learned the hard way: `context/sync-model.md`.
