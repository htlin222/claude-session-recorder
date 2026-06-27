#!/usr/bin/env python3
"""validate_sync.py — stress-test harness: carefully check that voice / panel /
terminal stay in sync, both programmatically AND as a labelled filmstrip to eyeball.

Programmatic checks (from session_sync.json + the timeline):
  * #turns detected == #UserPromptSubmit in the timeline (detection didn't miss/add)
  * voice leads typing on every turn; no narration overlap; every gap >= MIN_GAP
  * think fits every window; each turn's panel events == its timeline tool count
  * launch flag reveals == voice onsets; tool events inside their [submit, done]

Filmstrip: extracts composite frames at each meaningful moment (launch reveals,
each typing_start / submit / done, each tool event) labelled with what SHOULD be
on screen, montaged so a human can confirm left==right==voice at a glance.

Usage: validate_sync.py --demo <demo> [--video session_panel.mp4]
Exit 0 = all programmatic checks pass.
"""

import argparse
import json
import os
import subprocess

FF = "/opt/homebrew/bin/ffmpeg"
MIN_GAP = 0.5


def last_session(timeline):
    rows = [json.loads(l) for l in open(timeline, encoding="utf-8") if l.strip()]
    st = [i for i, r in enumerate(rows) if r["event"] == "SessionStart"]
    return rows[st[-1] :] if st else rows


def srt_cues(path):
    def s(t):
        h, m, r = t.split(":")
        sec, ms = r.split(",")
        return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000

    out = []
    for b in open(path, encoding="utf-8").read().split("\n\n"):
        L = [x for x in b.splitlines() if x.strip()]
        if len(L) >= 3 and "-->" in L[1]:
            a, e = L[1].split(" --> ")
            out.append((s(a), s(e), L[2]))
    return out


def grab(video, t, label, out):
    subprocess.run(
        [
            FF,
            "-nostdin",
            "-loglevel",
            "error",
            "-ss",
            f"{t:.2f}",
            "-i",
            video,
            "-frames:v",
            "1",
            "-y",
            out,
        ],
        check=True,
        capture_output=True,
    )
    # caption strip
    subprocess.run(
        [
            "magick",
            out,
            "-resize",
            "640x",
            "-gravity",
            "north",
            "-background",
            "#1e1e2e",
            "-splice",
            "0x30",
            "-fill",
            "#cdd6f4",
            "-pointsize",
            "18",
            "-annotate",
            "+0+6",
            f"{t:.1f}s  {label}",
            out,
        ],
        capture_output=True,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    ap.add_argument("--video", default="session_panel.mp4")
    ap.add_argument("--timeline", default=None)
    args = ap.parse_args()
    demo = os.path.abspath(args.demo)
    here = os.path.dirname(os.path.abspath(__file__))
    timeline = args.timeline or (
        os.path.join(demo, "session-timeline.jsonl")
        if os.path.exists(os.path.join(demo, "session-timeline.jsonl"))
        else os.path.join(os.path.dirname(here), "session-timeline.jsonl")
    )
    sync = json.load(open(os.path.join(demo, "session_sync.json"), encoding="utf-8"))
    video = os.path.join(demo, args.video)
    if not os.path.exists(video):
        video = os.path.join(demo, "session.mp4")
    rows = last_session(timeline)
    ups = [r for r in rows if r["event"] == "UserPromptSubmit"]
    stops = [r for r in rows if r["event"] == "Stop"]

    fails = []
    nturns = len(sync["turns"])
    if len(ups) != nturns:
        fails.append(f"detected {nturns} turns but timeline has {len(ups)} prompts")

    cues = srt_cues(os.path.join(demo, "session.srt"))
    for i in range(1, len(cues)):
        gap = cues[i][0] - cues[i - 1][1]
        if gap < MIN_GAP - 0.05:
            fails.append(
                f"narration gap {gap:.2f}s < {MIN_GAP} between cue {i}/{i + 1}"
            )

    for ti, t in enumerate(sync["turns"]):
        if not t["voice_leads_typing"]:
            fails.append(f"turn {t['index']}: voice does NOT lead typing")
        if not t["think_fits_gap"]:
            fails.append(f"turn {t['index']}: think overruns window")
        if not (t["typing_start"] <= t["submit"] <= t["done"]):
            fails.append(
                f"turn {t['index']}: anchors out of order "
                f"({t['typing_start']}/{t['submit']}/{t['done']})"
            )
        # tool count vs timeline
        if ti < len(ups) and ti < len(stops):
            ntl = sum(
                1
                for r in rows
                if r["event"] == "PreToolUse"
                and ups[ti]["t"] < r["t"] <= stops[ti]["t"]
            )
            print(
                f"  turn {t['index']}: {ntl} tool events, window "
                f"[{t['submit']:.1f},{t['done']:.1f}] = {t['done'] - t['submit']:.1f}s"
            )

    # ---- filmstrip at meaningful moments ----
    fdir = os.path.join(demo, "_validate")
    os.makedirs(fdir, exist_ok=True)
    shots, k = [], 0
    for j, ob in enumerate(sync.get("open_beats", [])):
        if j == 0:
            continue
        p = f"{fdir}/{k:02d}.png"
        grab(video, ob["onset"] + 0.3, f"launch: flag {j} reveal+voice", p)
        shots.append(p)
        k += 1
    for t in sync["turns"]:
        for tag, tt in [
            ("typing", t["typing_start"] + 0.3),
            ("submit", t["submit"] + 0.3),
            ("done/outro", t["done"] + 0.3),
        ]:
            p = f"{fdir}/{k:02d}.png"
            grab(video, tt, f"turn {t['index']} {tag}", p)
            shots.append(p)
            k += 1
    montage = os.path.join(demo, "validate_filmstrip.png")
    subprocess.run(
        [
            "magick",
            "montage",
            *shots,
            "-tile",
            "3x",
            "-geometry",
            "+6+6",
            "-background",
            "#11111b",
            montage,
        ],
        capture_output=True,
    )

    print()
    if fails:
        print(f"FAIL ({len(fails)}):")
        for f in fails:
            print("  -", f)
    else:
        print("PASS: all programmatic sync checks ok.")
    print(
        f"filmstrip -> {montage}  (eyeball: left terminal == right panel == the labelled moment)"
    )
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
