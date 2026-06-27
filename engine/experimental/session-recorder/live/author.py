#!/usr/bin/env python3
"""author.py — Phase 1: synth voice, size soft segments, place beats, write the
finalized ledger (every beat start/end computed). v6 core. See
docs/plans/2026-06-28-event-ledger-deterministic-pipeline-design.md.

Model — leads never drop; only rides drop. The soft regions STRETCH to fit the
lead voice, so intro/outro/launch/close are always placed. Only the `think` beat
RIDES the fixed hard gap [submit, done] and is fit-or-dropped.

  boot segment      -> all launch beats (intro + each flag say + outro), paced
                       from the boot out-start with BREATH between; the boot is
                       freeze-EXTENDED if the launch voice is longer than the
                       captured animation (the static entry screen is held).
  pre soft (turn i) -> previous turn's outro (i>=1) then turn i's intro, sized so
                       the intro ENDS exactly INTRO_GAP before typing starts.
  hard (turn i)     -> turn i's think (ride). submit maps to output time
                       linearly (hard is copied verbatim). fit_ride keeps/trims/
                       drops; a trim RE-SYNTHs a clause-trimmed clip via fit_think.
  tail soft         -> last turn's outro then the close.
"""
import argparse
import os
import re
import subprocess

from ledger import BREATH, beat_id, output_timeline, save
from detect_anchors import raw_segments

VOICE = "zh-TW-HsiaoChenNeural"
RATE = "+0%"
INTRO_GAP = 0.3       # silence between a lead voice end and the visual it leads
THINK_GUARD = 0.6     # free gap kept after a ride (think) voice


def synth(text, out_mp3):           # I/O boundary (monkeypatched in tests)
    subprocess.run(["edge-tts", "--voice", VOICE, "--rate", RATE,
                    "--text", text, "--write-media", out_mp3],
                   check=True, capture_output=True)
    return _dur(out_mp3)


def _dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout or 0)


def fit_ride(voice_dur, gap, first_clause_dur=None):
    """Tier-2 think rides the measured hard gap. Keep if it fits gap-THINK_GUARD;
    else trim (caller re-synths the trimmed clause); drop only if even the first
    clause overruns."""
    budget = max(0.5, gap - THINK_GUARD)
    if voice_dur <= budget + 0.1:
        return {"drop": False, "dur": round(voice_dur, 3)}
    if first_clause_dur is not None and first_clause_dur > budget + 0.1:
        return {"drop": True, "dur": 0.0}
    return {"drop": False, "dur": round(budget, 3)}   # trim to budget


def fit_think(text, mp3, budget, demo, idx):
    """Make the think narration fit `budget` seconds by SHORTENING THE CONTENT at
    a clause boundary (。！？，、) — natural speech, never time-compressed (atempo
    would suddenly speed the voice up and sound off). Returns (text, mp3, dur,
    trimmed): the longest leading clause-prefix that fits. If even the first
    clause overruns, returns it anyway with trimmed=True so verify flags it."""
    base = _dur(mp3)
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


def build_ledger(demo, script, anchors, write=True):
    """Synthesize every beat's voice, SIZE each soft segment to host its lead
    beats, place beats on the output timeline, and emit the finalized ledger.

    The committed serialization invariant counts a beat's FULL footprint
    (max over voice.end / visual.end / panel) — so visuals are TIGHT, non-
    overlapping windows, never the wide hosting segment. A lead beat's visual is
    the terminal action it leads (intro -> a point at typing_start; launch/outro/
    close -> a point at the voice end); a ride beat's visual is the hard response
    window [submit, done]. Each soft slot is sized to clear the preceding hard
    segment by a BREATH and to host its beats with BREATH between them, so the
    placement satisfies `beat[i].end + BREATH <= beat[i+1].start` by construction.
    """
    segs = [dict(s) for s in (anchors.get("segments") or raw_segments(
        anchors["ready"], anchors["turns"], anchors["vtot"]))]
    voice_dir = os.path.join(demo, "_voice")
    if write:
        os.makedirs(voice_dir, exist_ok=True)

    def clip(text, name):
        if not text:
            return None, 0.0
        mp3 = os.path.join(voice_dir, name + ".mp3")
        return os.path.relpath(mp3, demo), round(synth(text, mp3), 3)

    lc, turns = script.get("launch", {}), script["turns"]

    launch = []   # (slot, text, clip, dur)
    if lc.get("intro"):
        c, d = clip(lc["intro"], "open_intro"); launch.append(("intro", lc["intro"], c, d))
    for k, f in enumerate(lc.get("flags", [])):
        if f.get("say"):
            c, d = clip(f["say"], f"open_flag{k}"); launch.append((f"flag{k}", f["say"], c, d))
    if lc.get("outro"):
        c, d = clip(lc["outro"], "open_outro"); launch.append(("outro", lc["outro"], c, d))

    iv, tv, ov = [], [], []
    for i, t in enumerate(turns):
        iv.append(clip(t.get("intro", ""), f"intro_{i}") + (t.get("intro", ""),))
        tv.append(clip(t.get("think", ""), f"think_{i}") + (t.get("think", ""),))
        ov.append(clip(t.get("outro", ""), f"outro_{i}") + (t.get("outro", ""),))
    close_c, close_d = clip(script.get("close", ""), "close")

    def seq_len(durs):
        """Length to host `durs` sequentially with a BREATH between them, no
        trailing pad: sum(d) + BREATH*(n-1)."""
        return 0.0 if not durs else sum(durs) + BREATH * (len(durs) - 1)

    # ---- size each soft segment -------------------------------------------
    # Leads (intro / outro / launch / close) are ALWAYS stretch-hosted: a soft
    # segment freeze-extends with no upper bound, so every lead is placed in full
    # and NONE is ever dropped — there is no Tier-3 drop in v6. Sizing below just
    # computes how long each soft slot must hold to fit its lead beats + breaths.
    for s in segs:
        raw_len = round(s["raw"][1] - s["raw"][0], 3)
        if s["kind"] == "hard":
            continue
        if s["kind"] == "boot":
            # boot hosts the launch beats sequentially, then a trailing BREATH so
            # the last launch voice clears before turn-0's intro. Freeze-extended
            # only if the launch voice outlasts the captured animation.
            launch_dur = seq_len([b[3] for b in launch])
            s["out_dur"] = round(max(raw_len, launch_dur + BREATH if launch else 0.0), 3)
        elif s.get("role") == "pre":
            i = s["turn_idx"]
            lead = BREATH if i >= 1 else 0.0          # clear the prev hard/think
            prev_outro = ov[i - 1][1] if i >= 1 else 0.0
            outro_block = (prev_outro + BREATH) if prev_outro else 0.0
            intro_block = (iv[i][1] + INTRO_GAP) if iv[i][1] else 0.0
            if intro_block or outro_block:
                s["out_dur"] = round(lead + outro_block + intro_block, 3)
            elif i >= 1:
                s["out_dur"] = BREATH                  # bare clearance from prev hard
            else:
                s["out_dur"] = round(min(raw_len, BREATH), 3)
        else:  # tail
            outro = ov[-1][1] if turns else 0.0
            outro_block = (outro + BREATH) if outro else 0.0
            s["out_dur"] = round(BREATH + outro_block + (close_d if close_d else 0.0), 3)

    timed = output_timeline(segs)
    pre = {s["turn_idx"]: s for s in timed if s.get("role") == "pre"}
    hard = {s["turn_idx"]: s for s in timed if s["kind"] == "hard"}
    boot = next(s for s in timed if s["kind"] == "boot")
    tail = next(s for s in timed if s.get("role") == "tail")
    beats = []

    def add(kind, ti, text, clip_rel, vstart, vdur, vis, mode, tier, drop=False):
        beats.append({
            "id": beat_id(kind, ti, text), "kind": kind, "turn_idx": ti,
            "tier": tier, "mode": mode, "drop": drop,
            "voice": (None if (drop or not clip_rel) else
                      {"clip": clip_rel, "start": round(vstart, 3), "end": round(vstart + vdur, 3)}),
            "visual": {"start": round(vis[0], 3), "end": round(vis[1], 3)},
            "panel": {"switch_at": round(vstart if mode == "lead" else vis[0], 3)},
        })

    def pt(x):                     # a tight (point) visual window
        return (x, x)

    # ---- launch beats: sequential from the boot out-start -------------------
    cur = boot["out"][0]
    for slot, text, c, d in launch:
        add("launch_flag", -1, f"{slot}:{text}", c, cur, d, pt(cur + d), "lead", 1)
        cur += d + BREATH

    # ---- per-turn beats ----------------------------------------------------
    for i, t in enumerate(turns):
        h = hard[i]
        typing_out = h["out"][0]                       # hard copied verbatim
        if i >= 1 and ov[i - 1][0]:                    # previous turn's outro
            oc, od, ot = ov[i - 1]
            ostart = pre[i]["out"][0] + BREATH         # clear the prev hard/think
            add("outro", i - 1, ot, oc, ostart, od, pt(ostart + od), "lead", 3)
        ic, idur, itxt = iv[i]
        if ic:                                         # intro ENDS INTRO_GAP before typing
            istart = typing_out - INTRO_GAP - idur
            add("intro", i, itxt, ic, istart, idur, pt(typing_out), "lead", 1)
        thc, thdur, thtxt = tv[i]
        if thc:                                        # think RIDES [submit, done]
            # think is the ONLY droppable beat. fit_ride makes the keep/trim
            # decision against the measured gap; the actual DROP is decided below,
            # after the fit_think re-synth (write=True), when even the first clause
            # still overruns the gap.
            sub_out = typing_out + (h.get("submit", h["raw"][0]) - h["raw"][0])
            done_out = h["out"][1]
            gap = done_out - sub_out
            fr = fit_ride(thdur, gap)
            if fr["drop"]:
                add("think", i, thtxt, thc, sub_out, 0.0, (sub_out, done_out), "ride", 2, drop=True)
            elif fr["dur"] < thdur - 0.05 and write:
                # trimmed: re-synth a clause-trimmed clip that actually fits.
                # (write=False dry-run skips this and falls to the else: the clip
                # path stays full-length while dur is the trimmed budget —
                # intentional, dry-run is test-only and never muxes the clip.)
                budget = max(0.5, gap - THINK_GUARD)
                ntext, nmp3, ndur, _ = fit_think(thtxt, os.path.join(demo, thc),
                                                 budget, demo, i)
                if ndur > budget + 0.1:
                    # even the first clause overruns the measured gap -> drop
                    add("think", i, thtxt, thc, sub_out, 0.0, (sub_out, done_out),
                        "ride", 2, drop=True)
                else:
                    add("think", i, ntext, os.path.relpath(nmp3, demo), sub_out, ndur,
                        (sub_out, done_out), "ride", 2)
            else:
                add("think", i, thtxt, thc, sub_out, fr["dur"], (sub_out, done_out), "ride", 2)

    # ---- tail: last turn's outro then the close ----------------------------
    cur = tail["out"][0] + BREATH                      # clear the last hard/think
    if turns and ov[-1][0]:
        oc, od, ot = ov[-1]
        add("outro", len(turns) - 1, ot, oc, cur, od, pt(cur + od), "lead", 3)
        cur += od + BREATH
    if close_c:
        add("close", -1, script.get("close", ""), close_c, cur, close_d, pt(cur + close_d), "lead", 3)

    led = {"beats": beats, "meta": {"vtot_out": round(timed[-1]["out"][1], 3),
                                    "segments": timed, "demo": os.path.abspath(demo)}}
    if write:
        save(os.path.join(demo, "ledger.json"), led)
    return led


def main():
    import json
    import detect_anchors
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", required=True, help="demo dir with terminal_raw.mp4 + capture.json")
    ap.add_argument("--script", required=True, help="script json (launch/turns/close)")
    ap.add_argument("--video", default="terminal_raw.mp4")
    args = ap.parse_args()
    demo = os.path.abspath(args.demo)
    with open(os.path.join(demo, "capture.json"), encoding="utf-8") as fh:
        plan = json.load(fh)
    anchors = detect_anchors.detect(demo, args.video, plan)
    with open(args.script, encoding="utf-8") as fh:
        script = json.load(fh)
    led = build_ledger(demo, script, anchors, write=True)
    n = len(led["beats"])
    dropped = sum(1 for b in led["beats"] if b.get("drop"))
    print(f"wrote {os.path.join(demo, 'ledger.json')}  ({n} beats, {dropped} dropped)")


if __name__ == "__main__":
    main()
