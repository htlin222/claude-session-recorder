#!/usr/bin/env python3
"""author.py — Phase 1: synth voice, size soft segments, place beats, write the
finalized ledger (every beat start/end computed). v6 core. See
docs/plans/2026-06-28-event-ledger-deterministic-pipeline-design.md.

Model — leads never drop; only rides drop. The soft regions STRETCH to fit the
lead voice, so intro/outro/launch/close are always placed. Only the `think` beat
RIDES the fixed hard gap [submit, done] and is fit-or-dropped.

  boot segment      -> the launch beats. When the capture VOICE-PACED the launch
                       (capture.json carries launch beats with `at`+`mp3`), those
                       clips are REUSED and placed at their captured raw onsets,
                       and the boot is copied 1:1 (no freeze-extend) — the capture
                       was already paced to the voice, so the boot is real
                       animation, not a 15s frozen frame. FALLBACK (no captured
                       beats): synth the launch and freeze-EXTEND the boot to host
                       it (the static entry screen is held).
  pre soft (turn i) -> previous turn's outro (i>=1) then turn i's intro, sized so
                       the intro ENDS exactly INTRO_GAP before typing starts.
  hard (turn i)     -> turn i's think (ride). submit maps to output time
                       linearly (hard is copied verbatim). fit_ride keeps/trims/
                       drops; a trim RE-SYNTHs a clause-trimmed clip via fit_think.
  tail soft         -> last turn's outro then the close.
"""
import argparse
import json
import os
import re
import subprocess

from ledger import BREATH, beat_id, output_timeline, save
from detect_anchors import raw_segments

VOICE = "zh-TW-HsiaoChenNeural"
RATE = "+0%"
INTRO_GAP = 0.8       # silence between a lead voice end and the visual it leads
                      # (bumped from 0.3s: issue #5 — 0.3s felt hectic at scale,
                      # too short for a viewer to consolidate a just-heard
                      # sentence before the next visual event fires; see Mayer's
                      # segmenting principle / van der Meij software-training
                      # pacing guidance cited in the issue)
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

    # NEW v6 path: the capture tape voice-paced the launch and recorded each
    # beat's raw onset (`at`) + clip (`mp3`). REUSE those clips verbatim — do NOT
    # re-synth — and place them at their captured onsets; the boot is then copied
    # 1:1 (no freeze-extend), because the capture was already paced to the voice.
    # FALLBACK path (no captured beats — the integration tests, dry runs): synth
    # the launch from the script and freeze-extend the boot to host it (legacy).
    captured_launch = anchors.get("launch_beats")
    captured_outro = anchors.get("launch_outro")
    use_captured = bool(captured_launch)

    launch = []   # (slot, text, clip, dur) — fallback only
    if not use_captured:
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
            if use_captured:
                # boot is copied 1:1 — the capture was paced to the launch voice,
                # so NO freeze-extend for the launch. The boot must end at least a
                # BREATH after the LAST launch narration (the outro, or the last
                # flag if no outro), so turn-0's intro in the next soft segment is
                # cleanly separated — else the outro tail overlaps it by a frame.
                ends = [b["at"] + b["dur"] for b in captured_launch]
                if captured_outro:
                    ends.append(captured_outro["at"] + captured_outro["dur"])
                last_end = max(ends) if ends else 0.0
                s["out_dur"] = round(max(raw_len, last_end + BREATH), 3)
            else:
                # boot hosts the launch beats sequentially, then a trailing BREATH
                # so the last launch voice clears before turn-0's intro. Freeze-
                # extended only if the launch voice outlasts the captured animation.
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

    def add(kind, ti, text, clip_rel, vstart, vdur, vis, mode, tier, drop=False,
            id_payload=None):
        beats.append({
            "id": beat_id(kind, ti, text if id_payload is None else id_payload),
            "kind": kind, "turn_idx": ti,
            "text": text, "tier": tier, "mode": mode, "drop": drop,
            "voice": (None if (drop or not clip_rel) else
                      {"clip": clip_rel, "start": round(vstart, 3), "end": round(vstart + vdur, 3)}),
            "visual": {"start": round(vis[0], 3), "end": round(vis[1], 3)},
            "panel": {"switch_at": round(vstart if mode == "lead" else vis[0], 3)},
        })

    def pt(x):                     # a tight (point) visual window
        return (x, x)

    # ---- launch beats -------------------------------------------------------
    if use_captured:
        # Reuse the captured clips; place each at its raw onset mapped through the
        # boot. The boot is hard-copied 1:1, so output == raw: voice.start == at.
        boff = boot["out"][0] - boot["raw"][0]      # boot raw->out shift (== 0)
        for b in captured_launch:
            at = round(boff + b["at"], 3)
            add("launch_flag", -1, b.get("text", ""), b["mp3"], at, b["dur"],
                pt(at + b["dur"]), "lead", 1,
                id_payload=f'{b.get("token", "")}:{b.get("text", "")}')
        if captured_outro:
            at = round(boff + captured_outro["at"], 3)
            add("launch_flag", -1, captured_outro.get("text", ""), captured_outro["mp3"],
                at, captured_outro["dur"], pt(at + captured_outro["dur"]), "lead", 1,
                id_payload=f'outro:{captured_outro.get("text", "")}')
    else:
        cur = boot["out"][0]
        for slot, text, c, d in launch:
            add("launch_flag", -1, text, c, cur, d, pt(cur + d), "lead", 1,
                id_payload=f"{slot}:{text}")
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


# ---------------------------------------------------------------------------
# LAYER 2 — best-effort cross-check against session-timeline.jsonl (issue #23
# postmortem; see detect_anchors.py's Layer 1 floor for the sibling check).
# This is a SEPARATE, independent signal: Layer 1 catches an internally
# IMPOSSIBLE pixel result; this layer catches an internally CONSISTENT but
# still WRONG one, by comparing it against the real Claude-Code-hook wall
# clock (session-timeline.jsonl's UserPromptSubmit/Stop events) for the same
# recording. It lives HERE (author.py), not in detect_anchors.py, because
# detect_turns()'s own docstring is explicit that wall-clock time is NOT the
# primary ground truth for frame positions (VHS video time can drift from it
# by many seconds during heavy output) — so this must stay a secondary,
# best-effort sanity check, and author.py (which already knows the demo dir
# and orchestrates the pipeline — CONTRIBUTING.md's "I/O stays thin" split)
# is the right layer for optional I/O like this, not the pure-logic
# detect_anchors module.
# ---------------------------------------------------------------------------
TIMELINE_ABS_TOL = 5.0      # seconds — generous floor so short/quick turns'
                            # ordinary detection noise (the +0.3s/+0.5s scan
                            # slop already baked into detect_anchors' `done`)
                            # never trips this.
TIMELINE_REL_TOL = 0.5      # 50% of the real delta — generous vs. the
                            # documented "many seconds during heavy output"
                            # video/wall-clock drift risk, so this only fires
                            # on a WILD disagreement, not ordinary noise. A
                            # real capture (a ~110s recording; one turn's real
                            # Stop-minus-UserPromptSubmit delta was 8.115s)
                            # measured pixel-vs-wallclock agreement within
                            # ~0.6s (~7% relative) — comfortably inside this
                            # tolerance with a lot of headroom to spare.


def _load_timeline_rows(path):
    """Thin I/O: read <demo>/session-timeline.jsonl's LAST session (mirrors
    panel.py's last_session — duplicated rather than imported, so author.py,
    which runs UPSTREAM of panel.py in the pipeline, never has to depend on a
    downstream stage's module). Returns [] on ANY problem — missing file,
    unreadable, malformed JSON, empty — this is an optional secondary signal,
    never a hard requirement; absence must degrade silently, not raise."""
    try:
        with open(path, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
    except (OSError, json.JSONDecodeError):
        return []
    starts = [i for i, r in enumerate(rows) if r.get("event") == "SessionStart"]
    return rows[starts[-1]:] if starts else rows


def _turn_wallclock_deltas(turns, rows):
    """PURE: {turn_idx: real Stop-t minus UserPromptSubmit-t} for every turn we
    can UNAMBIGUOUSLY match — mirrors panel.py's _turn_stop_events matching
    (by POSITION among non-instant turns only: an instant turn fires
    UserPromptSubmit but never Stop, so naive index-zipping would shift every
    later turn onto the wrong pair). Any turn beyond the available rows (fewer
    hook events than turns — a dropped/retried hook, an older/partial capture,
    or simply no timeline at all) is silently omitted, never an error:
    correlation ambiguity here must shrink what Layer 2 can check, not break
    the pipeline."""
    ups = [r for r in rows if r.get("event") == "UserPromptSubmit"]
    stop = [r for r in rows if r.get("event") == "Stop"]
    real_idx = [i for i, t in enumerate(turns) if not t.get("instant")]
    out = {}
    for pos, ti in enumerate(real_idx):
        if ti >= len(ups) or pos >= len(stop):
            break
        u, s = ups[ti].get("t"), stop[pos].get("t")
        if isinstance(u, (int, float)) and isinstance(s, (int, float)) and s > u:
            out[ti] = s - u
    return out


def check_timeline_cross_check(det_turns, real_deltas):
    """LAYER 2's actual comparison (PURE — takes already-extracted data, no
    file I/O, so it's directly unit-testable without touching disk). For each
    turn we have a real delta for, compares the PIXEL-detected response window
    (done - submit — video time from Enter-clear to the last real content
    growth) against the real wall-clock (Stop - UserPromptSubmit) delta for
    the SAME turn. These should agree: `submit` is (per Layer 1's own
    invariant) exactly typing_start + type_dur + pre_enter after Enter, and
    `done` marks content settling, right around when Stop fires — DONE_HOLD's
    fixed hold and the next turn's PAD both come AFTER `done`, in the
    following soft segment (see raw_segments), so neither belongs in this
    comparison.

    Raises SystemExit ONLY on a WILD mismatch (see TIMELINE_ABS_TOL/REL_TOL
    above) for a turn we COULD correlate — a turn we couldn't correlate at all
    is already absent from `real_deltas` (see _turn_wallclock_deltas) and
    never reaches here. This is deliberately a SEPARATE, independent check
    from detect_anchors.py's Layer 1: a wrong-but-internally-self-consistent
    pixel result (e.g. a mis-selected group whose submit/typing_start/done
    still satisfy Layer 1's own floor) sails through Layer 1 untouched — only
    an independent real-world signal like the actual model wall-clock time can
    catch THAT class of error."""
    for ti, real_delta in real_deltas.items():
        if ti >= len(det_turns):
            continue
        pixel_delta = det_turns[ti]["done"] - det_turns[ti]["submit"]
        tol = max(TIMELINE_ABS_TOL, TIMELINE_REL_TOL * real_delta)
        if abs(pixel_delta - real_delta) > tol:
            raise SystemExit(
                f"turn {ti}: pixel-detected response window "
                f"({round(pixel_delta, 3)}s, from detect_anchors) wildly "
                f"disagrees with the real session-timeline.jsonl "
                f"Stop-minus-UserPromptSubmit delta ({round(real_delta, 3)}s) "
                f"for the same turn — outside the +/-{round(tol, 3)}s "
                f"tolerance. This independently signals the same class of "
                f"corruption Layer 1 guards against (a wrong pixel-detected "
                f"submit/done pair), even though it did not trip Layer 1's "
                f"own deterministic floor. Re-check group selection/merging "
                f"for this turn."
            )


def main():
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
    # LAYER 2 (issue #23 postmortem): best-effort cross-check the pixel
    # detection against session-timeline.jsonl's real hook wall-clock, if this
    # recording has one. Degrades silently when it's missing, unreadable, or
    # has no turns we can unambiguously correlate — see _load_timeline_rows /
    # _turn_wallclock_deltas. Only raises on a turn we COULD correlate whose
    # real and pixel-detected durations wildly disagree.
    real_deltas = _turn_wallclock_deltas(
        plan["turns"], _load_timeline_rows(os.path.join(demo, "session-timeline.jsonl")))
    if real_deltas:
        check_timeline_cross_check(anchors["turns"], real_deltas)
    # thread the capture's voice-paced launch beats (if any) into the anchors so
    # build_ledger reuses them instead of re-synthesizing + freeze-extending.
    lp = plan.get("launch", {}) or {}
    if lp.get("beats"):
        anchors["launch_beats"] = lp["beats"]
        anchors["launch_outro"] = lp.get("outro")
    with open(args.script, encoding="utf-8") as fh:
        script = json.load(fh)
    led = build_ledger(demo, script, anchors, write=True)
    n = len(led["beats"])
    dropped = sum(1 for b in led["beats"] if b.get("drop"))
    print(f"wrote {os.path.join(demo, 'ledger.json')}  ({n} beats, {dropped} dropped)")


if __name__ == "__main__":
    main()
