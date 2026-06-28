#!/usr/bin/env python3
"""overlay.py — Phase 3: mux the narration onto the spliced video FROM THE LEDGER.

NO detection here. splice already RECONCILED the ledger's voice.start times to
match terminal.mp4 exactly (output time == video time), so each voice clip is
dropped onto the audio track at its ledger onset and the result is frame-accurate.
This is a thin wrapper: load ledger.json, write session.srt, amix every voiced,
non-dropped beat at voice.start over terminal.mp4 -> session.mp4. The detection /
fitting that v5's session_overlay.py did now lives in detect_anchors + author.

See docs/plans/2026-06-28-event-ledger-deterministic-pipeline-design.md.
"""
import argparse
import os
import subprocess

from ledger import load

FF = "/opt/homebrew/bin/ffmpeg"


def srt_ts(s):
    h = int(s // 3600); s -= h * 3600
    m = int(s // 60); s -= m * 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def _voiced(beats):
    """The non-dropped, voiced beats ordered by their voice onset — the muxable
    cues. Everything downstream (srt + amix) walks this same ordered list so the
    cue numbers and the audio inputs agree."""
    return sorted((b for b in beats if not b.get("drop") and b.get("voice")),
                  key=lambda b: b["voice"]["start"])


def build_srt(beats):
    """Pure: numbered SRT cues straight from each voiced beat's ledger window
    (voice.start --> voice.end, beat.text), ordered by onset. Dropped / unvoiced
    beats produce no cue."""
    lines = []
    for k, b in enumerate(_voiced(beats), 1):
        v = b["voice"]
        lines.append(f"{k}\n{srt_ts(v['start'])} --> {srt_ts(v['end'])}\n"
                     f"{b.get('text', '')}\n")
    return "\n".join(lines) + ("\n" if lines else "")


def _vdur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout or 0)


def mux(demo, video="terminal.mp4", out="session.mp4"):
    """Mux every voiced, non-dropped beat at its ledger onset over `video`,
    writing session.srt and session.mp4. Returns the cue count."""
    demo = os.path.abspath(demo)
    led = load(os.path.join(demo, "ledger.json"))
    cues = _voiced(led["beats"])
    vpath = os.path.join(demo, video)
    vtot = _vdur(vpath)

    srt = os.path.join(demo, "session.srt")
    with open(srt, "w", encoding="utf-8") as f:
        f.write(build_srt(led["beats"]))

    # ffmpeg input 0 is the VIDEO; voice clip j is input j+1, adelay'd to its
    # onset then amixed, padded/trimmed to the exact video duration (v5 chain).
    inputs, filt, labs = [], [], []
    for j, b in enumerate(cues):
        onset, clip = b["voice"]["start"], b["voice"]["clip"]
        inputs += ["-i", os.path.join(demo, clip)]
        dms = int(round(max(0.0, onset) * 1000))
        filt.append(f"[{j+1}:a]adelay={dms}|{dms}[s{j}]")
        labs.append(f"[s{j}]")
    fc = ";".join(filt) + ";" + "".join(labs) + \
        f"amix=inputs={len(cues)}:normalize=0:dropout_transition=0," \
        f"apad=whole_dur={vtot:.3f},atrim=end={vtot:.3f}[a]"
    outpath = os.path.join(demo, out)
    subprocess.run([FF, "-y", "-i", vpath, *inputs, "-filter_complex", fc,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", outpath],
                   check=True, capture_output=True)
    return len(cues)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", required=True, help="demo dir with terminal.mp4 + ledger.json")
    ap.add_argument("--video", default="terminal.mp4")
    args = ap.parse_args()
    demo = os.path.abspath(args.demo)
    n = mux(demo, args.video)
    print(f"wrote {os.path.join(demo, 'session.mp4')}  ({n} cues)")
    print(f"wrote {os.path.join(demo, 'session.srt')}")


if __name__ == "__main__":
    main()
