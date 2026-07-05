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
import re
import subprocess
import unicodedata

from ledger import load

FF = "/opt/homebrew/bin/ffmpeg"

# chunk_cues() defaults: a cue's rendered width budget (CJK/fullwidth chars
# count as 2, ASCII as 1 — see cjk_width) and the floor on how short any one
# cue's on-screen duration may be, so a fast reader never sees a sub-cue flash
# by faster than it can be read.
MAX_CUE_UNITS = 34
MIN_CUE_DUR = 1.2

_SENTENCE_RE = re.compile(r"[^。！？]+[。！？]?")
_CLAUSE_RE = re.compile(r"[^，、,]+[，、,]?")


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


def cjk_width(text):
    """Rendered subtitle width: East-Asian Wide/Fullwidth characters (CJK
    ideographs, kana, hangul, fullwidth punctuation) count as 2 units, every
    other character (ASCII letters, digits, half-width punctuation) as 1."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
               for ch in text)


def _split_by(regex, text):
    return [m.group(0) for m in regex.finditer(text) if m.group(0)]


def _hard_wrap(text, max_units):
    """Last-resort split for a clause that has no 。！？，、, punctuation at
    all to break on (e.g. a long run of plain English): cut purely by
    rendered width so no cue is left over budget."""
    chunks, cur, w = [], [], 0
    for ch in text:
        cw = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if cur and w + cw > max_units:
            chunks.append("".join(cur))
            cur, w = [], 0
        cur.append(ch)
        w += cw
    if cur:
        chunks.append("".join(cur))
    return chunks


def split_on_punctuation(text, max_units=MAX_CUE_UNITS):
    """Split `text` into readable sub-cue strings, each targeting <= max_units
    of rendered width. Splits on sentence punctuation (。！？) first; any
    resulting sentence still over budget is split further on clause
    punctuation (，、,); a clause still over budget with no punctuation at all
    falls back to a hard width-based wrap. Concatenating the returned chunks
    always reproduces `text` exactly — no characters are dropped or added."""
    if not text:
        return []
    chunks = []
    for sentence in _split_by(_SENTENCE_RE, text):
        if cjk_width(sentence) <= max_units:
            chunks.append(sentence)
            continue
        for clause in _split_by(_CLAUSE_RE, sentence):
            if cjk_width(clause) <= max_units:
                chunks.append(clause)
            else:
                chunks.extend(_hard_wrap(clause, max_units))
    return chunks


def _merge_short_chunks(chunks, dur_total, min_dur):
    """Merge-back rule for the trailing-fragment edge case: splitting on
    punctuation is width-aware but duration-blind, so a short window can end
    up with a chunk whose proportional share of dur_total would fall below
    min_dur (a cue that flashes by unreadably fast). Repeatedly fold the
    first offending chunk into its neighbour (the next chunk, or — if it's
    the last one — its predecessor, so a short trailing fragment reads as
    part of the clause before it) and recompute, until every remaining
    chunk's proportional share clears min_dur or only one chunk is left.
    This can leave a merged chunk over max_units — a floor on reading time
    trumps the char-count budget, since a too-long-but-legible cue beats an
    unreadably brief flash of text."""
    items = list(chunks)
    while len(items) > 1:
        weights = [cjk_width(c) for c in items]
        total_w = sum(weights) or 1
        durs = [dur_total * w / total_w for w in weights]
        i = next((idx for idx, d in enumerate(durs) if d < min_dur), None)
        if i is None:
            break
        if i == len(items) - 1:
            items[i - 1] = items[i - 1] + items[i]
            items.pop(i)
        else:
            items[i] = items[i] + items[i + 1]
            items.pop(i + 1)
    return items


def chunk_cues(text, start, end, max_units=MAX_CUE_UNITS, min_dur=MIN_CUE_DUR):
    """Split `text` into readable sub-cues, redistributing the FIXED
    [start, end] voice window proportionally by rendered char-width (see
    cjk_width) — the total duration is preserved exactly (the last sub-cue's
    end is pinned to `end` to absorb any rounding drift). A short beat whose
    text doesn't need splitting collapses back to a single cue spanning the
    whole window, unchanged from the old one-cue-per-beat behaviour."""
    text = text or ""
    dur_total = end - start
    if dur_total <= 0:
        return [(start, end, text)]

    chunks = split_on_punctuation(text, max_units) or [text]
    chunks = _merge_short_chunks(chunks, dur_total, min_dur)

    weights = [cjk_width(c) for c in chunks]
    total_w = sum(weights) or 1
    cues, t = [], start
    for c, w in zip(chunks, weights):
        dur = dur_total * w / total_w
        cues.append([t, t + dur, c])
        t += dur
    cues[-1][1] = end
    return [tuple(c) for c in cues]


def build_srt(beats):
    """Pure: numbered SRT cues from each voiced beat's ledger window
    (voice.start --> voice.end, beat.text), ordered by onset. Long beats are
    re-sliced into multiple readable sub-cues by chunk_cues() within that
    SAME fixed window (the window itself never moves — only the caption
    layer inside it is re-cut); cue numbers are renumbered across the WHOLE
    file, not restarted per beat. Dropped / unvoiced beats produce no cue."""
    lines, k = [], 0
    for b in _voiced(beats):
        v = b["voice"]
        for start, end, chunk in chunk_cues(b.get("text", ""), v["start"], v["end"]):
            k += 1
            lines.append(f"{k}\n{srt_ts(start)} --> {srt_ts(end)}\n{chunk}\n")
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
