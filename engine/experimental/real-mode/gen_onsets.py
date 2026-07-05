#!/usr/bin/env python3
"""gen_onsets.py <tape> <content.mp4> — print one onset (seconds) per line,
one per stdout line, for every `Type "..."` between `Show` and the closing
`Escape` in <tape>.

Why this exists: hand-calibrating cue timestamps against one render (via
screenshot probing) is slow AND not robust — VHS re-renders the same tape
with measurably different total duration run to run (CJK typing especially:
observed 8.96s vs 10.36s for an identical tape), so timestamps picked off
one render silently drift on the next. This instead:

  1. reads the tape's own Sleep constants (lead-in before the first Type,
     breath before each subsequent one, tail after Escape) — these ARE
     deterministic wall-clock waits, unlike typing speed;
  2. weights each line by character count, CJK chars at 3x — empirically,
     VHS spends roughly 3x as long per CJK character as per ASCII one
     (consistent with a per-UTF8-byte, not per-character, typing delay);
  3. divides whatever typing budget is LEFT (measured total duration minus
     the known-fixed lead-in/breaths/tail) across lines proportional to
     that weight.

So it re-derives onsets from the ACTUAL measured duration of whatever this
render produced, rather than predicting it — self-correcting for render-to-
render drift instead of assuming a fixed typing rate. Not frame-accurate,
but the cue is flavor sitting under a fast typing animation, not a hard
sync target; this keeps it in the right neighborhood automatically, with
no per-content manual calibration step.
"""
import re
import subprocess
import sys

FF_PROBE = "/opt/homebrew/bin/ffprobe"
CJK_WEIGHT = 3  # empirical: CJK chars render ~3x slower than ASCII in VHS


def char_weight(s):
    return sum(CJK_WEIGHT if ord(ch) > 0x2FFF else 1 for ch in s)


def parse_tape(tape_path):
    """Returns (lead_in, breath, tail, [line_text, ...]) — all Sleep values
    in seconds, lines in typing order. Assumes the convention used by this
    module's tapes: Sleep <lead_in> right after Show, Sleep <breath> before
    every Type (including the first), Sleep <tail> right after the closing
    Escape."""
    lines = open(tape_path, encoding="utf-8").read().splitlines()
    started = False
    lead_in = None
    breath = None
    tail = None
    texts = []
    sleeps_seen = 0
    for raw in lines:
        line = raw.strip()
        if not started:
            if line == "Show":
                started = True
            continue
        if line == "Escape":
            break
        m = re.match(r'^Sleep\s+([\d.]+)(ms|s)$', line)
        if m:
            val = float(m.group(1)) / (1000.0 if m.group(2) == "ms" else 1.0)
            if sleeps_seen == 0:
                lead_in = val
            elif breath is None:
                breath = val
            sleeps_seen += 1
            continue
        m = re.match(r'^Type\s+"(.*)"$', line)
        if m:
            texts.append(m.group(1))
    # tail: first Sleep after the closing Escape
    in_tail = False
    for raw in lines:
        line = raw.strip()
        if line == "Escape":
            in_tail = True
            continue
        if in_tail:
            m = re.match(r'^Sleep\s+([\d.]+)(ms|s)$', line)
            if m:
                tail = float(m.group(1)) / (1000.0 if m.group(2) == "ms" else 1.0)
                break
    if lead_in is None or breath is None or tail is None or not texts:
        raise SystemExit(f"gen_onsets.py: couldn't parse {tape_path} "
                          f"(lead_in={lead_in} breath={breath} tail={tail} "
                          f"lines={len(texts)})")
    return lead_in, breath, tail, texts


def video_duration(path):
    out = subprocess.run(
        [FF_PROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return float(out.strip())


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: gen_onsets.py <tape> <content.mp4>")
    tape, video = sys.argv[1], sys.argv[2]
    lead_in, breath, tail, texts = parse_tape(tape)
    n = len(texts)
    total = video_duration(video)
    budget = total - lead_in - tail - breath * (n - 1)
    if budget <= 0:
        raise SystemExit(f"gen_onsets.py: non-positive typing budget "
                          f"({budget:.3f}s) — lead_in/breath/tail constants "
                          f"in this script no longer match {tape}?")
    weights = [char_weight(t) for t in texts]
    wsum = sum(weights)
    onset = lead_in
    for w in weights:
        print(f"{onset:.3f}")
        dur = budget * w / wsum
        onset += dur + breath


if __name__ == "__main__":
    main()
