#!/usr/bin/env python3
"""detect_anchors.py — Phase 0: derive the ledger's HARD fields from the filmed
terminal video. Reuses the v5 detection core (signals / detect_ready /
detect_turns / dur) VERBATIM — it is the validated, stress-tested ground truth
(survives multi-turn file-writing). The NEW work is `raw_segments(...)`, which
turns each detected per-turn (typing_start, submit, done) into the alternating
SOFT/HARD segment partition the splice stage consumes, plus a `detect(...)` I/O
entry point.

Needs numpy (run with the repo venv: .venv/bin/python detect_anchors.py ...).
"""
import argparse
import json
import os
import subprocess

import numpy as np

FF = "/opt/homebrew/bin/ffmpeg"
FPS = 12.5


def dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout or 0)


def signals(video):
    """(full, input) signals per frame. `input` measures NEW brightness in the
    bottom band relative to each pixel's own baseline (its min over time), so a
    constant status line contributes nothing while the input box (dark when idle,
    bright while typing) stands out. This makes detection robust across terminal
    heights — the status line's fraction of the frame changes with height but its
    constant brightness is always cancelled."""
    sw, sh = 240, 180
    raw = subprocess.run([FF, "-i", video, "-vf",
                          f"scale={sw}:{sh},format=gray,fps={FPS}",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (sw * sh)
    f = np.frombuffer(raw, np.uint8)[:n * sw * sh].reshape(n, sh, sw).astype(np.int16)
    full = (f > 90).sum(axis=(1, 2)).astype(float)
    # AUTO-LOCATE the input line: it's the most temporally-DYNAMIC band in the
    # bottom region (typing swings its brightness hardest), while the status line
    # is near-constant and the BG baseline is uniform. So no hand-tuned band is
    # needed across font sizes / terminal heights — pick the bottom variance peak.
    rng = (f.max(axis=0) - f.min(axis=0)).mean(axis=1)          # per-row dynamic range
    lo, hi = int(0.80 * sh), int(0.95 * sh)
    peak = lo + int(np.argmax(rng[lo:hi]))
    hw = int(0.016 * sh)                                         # TIGHT: just the input box,
    r0, r1 = max(0, peak - hw), min(sh, peak + hw + 1)           # else response content leaks in
    band = f[:, r0:r1, :]
    base = band.min(axis=0, keepdims=True)            # per-pixel idle baseline
    inp = ((band - base) > 45).sum(axis=(1, 2)).astype(float)   # NEW bright pixels
    return full, inp


def detect_ready(full):
    thr = 0.3 * np.percentile(full, 90)
    for i in range(len(full)):
        if full[i] > thr and full[min(i + 3, len(full) - 1)] > thr:
            return round(i / FPS, 3)
    return 0.0


def detect_turns(full, inp, n, turns, pre_enter):
    """Detect each turn's (typing_start, submit, done) FROM THE VIDEO — the only
    reliable ground truth (VHS video time drifts from the hook wall-clock by many
    seconds during heavy output, so the timeline can't be mapped to video time).

    The discriminator for a SUBMIT is a sharp PEAK: typing fills the input box to
    near its maximum brightness, then Enter clears it. Lingering response content
    in the band sits only MODERATELY bright and never peaks; the welcome flicker
    and the idle state peak low too. So the contiguous runs where the band exceeds
    HALF its global max are exactly the N prompt submissions — this separates a
    turn's typing from the previous turn's response output, which a simpler
    above-threshold span would merge. typing_start is derived from the tape's
    known typing duration; `done` is the last big jump in full-screen content
    before the next turn."""
    fmax = float(inp.max()) or 1.0
    above = inp > 0.5 * fmax
    groups, i, N = [], 0, len(inp)
    while i < N:
        if above[i]:
            j = i
            while j < N and (above[j] or (j + 6 < N and above[j:j + 6].any())):
                j += 1                                   # tolerate <=0.5s dips
            groups.append((i, j))
            i = j
        else:
            i += 1
    if len(groups) != n:
        raise SystemExit(f"detected {len(groups)} prompt submissions, expected {n}. "
                         f"Tune the input band / thresholds, or the recording differs.")
    cmax = float(full.max()) or 1.0
    out = []
    for k, (a, b) in enumerate(groups):
        submit = round(b / FPS, 3)                       # box fullest -> Enter clears
        typing_start = round(max(0.0, submit - turns[k].get("type_dur", 1.0) - pre_enter), 3)
        nxt = (groups[k + 1][0] / FPS) if k + 1 < len(groups) else N / FPS
        last = b
        for m in range(b + 1, min(int(nxt * FPS), N)):
            if full[m] - full[m - 1] > 0.04 * cmax:      # content still growing
                last = m
        done = round(min(nxt - 0.3, last / FPS + 0.5), 3)
        out.append({"typing_start": typing_start, "submit": submit,
                    "done": max(round(submit + 0.3, 3), done)})
    return out


def raw_segments(ready, turns, vtot):
    """Partition raw-video time into MONOTONIC, non-overlapping segments. boot
    [0,ready] is the launch animation (verbatim); each turn's [typing_start,done]
    is hard (verbatim); idle gaps + tail are soft (freeze-stretchable). typing_start
    is a tape ESTIMATE (submit - type_dur - pre_enter) and can fall before `ready`
    or a previous `done`, so every boundary is clamped to the running cursor — a
    degenerate (zero-length) soft gap is allowed (splice freezes a single frame)."""
    ready = max(0.0, ready)
    segs = [{"kind": "boot", "raw": [0.0, ready], "role": "boot"}]
    cursor = ready
    for i, t in enumerate(turns):
        ts = max(t["typing_start"], cursor)          # can't type before ready/prev done
        done = max(t["done"], ts)                     # monotonic
        segs.append({"kind": "soft", "raw": [cursor, ts], "role": "pre", "turn_idx": i})
        segs.append({"kind": "hard", "raw": [ts, done], "turn_idx": i,
                     "submit": min(max(t["submit"], ts), done)})
        cursor = done
    segs.append({"kind": "soft", "raw": [cursor, max(cursor, vtot)], "role": "tail"})
    return segs


def detect(demo, video, plan):
    """I/O entry: run signals/detect on <demo>/<video>, return
    {ready, turns:[{typing_start,submit,done}], vtot, segments}. Writes nothing —
    author.py owns the ledger. Reuses the v5 detection verbatim."""
    path = os.path.join(demo, video)
    vtot = dur(path)
    full, inp = signals(path)
    ready = detect_ready(full)
    det = detect_turns(full, inp, len(plan["turns"]), plan["turns"],
                       plan.get("pre_enter", 0.4))
    return {"ready": ready, "turns": det, "vtot": round(vtot, 3),
            "segments": raw_segments(ready, det, vtot)}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", required=True, help="demo dir with terminal_raw.mp4 + capture.json")
    ap.add_argument("--video", default="terminal_raw.mp4")
    args = ap.parse_args()
    with open(os.path.join(args.demo, "capture.json")) as fh:
        plan = json.load(fh)
    out = detect(args.demo, args.video, plan)
    print(json.dumps(out["segments"], indent=2))


if __name__ == "__main__":
    main()
