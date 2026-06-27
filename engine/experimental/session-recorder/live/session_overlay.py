#!/usr/bin/env python3
"""session_overlay.py — place the narration onto a filmed Claude Code session so
the voice LEADS each prompt (never trails it), then mux it over terminal.mp4.

Design: docs/plans/2026-06-27-claude-session-voiceover-sync-design.md.

Anchors come from VISUAL DETECTION (the repo's detect_clears philosophy), not
tape arithmetic — per-turn typing time, boot, and sentinel-render errors compound
too much, and the hook wall-clock drifts from VHS video time (~2s/turn observed),
so a single offset can't align. Instead we read the terminal's own pixels:
  * claude-ready : first frame the TUI fills the screen.
  * per turn     : the INPUT line lights up while the prompt is typed, then drops
                   when it's submitted -> (typing_start_i, submit_i).
The think gap's DURATION (offset-invariant) is taken from the timeline
(Stop_i - UserPromptSubmit_i) to locate the response end.

Voice placement (video time, from detected anchors):
  open     -> just after claude-ready, ending before turn-1's intro
  intro_i  -> ends exactly at typing_start_i      (=> voice-leads-typing)
  think_i  -> submit_i (rides the gap; atempo-compressed if it would overrun)
  outro_i  -> submit_i + real_gap_i (over the finished response)
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
    """(full, input) bright-pixel signals per frame: full screen and the bottom
    input-line band. Typing lights the input band; submitting clears it."""
    sw, sh = 240, 135
    raw = subprocess.run([FF, "-i", video, "-vf",
                          f"scale={sw}:{sh},format=gray,fps={FPS}",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (sw * sh)
    f = np.frombuffer(raw, np.uint8)[:n * sw * sh].reshape(n, sh, sw)
    r0, r1 = int(0.82 * sh), int(0.93 * sh)
    full = (f > 90).sum(axis=(1, 2)).astype(float)
    inp = (f[:, r0:r1, :] > 90).sum(axis=(1, 2)).astype(float)
    return full, inp


def detect_ready(full):
    thr = 0.3 * np.percentile(full, 90)
    for i in range(len(full)):
        if full[i] > thr and full[min(i + 3, len(full) - 1)] > thr:
            return round(i / FPS, 3)
    return 0.0


def detect_typing(inp):
    """Return [(typing_start, submit)] for every contiguous span where the input
    band sits well above its idle (cursor-blink) level. Includes the launch
    command typed in the shell before claude boots — the caller splits on
    claude-ready (launch spans come before it, prompt spans after)."""
    idle = float(np.median(inp[inp > 0]))
    thr = idle + 30
    hot = inp > thr
    regs, i, N = [], 0, len(inp)
    while i < N:
        if hot[i]:
            j = i
            while j < N and (hot[j] or (j + 3 < N and hot[j:j + 3].any())):
                j += 1
            regs.append((round(i / FPS, 3), round(j / FPS, 3)))
            i = j
        else:
            i += 1
    return regs


def load_gaps(timeline, n):
    """real_gap_i = Stop_i - UserPromptSubmit_i for n turns, from the LAST session
    in the timeline (timelog.py APPENDS, so reset or take the most recent block)."""
    rows = [json.loads(l) for l in open(timeline, encoding="utf-8") if l.strip()]
    starts = [i for i, r in enumerate(rows) if r["event"] == "SessionStart"]
    if starts:
        rows = rows[starts[-1]:]
    ups = [r["t"] for r in rows if r["event"] == "UserPromptSubmit"]
    stop = [r["t"] for r in rows if r["event"] == "Stop"]
    if len(ups) < n or len(stop) < n:
        raise SystemExit(f"last session has {len(ups)} prompts / {len(stop)} stops, "
                         f"need {n}. Stale/empty {timeline}? Reset it before recording.")
    return [round(stop[i] - ups[i], 3) for i in range(n)]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", required=True)
    ap.add_argument("--timeline", default=None,
                    help="session-timeline.jsonl (default: the repo session-recorder one)")
    ap.add_argument("--video", default="terminal.mp4")
    args = ap.parse_args()
    demo = os.path.abspath(args.demo)
    here = os.path.dirname(os.path.abspath(__file__))
    timeline = args.timeline or os.path.join(os.path.dirname(here), "session-timeline.jsonl")
    video = os.path.join(demo, args.video)
    plan = json.load(open(os.path.join(demo, "plan.json"), encoding="utf-8"))
    turns = plan["turns"]
    n = len(turns)
    vtot = dur(video)
    gaps = load_gaps(timeline, n)

    full, inp = signals(video)
    ready = detect_ready(full)
    all_regions = detect_typing(inp)
    # the n PROMPT typings are the spans after claude-ready (the launch typing in
    # the shell sits before it; we don't rely on detecting it — its position is
    # deterministic: nothing variable precedes it in the tape).
    regions = [r for r in all_regions if r[0] >= ready]
    if len(regions) != n:
        raise SystemExit(f"detected {len(regions)} prompt typings after ready, expected {n}. "
                         f"Tune the input band / threshold, or the recording differs.")

    op = plan.get("open", {})
    cl = plan.get("close", {"dur": 0.0, "text": "", "mp3": ""})

    segs = []        # (label, text, onset, dur, src_mp3, atempo)
    sync = {"video_total": round(vtot, 3), "ready": ready, "gaps": gaps,
            "regions": regions, "turns": []}

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
        first_intro = regions[0][0] - turns[0]["intro"]["dur"] - INTRO_GAP
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
        typing_start, submit = regions[i]
        stop = round(submit + gaps[i], 3)
        last_stop = stop
        # intro: ends INTRO_GAP before typing starts
        intro_onset = round(typing_start - tn["intro"]["dur"] - INTRO_GAP, 3)
        if tn["intro"]["dur"]:
            segs.append(("intro", tn["intro"]["text"], intro_onset,
                         tn["intro"]["dur"], os.path.join(demo, tn["intro"]["mp3"]), 1.0))
        # think: rides the real gap. If the authored line overruns, SHORTEN THE
        # CONTENT to fit (natural speech) — never time-compress (that suddenly
        # speeds the voice and sounds off against the normal-rate intro/outro).
        th_text, th_dur, th_trim = tn["think"]["text"], tn["think"]["dur"], False
        if th_dur:
            budget = max(0.5, gaps[i] - THINK_GUARD)
            th_text, th_mp3, th_dur, th_trim = fit_think(
                tn["think"]["text"], os.path.join(demo, tn["think"]["mp3"]),
                budget, demo, tn["index"])
            segs.append(("think", th_text, submit, th_dur, th_mp3, 1.0))
        # outro: over the finished response
        if tn["outro"]["dur"]:
            segs.append(("outro", tn["outro"]["text"], stop, tn["outro"]["dur"],
                         os.path.join(demo, tn["outro"]["mp3"]), 1.0))
        sync["turns"].append({
            "index": tn["index"], "typing_start": typing_start, "submit": submit,
            "stop": stop, "intro_onset": intro_onset, "real_gap": gaps[i],
            "think_dur": round(th_dur, 3), "think_trimmed": th_trim,
            "think_text": th_text,
            "voice_leads_typing": round(intro_onset + tn["intro"]["dur"], 3) <= typing_start,
            "think_fits_gap": round(th_dur, 3) <= round(gaps[i] - THINK_GUARD + 0.05, 3),
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
              f"submit@{t['submit']:.1f} stop@{t['stop']:.1f} gap={t['real_gap']:.1f}{trim}")
    if "open_onset" in sync:
        print(f"  open@{sync['open_onset']:.1f}  close@{sync.get('close_onset','-')}")


if __name__ == "__main__":
    main()
