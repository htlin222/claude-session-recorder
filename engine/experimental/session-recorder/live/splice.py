#!/usr/bin/env python3
"""splice.py — Phase 2 core: freeze-frame re-time the SOFT segments of
terminal_raw.mp4 to their authored lengths; copy HARD/BOOT segments verbatim
(boot freeze-EXTENDED at its static tail if the launch voice needs longer);
concat -> terminal.mp4. Output lengths come from the ledger, so downstream never
re-detects. See docs/plans/2026-06-28-event-ledger-deterministic-pipeline-design.md."""
import argparse
import os
import subprocess

import numpy as np

from ledger import load, save
from strategies import strategy_for

FF = "/opt/homebrew/bin/ffmpeg"
FPS = 12.5


def calmest_frame(deltas):
    """Index of the frame with the least change vs its neighbour — the truly
    static frame to freeze (cursor blink flickers the input line, so never just
    take an endpoint). Ties resolve to the earliest (np.argmin)."""
    return int(np.argmin(deltas))


def _beat_anchor(beat):
    """Earliest present output-time anchor of a beat — min over voice.start,
    visual.start, panel.switch_at (a beat sits within one planned segment)."""
    anchors = []
    v = beat.get("voice")
    if v and "start" in v:
        anchors.append(v["start"])
    vis = beat.get("visual")
    if vis and "start" in vis:
        anchors.append(vis["start"])
    p = beat.get("panel")
    if p and "switch_at" in p:
        anchors.append(p["switch_at"])
    return min(anchors) if anchors else 0.0


def reconcile(led, realized_durs):
    """Rewrite the ledger's segment out-windows and beat times to the ACTUAL
    spliced durations (each re-encoded segment may realize a few frames longer
    than planned). Each beat sits within one planned segment; shift all of its
    times by that segment's planned->realized START delta (content sits at the
    segment front; a freeze just holds longer at the back, so offset-from-start
    is preserved). Mutates and returns `led`."""
    segs = led["meta"]["segments"]
    # capture PLANNED windows BEFORE overwriting (match beats by these)
    planned = [(s["out"][0], s["out"][1]) for s in segs]
    # realized cumulative out-windows
    cur = 0.0
    for s, d in zip(segs, realized_durs):
        s["out"] = [round(cur, 3), round(cur + d, 3)]
        s["out_dur"] = round(d, 3)
        cur += d
    led["meta"]["vtot_out"] = round(cur, 3)

    def host_shift(anchor):
        for (p0, p1), s in zip(planned, segs):
            if p0 <= anchor < p1:
                return s["out"][0] - p0
        # anchor at/after the last planned window -> last segment
        return segs[-1]["out"][0] - planned[-1][0]

    for b in led.get("beats", []):
        shift = host_shift(_beat_anchor(b))
        if not shift:
            continue
        v = b.get("voice")
        if v:
            if "start" in v:
                v["start"] = round(v["start"] + shift, 3)
            if "end" in v:
                v["end"] = round(v["end"] + shift, 3)
        vis = b.get("visual")
        if vis:
            if "start" in vis:
                vis["start"] = round(vis["start"] + shift, 3)
            if "end" in vis:
                vis["end"] = round(vis["end"] + shift, 3)
        p = b.get("panel")
        if p and "switch_at" in p:
            p["switch_at"] = round(p["switch_at"] + shift, 3)
    return led


def plan(segments):
    """Per ledger segment -> ffmpeg op(s), dispatched through the SegmentStrategy
    registry (strategies.py). HARD/BOOT copy verbatim (BOOT end-freezes any
    out_dur beyond its captured length); SOFT freezes one static frame for out_dur."""
    ops = []
    for s in segments:
        ops.extend(strategy_for(s).splice_ops(s))
    return ops


def _probe_dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout or 0)


def _probe_fps(video):
    """Raw video's real frame rate (e.g. 25/1 -> 25.0). Used as the OUTPUT encode
    fps so copied hard segments keep every frame and rounding stays minimal."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=r_frame_rate", "-of", "csv=p=0", video],
        capture_output=True, text=True, check=True).stdout.strip()
    if "/" in out:
        num, den = out.split("/")
        den = float(den) or 1.0
        return float(num) / den
    return float(out) if out else FPS


def _probe_wh(video):
    """Raw video's (width, height) so every re-encoded segment matches and the
    concat demuxer's stream-copy stays valid."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", video],
        capture_output=True, text=True, check=True).stdout.strip()
    w, h = out.split("x")
    return int(w), int(h)


def _calm_time(video, a, b):
    """Read the raw range [a,b] as small grayscale frames, compute each frame's
    mean-abs-diff vs the previous frame, and return the absolute source time of
    the calmest frame — the static frame safe to freeze."""
    if b - a < 1.5 / FPS:                 # degenerate (zero-length) soft window:
        return round(a, 3)                # source the single frame at `a`
    sw, sh = 240, 135
    raw = subprocess.run(
        [FF, "-ss", f"{a}", "-to", f"{b}", "-i", video, "-vf",
         f"scale={sw}:{sh},format=gray,fps={FPS}", "-f", "rawvideo", "-"],
        capture_output=True).stdout
    n = len(raw) // (sw * sh)
    if n <= 0:
        return a
    f = np.frombuffer(raw, np.uint8)[:n * sw * sh].reshape(
        n, sh, sw).astype(np.int16)
    # per-frame change vs previous; frame 0 has no predecessor -> large so it is
    # never chosen as "calmest".
    deltas = np.empty(n, dtype=float)
    deltas[0] = 1e9
    if n > 1:
        deltas[1:] = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    return round(a + calmest_frame(deltas) / FPS, 3)


def _seg_file(video, op, idx, outdir, w, h, fps=FPS):
    """Produce one segment mp4. Copy ops are re-encoded (frame-accurate cut +
    uniform codec/size); freeze ops extract one frame and hold it for out_dur.
    All segments share codec/pix_fmt/fps/size so the concat demuxer can -c copy.
    `fps` is the SOURCE frame rate so copied hard segments keep every frame."""
    seg = os.path.join(outdir, f"seg_{idx:03d}.mp4")
    if op["op"] == "copy":
        a, b = op["raw"]
        subprocess.run(
            [FF, "-ss", f"{a}", "-to", f"{b}", "-i", video, "-an",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", f"{fps}",
             "-vf", f"scale={w}:{h}", "-y", seg],
            capture_output=True, check=True)
        return seg
    # freeze: choose the source frame to hold
    if op.get("at") == "end":
        src = round(op["raw"][1] - 1.0 / fps, 3)        # boot's last static frame
    elif op.get("freeze_from") == "start":
        # tail: hold the FINAL settled result. The capture's DONE_HOLD keeps
        # claude's finished result (its final message + the VHS_TURN_DONE line) on
        # screen, STABLE, for ~3s right before the brief Ctrl+C teardown. Source
        # the calmest frame in THAT end window (not the whole tail — earlier the
        # tail also contains the mid-run "Running…/Drizzling/Burrowing" spinner,
        # which has its own near-static moments that a whole-tail search can wrongly
        # pick). The DONE_HOLD window at the end is the only place the FINAL result
        # is guaranteed shown + stable.
        a, b = op["raw"]
        teardown, hold = 0.8, 2.4
        hi = max(a + 1.0 / fps, b - teardown)
        lo = max(a, hi - hold)
        src = _calm_time(video, lo, hi)
    else:
        src = _calm_time(video, op["raw"][0], op["raw"][1])
    png = os.path.join(outdir, f"frame_{idx:03d}.png")
    subprocess.run(
        [FF, "-ss", f"{src}", "-i", video, "-frames:v", "1", "-y", png],
        capture_output=True, check=True)
    subprocess.run(
        [FF, "-loop", "1", "-t", f"{op['out_dur']}", "-i", png, "-an",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", f"{fps}",
         "-vf", f"scale={w}:{h}", "-y", seg],
        capture_output=True, check=True)
    return seg


def splice(demo, raw="terminal_raw.mp4", out="terminal.mp4"):
    """Re-time terminal_raw.mp4 to the ledger's segment lengths -> terminal.mp4."""
    led_path = os.path.join(demo, "ledger.json")
    led = load(led_path)
    segs = led["meta"]["segments"]
    video = os.path.join(demo, raw)
    w, h = _probe_wh(video)
    fps = _probe_fps(video)                     # output at SOURCE fps (B1)
    ops = plan(segs)

    outdir = os.path.join(demo, "_splice")
    os.makedirs(outdir, exist_ok=True)
    files = [_seg_file(video, op, i, outdir, w, h, fps)
             for i, op in enumerate(ops)]

    listf = os.path.join(outdir, "list.txt")
    with open(listf, "w", encoding="utf-8") as f:
        for p in files:
            f.write(f"file '{os.path.abspath(p)}'\n")
    out_path = os.path.join(demo, out)
    subprocess.run(
        [FF, "-f", "concat", "-safe", "0", "-i", listf, "-c", "copy",
         "-y", out_path], capture_output=True, check=True)

    # B2: RECONCILE the ledger to the realized per-segment durations, then save so
    # downstream (overlay/panel) reads the timeline the video ACTUALLY has. A copy
    # op and its boot end-freeze belong to the SAME ledger segment, so realized
    # durations are accumulated back per segment (one ledger seg -> 1..2 op files).
    planned_want = led["meta"].get("vtot_out")
    realized_durs, oi = [], 0
    for s in segs:
        n_ops = 2 if (s["kind"] == "boot"
                      and round(s.get("out_dur", 0.0)
                                - (s["raw"][1] - s["raw"][0]), 3) > 0.01) else 1
        realized_durs.append(sum(_probe_dur(files[oi + k]) for k in range(n_ops)))
        oi += n_ops
    reconcile(led, realized_durs)
    save(led_path, led)

    realized = _probe_dur(out_path)
    want = led["meta"].get("vtot_out")          # now == realized after reconcile
    if want is not None and abs(realized - want) > 0.3:
        print(f"WARNING: realized {realized:.3f}s vs reconciled {want:.3f}s "
              f"(off by {realized - want:+.3f}s)")
    if planned_want is not None:
        print(f"splice: reconciled ledger {planned_want:.3f}s -> {want:.3f}s")
    print(f"splice: {len(ops)} segments -> {realized:.3f}s ({out_path})")
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", required=True)
    ap.add_argument("--video", default="terminal_raw.mp4")
    args = ap.parse_args()
    splice(args.demo, raw=args.video)


if __name__ == "__main__":
    main()
