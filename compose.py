#!/usr/bin/env python3
"""Lock the one continuous narration to the rendered video.

The tape places every on-screen action at a sentence timestamp on the
*predicted* clock. VHS's real clock drifts a little (typing), so we measure the
real render length, compute scale = real/predicted, and atempo-nudge the single
narration by 1/scale so its sentence boundaries land on the real action frames.
Subtitles (built from the same cues) get the same scale, so voice + subs + video
all share one clock. Subtitles are burned afterwards by burn_png.py."""
import json
import subprocess

import os
DEMO = os.path.dirname(os.path.abspath(__file__))
VIDEO = f"{DEMO}/rsync-demo.mp4"
AV = f"{DEMO}/_av.mp4"


def srt_ts(s):
    h = int(s // 3600); s -= h * 3600
    m = int(s // 60); s -= m * 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s-int(s))*1000)):03d}"


def main():
    tl = json.load(open(f"{DEMO}/timeline.json", encoding="utf-8"))
    real = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", VIDEO], capture_output=True, text=True).stdout)
    scale = real / tl["predicted_total"]
    tempo = 1 / scale
    anchor = tl["anchor"] * scale
    print(f"real={real:.1f}s predicted={tl['predicted_total']:.1f}s "
          f"-> scale={scale:.3f}, atempo={tempo:.3f}, anchor={anchor:.2f}s")

    # subtitles share the (scaled) narration clock
    out, n = [], 0
    for a, b, txt in tl["cues"]:
        n += 1
        st = (tl["anchor"] + a) * scale
        en = (tl["anchor"] + b) * scale
        out.append(f"{n}\n{srt_ts(st)} --> {srt_ts(en)}\n{txt}\n")
    open(f"{DEMO}/subs.srt", "w", encoding="utf-8").write("\n".join(out))

    # atempo-stretch the single narration to the real clock, delay to anchor,
    # mux onto the untouched video (subtitles added later by burn_png.py)
    d = int(anchor * 1000)
    subprocess.run(
        ["ffmpeg", "-y", "-i", VIDEO, "-i", tl["mp3"],
         "-filter_complex", f"[1]atempo={tempo:.5f},adelay={d}:all=1[a]",
         "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", AV],
        check=True)
    print(f"wrote {AV} (run burn_png.py for subtitles)")


if __name__ == "__main__":
    main()
