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

from ledger import load

FF = "/opt/homebrew/bin/ffmpeg"
FPS = 12.5


def calmest_frame(deltas):
    """Index of the frame with the least change vs its neighbour — the truly
    static frame to freeze (cursor blink flickers the input line, so never just
    take an endpoint). Ties resolve to the earliest (np.argmin)."""
    return int(np.argmin(deltas))


def plan(segments):
    """Per ledger segment -> ffmpeg op(s). HARD/BOOT copy verbatim; a BOOT whose
    out_dur exceeds its raw length gets an extra end-freeze of the remainder; SOFT
    becomes a single-frame freeze held for out_dur."""
    ops = []
    for s in segments:
        raw_len = s["raw"][1] - s["raw"][0]
        if s["kind"] in ("hard", "boot"):
            ops.append({"op": "copy", "raw": list(s["raw"])})
            if s["kind"] == "boot":
                extra = round(s.get("out_dur", raw_len) - raw_len, 3)
                if extra > 0.01:
                    ops.append({"op": "freeze", "raw": list(s["raw"]),
                                "at": "end", "out_dur": extra})
        else:  # soft
            ops.append({"op": "freeze", "raw": list(s["raw"]),
                        "out_dur": round(s.get("out_dur", raw_len), 3)})
    return ops


def _probe_dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout or 0)


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


def _seg_file(video, op, idx, outdir, w, h):
    """Produce one segment mp4. Copy ops are re-encoded (frame-accurate cut +
    uniform codec/size); freeze ops extract one frame and hold it for out_dur.
    All segments share codec/pix_fmt/fps/size so the concat demuxer can -c copy."""
    seg = os.path.join(outdir, f"seg_{idx:03d}.mp4")
    if op["op"] == "copy":
        a, b = op["raw"]
        subprocess.run(
            [FF, "-ss", f"{a}", "-to", f"{b}", "-i", video, "-an",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", f"{FPS}",
             "-vf", f"scale={w}:{h}", "-y", seg],
            capture_output=True, check=True)
        return seg
    # freeze: choose the source frame to hold
    if op.get("at") == "end":
        src = round(op["raw"][1] - 1.0 / FPS, 3)        # boot's last static frame
    else:
        src = _calm_time(video, op["raw"][0], op["raw"][1])
    png = os.path.join(outdir, f"frame_{idx:03d}.png")
    subprocess.run(
        [FF, "-ss", f"{src}", "-i", video, "-frames:v", "1", "-y", png],
        capture_output=True, check=True)
    subprocess.run(
        [FF, "-loop", "1", "-t", f"{op['out_dur']}", "-i", png, "-an",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", f"{FPS}",
         "-vf", f"scale={w}:{h}", "-y", seg],
        capture_output=True, check=True)
    return seg


def splice(demo, raw="terminal_raw.mp4", out="terminal.mp4"):
    """Re-time terminal_raw.mp4 to the ledger's segment lengths -> terminal.mp4."""
    led = load(os.path.join(demo, "ledger.json"))
    segs = led["meta"]["segments"]
    video = os.path.join(demo, raw)
    w, h = _probe_wh(video)
    ops = plan(segs)

    outdir = os.path.join(demo, "_splice")
    os.makedirs(outdir, exist_ok=True)
    files = [_seg_file(video, op, i, outdir, w, h) for i, op in enumerate(ops)]

    listf = os.path.join(outdir, "list.txt")
    with open(listf, "w", encoding="utf-8") as f:
        for p in files:
            f.write(f"file '{os.path.abspath(p)}'\n")
    out_path = os.path.join(demo, out)
    subprocess.run(
        [FF, "-f", "concat", "-safe", "0", "-i", listf, "-c", "copy",
         "-y", out_path], capture_output=True, check=True)

    realized = _probe_dur(out_path)
    want = led["meta"].get("vtot_out")
    if want is not None and abs(realized - want) > 0.3:
        print(f"WARNING: realized {realized:.3f}s vs planned {want:.3f}s "
              f"(off by {realized - want:+.3f}s)")
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
