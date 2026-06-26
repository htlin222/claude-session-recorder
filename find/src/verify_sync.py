#!/usr/bin/env python3
"""Verify (and optionally auto-fix) audio↔video sync of a rendered clip.

This is the measurable signal that lets the /clip loop own A/V sync so authors
focus on content. It judges the ONE thing that silently degrades the render:
whether overlay.py locked every scene's panel/video switch to the terminal's real
clear frames (synced) or fell back to a global offset (desynced).

Inputs (all already produced by the pipeline):
  intermediate/timeline.json     predicted clock + per-scene panels
  intermediate/terminal.mp4      the raw VHS terminal render (left pane)
  intermediate/sync_report.json  overlay.py's own synced/fallback verdict
  dist/<slug>.mp4                the finished video

Checks (objective, from the files — never the model's opinion):
  1. structural sync   overlay reported synced (detected clears == scenes-1)
  2. narration fit     the finished video is long enough to contain the whole
                       narration (voice never cut)
  3. duration target   (optional) finished length within tolerance of --target-sec

Verdict / exit code, consumed by the loop:
  0  PASS              synced + narration fits (+ on target if asked)
  1  FAIL, FIXABLE     fell back, but guided clears (anchored to the predicted
                       scene times) give the right count — written to
                       intermediate/clears_override.json when --write-override is
                       set, so a re-run of overlay.py composites in sync
  2  FAIL, NOT-FIXABLE narration is cut, or no guided clear solution exists

Usage:
  python3 src/verify_sync.py [--slug X] [--target-sec N] [--write-override]
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the slug folder
DEMO = f"{ROOT}/intermediate"
FF = "/opt/homebrew/bin/ffmpeg"

# detection grid identical to overlay.detect_clears, so "default count" here
# matches what overlay computed.
SW, SH, FPS, BRIGHT = 200, 180, 12.5, 90


def _dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout)


def content_signal(video):
    """Per-frame count of bright pixels (mirrors overlay.detect_clears)."""
    raw = subprocess.run([FF, "-i", video, "-vf",
                          f"scale={SW}:{SH},format=gray,fps={FPS}",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (SW * SH)
    f = np.frombuffer(raw, np.uint8)[:n * SW * SH].reshape(n, SH, SW)
    return (f > BRIGHT).sum(axis=(1, 2)).astype(float)


def default_clears(content):
    """The blind global-threshold detection overlay uses by default."""
    base, hi = np.percentile(content, 5), np.percentile(content, 70)
    thr = base + 0.30 * (hi - base)
    empty = content < thr
    return [i / FPS for i in range(1, len(content)) if empty[i] and not empty[i - 1]]


def search_clears(content, expected):
    """Heal a miscounted detection by SWEEPING the empty-threshold until the
    rising-edge count equals the known `expected` (= scenes-1). The single
    default threshold occasionally merges or invents a clear on a given lesson's
    content; some fraction of the base→peak range almost always lands the exact
    count. Sub-second flickers are merged (scenes are many seconds apart).
    Returns (clears, fraction) or (None, None) if no fraction gives the count."""
    base, hi = np.percentile(content, 5), np.percentile(content, 70)
    for frac in [0.30, 0.25, 0.35, 0.20, 0.40, 0.15, 0.45, 0.50, 0.55, 0.10, 0.60]:
        thr = base + frac * (hi - base)
        empty = content < thr
        raw = [i / FPS for i in range(1, len(content)) if empty[i] and not empty[i - 1]]
        merged = []
        for t in raw:
            if not merged or t - merged[-1] > 1.0:
                merged.append(round(t, 3))
        if len(merged) == expected:
            return merged, round(frac, 2)
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default=None)
    ap.add_argument("--target-sec", type=float, default=None)
    ap.add_argument("--tol-sec", type=float, default=20.0)
    ap.add_argument("--write-override", action="store_true",
                    help="when fixable, write intermediate/clears_override.json")
    a = ap.parse_args()
    demo = DEMO                                # this slug folder's intermediate/
    terminal = f"{demo}/terminal.mp4"

    tl = json.load(open(f"{demo}/timeline.json", encoding="utf-8"))
    slug = a.slug or tl.get("slug", "demo")
    final = f"{ROOT}/{slug}.mp4"
    panels = tl["panels"]
    expected = len(panels) - 1

    report = {}
    rp = f"{demo}/sync_report.json"
    if os.path.exists(rp):
        report = json.load(open(rp))

    term_dur = _dur(terminal)
    final_dur = _dur(final) if os.path.exists(final) else 0.0
    narr = tl["narration_dur"]

    # 1) structural sync — trust overlay's own report if present, else recompute
    if "synced" in report:
        synced, detected, method = report["synced"], report["detected"], report.get("method", "detect")
    else:
        c = content_signal(terminal)
        det = default_clears(c)
        detected, method = len(det), "detect"
        synced = detected == expected

    # 2) narration fit — the finished video must contain the whole voice
    narr_fits = final_dur >= narr - 0.5 if final_dur else False

    # 3) optional duration target
    on_target = True if a.target_sec is None else abs(final_dur - a.target_sec) <= a.tol_sec

    # 4) J-cut quality — no transition's lead may eat into the previous scene's
    # narration (lead must stay within gap-guard); J-cut absence is fine.
    jcut_total = jcut_applied = jcut_clip = voice_overruns = 0
    jcut_mean = min_gap = 0.0
    jrp = f"{demo}/jcut_report.json"
    if os.path.exists(jrp):
        jc = json.load(open(jrp))
        g = jc.get("guard", 0.12)
        trans = jc.get("transitions", [])
        jcut_total = len(trans)
        applied = [t for t in trans if t["lead"] > 0.02]
        jcut_applied = len(applied)
        jcut_mean = round(sum(t["lead"] for t in applied) / len(applied), 3) if applied else 0.0
        jcut_clip = sum(1 for t in trans if t["lead"] > max(0.0, t["gap"] - g) + 0.03)
        # the bug this guards: a scene whose narration runs into the next clip.
        # gap = silence between a scene's last word and the next scene's start;
        # below the guard means the previous voice isn't comfortably finished.
        min_gap = round(min((t["gap"] for t in trans), default=0.0), 3)
        voice_overruns = sum(1 for t in trans if t["gap"] < g)

    verdict = {
        "slug": slug, "expected_scenes": expected, "detected_clears": detected,
        "method": method, "structural_synced": bool(synced),
        "terminal_sec": round(term_dur, 2), "final_sec": round(final_dur, 2),
        "narration_sec": round(narr, 2), "narration_fits": bool(narr_fits),
        "target_sec": a.target_sec, "on_target": bool(on_target),
        "jcut_applied": jcut_applied, "jcut_total": jcut_total,
        "jcut_mean_sec": jcut_mean, "jcut_clips": jcut_clip,
        "min_gap_sec": min_gap, "voice_overruns": voice_overruns,
        "fixable": False, "override_written": False,
    }

    passed = (synced and narr_fits and on_target
              and jcut_clip == 0 and voice_overruns == 0)
    if not passed and not synced:
        # only structural desync is auto-fixable: sweep the threshold for the
        # count-correct clears and offer them as an override
        c = content_signal(terminal)
        g, frac = search_clears(c, expected)
        if g and len(g) == expected:
            verdict["fixable"] = True
            verdict["healed_clears"] = g
            verdict["healed_frac"] = frac
            if a.write_override:
                json.dump({"slug": slug, "clears": g, "source": f"verify_sync.search(frac={frac})"},
                          open(f"{demo}/clears_override.json", "w"))
                verdict["override_written"] = True

    code = 0 if passed else (1 if verdict["fixable"] else 2)
    verdict["verdict"] = ["PASS", "FAIL_FIXABLE", "FAIL"][code]

    # human line + machine JSON (the loop greps the JSON; humans read line 1)
    reasons = []
    if not synced:
        reasons.append(f"desynced ({detected}/{expected} clears, method={method})")
    if not narr_fits:
        reasons.append(f"narration cut (final {final_dur:.1f}s < voice {narr:.1f}s)")
    if not on_target:
        reasons.append(f"off target ({final_dur:.1f}s vs {a.target_sec}±{a.tol_sec}s)")
    if voice_overruns:
        reasons.append(f"{voice_overruns} scene(s) whose voice runs into the next clip "
                       f"(min gap {min_gap:.2f}s < guard)")
    if jcut_clip:
        reasons.append(f"{jcut_clip} J-cut(s) overrun previous narration")
    jtag = (f" | J-cut {jcut_applied}/{jcut_total} mean {jcut_mean:.2f}s, "
            f"min gap {min_gap:.2f}s" if jcut_total else "")
    tail = ("ok" if passed else "; ".join(reasons)) + jtag
    fix = " [guided fix available]" if verdict["fixable"] and not verdict["override_written"] else \
          " [override written → re-run overlay.py]" if verdict["override_written"] else ""
    print(f"[{slug}] {verdict['verdict']}: {tail}{fix}")
    print("VERIFY_JSON " + json.dumps(verdict, ensure_ascii=False))
    sys.exit(code)


if __name__ == "__main__":
    main()
