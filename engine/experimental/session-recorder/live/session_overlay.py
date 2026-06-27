#!/usr/bin/env python3
"""session_overlay.py — place the narration onto a filmed Claude Code session so
the voice LEADS each prompt (never trails it), then mux it over terminal.mp4.

Design: docs/plans/2026-06-27-claude-session-voiceover-sync-design.md.

ALL timing comes from VISUAL DETECTION of the terminal video — the only ground
truth (the repo's detect_clears philosophy). The hook wall-clock CANNOT be mapped
to video time: VHS video time drifts from wall-clock by many seconds during heavy
output (8.3s over one 70s session, measured), and the drift is non-uniform, so no
single or per-turn offset aligns. We read the terminal's own pixels instead:
  * claude-ready  : first frame the TUI fills the screen.
  * per turn      : the input band spikes then FALLS while the prompt is typed
                    -> (typing_start, submit); `done` (claude finished) is the
                    last big jump in full-screen content after submit.
The timeline is NOT used here (session_panel.py uses it only to label the tool
events, mapped into each detected [submit, done] window by wall-clock fraction).

Voice placement (video time, from detected anchors):
  open     -> deterministic launch beats (prelude-paced), each leads its flag
  intro_i  -> ends exactly at typing_start_i      (=> voice-leads-typing)
  think_i  -> submit_i (rides [submit, done]; content-shortened if it overruns)
  outro_i  -> done_i (over the finished response)
  close    -> after the last response, over the ending

Outputs (in --demo): session.mp4, session.srt, session_sync.json. The video is
copied through untouched (-c:v copy) — we only add an audio track.

Needs numpy (run with the repo venv: .venv/bin/python session_overlay.py ...).
"""
import argparse
import json
import os
import re
import subprocess

import numpy as np

FF = "/opt/homebrew/bin/ffmpeg"
FPS = 12.5
VOICE = "zh-TW-HsiaoChenNeural"
RATE = "+0%"
THINK_GUARD = 0.6       # free gap after the think voice (>= MIN_GAP so the think
                        # always leaves a breath before the outro at `stop`)
INTRO_GAP = 0.3         # silence between intro voice end and typing start
OPEN_GAP = 0.3          # margin around the open clip
OPEN_LEAD = 0.5         # open voice leads the launch-command typing by this much
MIN_GAP = 0.5           # minimum silence between any two narration clips (breath)


def dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout or 0)


def synth(text, out_mp3):
    subprocess.run(["edge-tts", "--voice", VOICE, "--rate", RATE,
                    "--text", text, "--write-media", out_mp3],
                   check=True, capture_output=True)
    return dur(out_mp3)


def fit_think(text, mp3, budget, demo, idx):
    """Make the think narration fit `budget` seconds by SHORTENING THE CONTENT at
    a clause boundary (。！？，、) — natural speech, never time-compressed (atempo
    would suddenly speed the voice up and sound off). Returns (text, mp3, dur,
    trimmed): the longest leading clause-prefix that fits. If even the first
    clause overruns, returns it anyway with trimmed=True so verify flags it."""
    base = dur(mp3)
    if base <= budget:
        return text, mp3, round(base, 3), False
    clauses = [c for c in re.split(r"(?<=[。！？，、])", text) if c]
    best = None
    for k in range(1, len(clauses) + 1):
        cand = "".join(clauses[:k]).rstrip("，、")
        if not cand.endswith(("。", "！", "？")):
            cand += "。"
        out = os.path.join(demo, "_voice", f"think_{idx}_fit.mp3")
        d = synth(cand, out)
        if d <= budget:
            best = (cand, out, round(d, 3))      # keep growing while it still fits
        else:
            break
    if best:
        return best[0], best[1], best[2], True
    # even one clause overruns: synth the first clause, flag it (FAIL_FIXABLE)
    cand = clauses[0].rstrip("，、")
    if not cand.endswith(("。", "！", "？")):
        cand += "。"
    out = os.path.join(demo, "_voice", f"think_{idx}_fit.mp3")
    return cand, out, round(synth(cand, out), 3), True


def srt_ts(s):
    h = int(s // 3600); s -= h * 3600
    m = int(s // 60); s -= m * 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


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
    # tight band on JUST the input line (above the status line), baseline-subtracted
    # so the constant status line cancels and only typed text lights it up. Response
    # output renders higher, so it stays out of this band.
    r0, r1 = int(0.84 * sh), int(0.905 * sh)
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


def detect_turns(full, inp, n):
    """Detect each turn's (typing_start, submit, done) FROM THE VIDEO — the only
    reliable ground truth (VHS video time drifts from the hook wall-clock by many
    seconds during heavy output, so the timeline can't be mapped to video time).

    A prompt typing is a span where the input band spikes high then FALLS BACK
    (the prompt is submitted) within a few seconds; the trailing idle state also
    sits moderately high but never falls, so the duration cap rejects it. `done`
    (claude finished) is the last big jump in full-screen content after submit —
    after that the screen stops changing."""
    fmax = float(inp.max()) or 1.0
    HI, LO = fmax * 0.30, fmax * 0.12
    spans, i, N = [], 0, len(inp)
    while i < N:
        if inp[i] > HI:
            j = i
            while j < N and inp[j] > LO:
                j += 1
            if (j - i) / FPS < 8.0:                     # a real typing is brief
                spans.append((round(i / FPS, 3), round(j / FPS, 3)))
            i = j
        else:
            i += 1
    if len(spans) < n:
        raise SystemExit(f"detected {len(spans)} prompt typings, expected {n}. "
                         f"Tune the input band / thresholds, or the recording differs.")
    spans = spans[:n]
    cmax = float(full.max()) or 1.0
    out = []
    for k, (ts, sub) in enumerate(spans):
        end = spans[k + 1][0] if k + 1 < len(spans) else N / FPS
        a, b = int(sub * FPS), int(end * FPS)
        last = a
        for m in range(a + 1, min(b, N)):
            if full[m] - full[m - 1] > 0.04 * cmax:     # content still growing
                last = m
        done = round(min(end - 0.3, last / FPS + 0.5), 3)
        out.append({"typing_start": ts, "submit": sub, "done": done})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", required=True)
    ap.add_argument("--video", default="terminal.mp4")
    args = ap.parse_args()
    demo = os.path.abspath(args.demo)
    video = os.path.join(demo, args.video)
    plan = json.load(open(os.path.join(demo, "plan.json"), encoding="utf-8"))
    turns = plan["turns"]
    n = len(turns)
    vtot = dur(video)

    full, inp = signals(video)
    ready = detect_ready(full)
    det = detect_turns(full, inp, n)        # per turn: typing_start, submit, done

    op = plan.get("open", {})
    cl = plan.get("close", {"dur": 0.0, "text": "", "mp3": ""})

    segs = []        # (label, text, onset, dur, src_mp3, atempo)
    sync = {"video_total": round(vtot, 3), "ready": ready, "turns": []}

    # open: narrate the LAUNCH as separate per-flag beats (not one dense clip).
    # VOICE LEADS each token: the tape narrates a flag, THEN types it, so the
    # narration onset is the start of its slot and the token appears at onset+dur.
    # The launch is the first thing in the tape and paced deterministically, so
    # every beat onset is known by walking the fixed slots from `prelude`.
    prelude = plan.get("prelude", 2.0)
    beats = op.get("beats", [])
    beat_gap = op.get("beat_gap", 0.6)
    cursor = prelude
    for k, b in enumerate(beats):
        if b.get("dur"):
            segs.append((f"open{k}", b["text"], round(cursor, 3), b["dur"],
                         os.path.join(demo, b["mp3"]), 1.0))
        cursor += b.get("dur", 0.0) + beat_gap   # narrate, type (instant), breath
    # open outro ("…進入互動畫面") plays at Enter, through boot, into the entry
    # screen — but turn 1 may start right after a fast boot, leaving little room.
    # FIT it to the window before turn-1's intro (content-trim), or DROP it if
    # there's no room (the flags are already narrated; the outro is just flavor).
    outro = op.get("outro", {"dur": 0.0})
    if outro.get("dur"):
        first_intro = det[0]["typing_start"] - turns[0]["intro"]["dur"] - INTRO_GAP
        budget = first_intro - MIN_GAP - cursor
        if budget >= 1.0:
            otext, omp3, odur, _ = fit_think(outro["text"], os.path.join(demo, outro["mp3"]),
                                             budget, demo, "open_outro")
            segs.append(("open_outro", otext, round(cursor, 3), odur, omp3, 1.0))
            sync["open_outro_dropped"] = False
        else:
            sync["open_outro_dropped"] = True   # no room before turn 1 — omit it
    sync["open_beats"] = [{"onset": s[2], "dur": s[3], "text": s[1]}
                          for s in segs if s[0].startswith("open")]

    last_stop = ready
    for i, tn in enumerate(turns):
        # all three anchors are DETECTED from the video (the only ground truth).
        typing_start = det[i]["typing_start"]
        submit = det[i]["submit"]
        done = det[i]["done"]                  # claude finished (last content jump)
        last_stop = done
        # intro: ends INTRO_GAP before typing starts
        intro_onset = round(typing_start - tn["intro"]["dur"] - INTRO_GAP, 3)
        if tn["intro"]["dur"]:
            segs.append(("intro", tn["intro"]["text"], intro_onset,
                         tn["intro"]["dur"], os.path.join(demo, tn["intro"]["mp3"]), 1.0))
        # think: rides the response window [submit, done]; shorten the CONTENT to
        # fit (natural speech, never time-compress).
        th_text, th_dur, th_trim = tn["think"]["text"], tn["think"]["dur"], False
        gap = max(0.5, done - submit)
        if th_dur:
            th_text, th_mp3, th_dur, th_trim = fit_think(
                tn["think"]["text"], os.path.join(demo, tn["think"]["mp3"]),
                max(0.5, gap - THINK_GUARD), demo, tn["index"])
            segs.append(("think", th_text, submit, th_dur, th_mp3, 1.0))
        # outro: over the finished response, at the detected `done`
        if tn["outro"]["dur"]:
            segs.append(("outro", tn["outro"]["text"], done, tn["outro"]["dur"],
                         os.path.join(demo, tn["outro"]["mp3"]), 1.0))
        sync["turns"].append({
            "index": tn["index"], "typing_start": typing_start, "submit": submit,
            "done": done, "intro_onset": intro_onset, "real_gap": round(gap, 3),
            "think_dur": round(th_dur, 3), "think_trimmed": th_trim,
            "think_text": th_text,
            "voice_leads_typing": round(intro_onset + tn["intro"]["dur"], 3) <= typing_start,
            "think_fits_gap": round(th_dur, 3) <= round(gap - THINK_GUARD + 0.05, 3),
        })

    # close: over the ending, AFTER the last placed voice finishes (+ a full
    # breath, so it never butts against the last outro)
    if cl["dur"]:
        voice_end = max((on + d for _l, _t, on, d, _m, _a in segs), default=last_stop)
        onset = round(max(last_stop + 0.5, voice_end + MIN_GAP), 3)
        segs.append(("close", cl["text"], onset, cl["dur"],
                     os.path.join(demo, cl["mp3"]), 1.0))
        sync["close_onset"] = onset

    # consecutive-clip spacing: report hard overlaps AND gaps tighter than MIN_GAP
    # (a 0.4s gap isn't an overlap but still sounds like one sentence runs into the
    # next — the gate must catch both).
    ordered = sorted(((on, on + d, lab) for lab, _t, on, d, _m, _a in segs))
    overlaps = [(ordered[k-1][2], ordered[k][2]) for k in range(1, len(ordered))
                if ordered[k][0] < ordered[k-1][1] - 0.05]
    tight = [{"prev": ordered[k-1][2], "next": ordered[k][2],
              "gap": round(ordered[k][0] - ordered[k-1][1], 3)}
             for k in range(1, len(ordered))
             if 0 <= ordered[k][0] - ordered[k-1][1] < MIN_GAP - 0.05]
    sync["overlaps"] = overlaps
    sync["tight_gaps"] = tight
    sync["min_gap"] = round(min((ordered[k][0] - ordered[k-1][1]
                                 for k in range(1, len(ordered))), default=9.0), 3)

    # report + subtitles first (so verify_session runs even if the mux fails)
    json.dump(sync, open(os.path.join(demo, "session_sync.json"), "w"),
              ensure_ascii=False, indent=2)
    srt = os.path.join(demo, "session.srt")
    with open(srt, "w", encoding="utf-8") as f:
        for k, (_lab, txt, onset, d, _m, _a) in enumerate(segs, 1):
            f.write(f"{k}\n{srt_ts(onset)} --> {srt_ts(onset + d)}\n{txt}\n\n")

    # one narration track: each clip atempo'd + adelay'd to its onset.
    # ffmpeg input 0 is the VIDEO, so the j-th voice clip is input j+1.
    inputs, filt, labs = [], [], []
    for j, (_lab, _txt, onset, _d, mp3, atempo) in enumerate(segs):
        inputs += ["-i", mp3]
        chain = f"[{j+1}:a]"
        if atempo != 1.0:
            chain += f"atempo={atempo},"
        dms = int(round(max(0.0, onset) * 1000))
        filt.append(f"{chain}adelay={dms}|{dms}[s{j}]")
        labs.append(f"[s{j}]")
    fc = ";".join(filt) + ";" + "".join(labs) + \
        f"amix=inputs={len(segs)}:normalize=0:dropout_transition=0," \
        f"apad=whole_dur={vtot:.3f},atrim=end={vtot:.3f}[a]"
    out = os.path.join(demo, "session.mp4")
    subprocess.run([FF, "-y", "-i", video, *inputs, "-filter_complex", fc,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", out],
                   check=True, capture_output=True)

    leads = all(t["voice_leads_typing"] for t in sync["turns"])
    fits = all(t["think_fits_gap"] for t in sync["turns"])
    print(f"wrote {out}")
    print(f"wrote {srt}  ({len(segs)} cues)")
    print(f"ready={ready}s  voice_leads_typing={leads}  think_fits_gap={fits}")
    for t in sync["turns"]:
        trim = "  [think trimmed to fit]" if t["think_trimmed"] else ""
        print(f"  turn {t['index']}: intro@{t['intro_onset']:.1f} type@{t['typing_start']:.1f} "
              f"submit@{t['submit']:.1f} done@{t['done']:.1f} win={t['real_gap']:.1f}{trim}")
    print(f"  open beats: {len(sync.get('open_beats', []))}  close@{sync.get('close_onset','-')}")


if __name__ == "__main__":
    main()
