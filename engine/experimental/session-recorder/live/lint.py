#!/usr/bin/env python3
"""lint.py — Phase 3: deterministic gate over the finalized ledger. The timeline
is COMPUTED (splice reconciled it to the video), so failures are AUTHORING errors,
not detection noise. Exit 0 PASS / 1 FAIL. See the design doc."""
import argparse
import os
import subprocess

from ledger import load, serialization_violations

FF = "/opt/homebrew/bin/ffmpeg"


def check(led):
    beats = led["beats"]
    violations = []
    for s in serialization_violations(beats):
        violations.append(f"serialization: {s['prev']}->{s['next']} gap {s['gap']}s")
    for b in beats:
        if b.get("drop"):
            if b.get("tier") == 1:
                violations.append(f"tier-1 beat {b['id']} ({b['kind']}) was dropped — "
                                  f"the spine must never drop")
            continue
        v, vis = b.get("voice"), b.get("visual")
        if b["mode"] == "lead" and v and vis and v["end"] > vis["start"] + 0.05:
            violations.append(f"lead beat {b['id']}: voice does not lead "
                              f"(voice.end {v['end']} > visual.start {vis['start']})")
        if b["mode"] == "ride" and v and vis and (
                v["start"] < vis["start"] - 0.05 or v["end"] > vis["end"] + 0.05):
            violations.append(f"ride beat {b['id']}: voice not contained in visual "
                              f"[{vis['start']},{vis['end']}]")
        if vis and vis["start"] > vis["end"] + 0.001:
            violations.append(f"beat {b['id']}: visual anchors out of order")
    return {"ok": not violations, "violations": violations}


def _grab(video, t, label, out):
    """Single composite frame at t, captioned with the beat label (v5 grab())."""
    subprocess.run(
        [FF, "-nostdin", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", video,
         "-frames:v", "1", "-y", out],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["magick", out, "-resize", "640x", "-gravity", "north",
         "-background", "#1e1e2e", "-splice", "0x30", "-fill", "#cdd6f4",
         "-pointsize", "18", "-annotate", "+0+6", f"{t:.1f}s  {label}", out],
        capture_output=True,
    )


def _filmstrip(demo, led):
    """Best-effort eyeball montage: one captioned frame per non-dropped beat at
    its panel switch (fallback voice.start), montaged to lint_filmstrip.png. Never
    fails the lint — the programmatic check() is the gate."""
    try:
        video = os.path.join(demo, "session_panel.mp4")
        if not os.path.exists(video):
            video = os.path.join(demo, "session.mp4")
        if not os.path.exists(video):
            print("note: no session_panel.mp4 / session.mp4 — skipping filmstrip.")
            return
        fdir = os.path.join(demo, "_lint")
        os.makedirs(fdir, exist_ok=True)
        shots, k = [], 0
        for b in led["beats"]:
            if b.get("drop"):
                continue
            panel = b.get("panel") or {}
            voice = b.get("voice") or {}
            t = panel.get("switch_at")
            if t is None:
                t = voice.get("start", 0.0)
            text = (b.get("text") or "").replace("\n", " ")[:48]
            label = f"{b.get('kind', '?')}: {text}".strip()
            p = os.path.join(fdir, f"{k:02d}.png")
            _grab(video, float(t) + 0.3, label, p)
            shots.append(p)
            k += 1
        if not shots:
            print("note: no beats to montage — skipping filmstrip.")
            return
        montage = os.path.join(demo, "lint_filmstrip.png")
        subprocess.run(
            ["magick", "montage", *shots, "-tile", "3x", "-geometry", "+6+6",
             "-background", "#11111b", montage],
            capture_output=True,
        )
        print(f"filmstrip -> {montage}  (eyeball: frame == the beat's labelled moment)")
    except Exception as e:  # best-effort: ffmpeg/magick hiccup must not fail lint
        print(f"note: filmstrip skipped ({e}).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    ap.add_argument("--filmstrip", action="store_true",
                    help="also extract an eyeball montage from session_panel.mp4")
    args = ap.parse_args()
    demo = os.path.abspath(args.demo)
    led = load(os.path.join(demo, "ledger.json"))
    report = check(led)
    for v in report["violations"]:
        print("  FAIL:", v)
    if report["ok"]:
        print("PASS: ledger satisfies the serialization invariant + all internal relations.")
    else:
        print(f"\nFAIL ({len(report['violations'])} violation(s)).")
    if args.filmstrip:
        _filmstrip(demo, led)
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
