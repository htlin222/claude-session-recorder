#!/usr/bin/env python3
"""Freeze a finished clip's provenance into  <slug>/provenance/.

clip/intermediate/ is SHARED, disposable scratch — the next build overwrites it,
so a delivered clip would otherwise be unreproducible the moment another lesson
renders. This copies the small, valuable record of ONE render next to the product
so each ./<slug>/ is self-contained and auditable. (The folder is "provenance/",
NOT "build/", because "build/" is in nearly everyone's global gitignore.)

  provenance/
    timeline.json     sync source of truth (re-verify / re-overlay)
    sync_report.json  structural-sync verdict (synced/detected/expected)
    jcut_report.json  per-transition J-cut leads + silent gaps
    verify.json       the 5-gate PASS/FAIL verdict (recomputed here)
    config.toml       snapshot of the knobs THIS clip was built with
    demo.tape         the generated VHS tape
    terminal.mp4      raw terminal render — re-overlay WITHOUT re-running vhs
    narration.mp3     the synthesized voice (re-overlay needs it)
    lesson/           a copy of the lesson source (lesson.py + setup.sh)
    build.log         build+render+verify stdout, if the pipeline teed one
    PROVENANCE.md     human index + verdict + how to re-render from this bundle

The heavy regenerable scratch (_seg*, _panels, the demo env) is deliberately NOT
copied — setup.sh + the pipeline regenerate it.

Usage:  python3 src/bundle.py --slug fzf [--dest DIR] [--target-sec 300] [--tol-sec 60]
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the slug folder
DEMO = f"{ROOT}/intermediate"
VENV = f"{ROOT}/.venv/bin/python"                # verify_sync needs numpy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default=None, help="default: from timeline.json")
    ap.add_argument("--target-sec", type=float, default=300.0)
    ap.add_argument("--tol-sec", type=float, default=60.0)
    a = ap.parse_args()
    demo = DEMO                                   # this slug folder's intermediate/
    slug = a.slug or json.load(open(f"{demo}/timeline.json"))["slug"]
    bdir = f"{ROOT}/provenance"                   # provenance lives IN the slug folder
    os.makedirs(bdir, exist_ok=True)

    # small provenance + the two expensive-to-regenerate artifacts
    copies = [
        (f"{demo}/timeline.json", "timeline.json"),
        (f"{demo}/sync_report.json", "sync_report.json"),
        (f"{demo}/jcut_report.json", "jcut_report.json"),
        (f"{demo}/demo.tape", "demo.tape"),
        (f"{demo}/terminal.mp4", "terminal.mp4"),
        (f"{demo}/audio/{slug}.mp3", "narration.mp3"),
        (f"{ROOT}/config.toml", "config.toml"),
        (f"{ROOT}/build.log", "build.log"),
    ]
    saved = []
    for src, name in copies:
        if os.path.exists(src):
            shutil.copy2(src, f"{bdir}/{name}")
            saved.append(name)

    # a copy of the lesson source, so the bundle reproduces the clip standalone
    ldst = f"{bdir}/lesson"
    os.makedirs(ldst, exist_ok=True)
    for f in ("lesson.py", "setup.sh"):
        if os.path.exists(f"{ROOT}/{f}"):
            shutil.copy2(f"{ROOT}/{f}", f"{ldst}/{f}")
    saved.append("lesson/")

    # recompute the 5-gate verdict and freeze it
    py = VENV if os.path.exists(VENV) else "python3"
    verdict, human = {}, ""
    try:
        r = subprocess.run([py, f"{ROOT}/src/verify_sync.py", "--slug", slug,
                            "--target-sec", str(a.target_sec), "--tol-sec", str(a.tol_sec)],
                           capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if line.startswith("VERIFY_JSON "):
                verdict = json.loads(line[len("VERIFY_JSON "):])
            elif line.startswith(f"[{slug}]"):
                human = line
        if verdict:
            json.dump(verdict, open(f"{bdir}/verify.json", "w"),
                      ensure_ascii=False, indent=2)
            saved.append("verify.json")
    except Exception as e:                                   # noqa: BLE001
        human = f"(verify_sync failed: {e})"

    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    v = verdict
    lines = [
        f"# {slug} — build provenance", "",
        f"Frozen {stamp}. A snapshot of this clip's `intermediate/` (regenerable",
        "scratch) so the finished clip stays reproducible on its own.", "",
        "## Verdict", "",
        f"`{human or 'verify not run'}`", "",
    ]
    if v:
        lines += [
            f"- structural sync: **{'OK' if v.get('structural_synced') else 'FALLBACK'}** "
            f"({v.get('detected_clears')}/{v.get('expected_scenes')} clears, {v.get('method')})",
            f"- narration fits: **{v.get('narration_fits')}** "
            f"(voice {v.get('narration_sec')}s ≤ final {v.get('final_sec')}s)",
            f"- duration: final **{v.get('final_sec')}s**",
            f"- J-cut: **{v.get('jcut_applied')}/{v.get('jcut_total')}** transitions, "
            f"mean {v.get('jcut_mean_sec')}s, {v.get('jcut_clips')} clips",
            f"- voice overruns: **{v.get('voice_overruns')}** (min gap {v.get('min_gap_sec')}s)", "",
        ]
    lines += [
        "## Files", "",
        *[f"- `{n}`" for n in saved], "",
        "## Re-render from this bundle (no vhs), from THIS folder", "",
        "```bash",
        "mkdir -p intermediate/audio",
        "cp provenance/timeline.json   intermediate/timeline.json",
        "cp provenance/terminal.mp4    intermediate/terminal.mp4",
        f"cp provenance/narration.mp3   intermediate/audio/{slug}.mp3",
        "rm -f intermediate/clears_override.json",
        f".venv/bin/python src/overlay.py            # -> ./{slug}.mp4",
        "```",
        "",
        "Full rebuild (edit lesson.py first) and handoff: see this folder's CLAUDE.md.",
    ]
    open(f"{bdir}/PROVENANCE.md", "w").write("\n".join(lines) + "\n")
    saved.append("PROVENANCE.md")
    print(f"[bundle] {slug}: wrote {len(saved)} items to {bdir}")
    print(f"[bundle] {human}")


if __name__ == "__main__":
    main()
