#!/usr/bin/env python3
"""verify_session.py — gate the session-mode sync (the "loop until align" check).

Reads session_sync.json (written by session_overlay.py) and asserts the
invariants the design promises. Exit codes mirror verify_sync.py:
  0  PASS               voice leads every prompt + every think voice fits its gap
  1  FAIL, FIXABLE      a think voice overruns its real gap even after atempo —
                        the INNER loop is exhausted; OUTER loop = shorten that
                        turn's think line (or widen the prompt) and re-record
  2  FAIL, NOT-FIXABLE  voice does NOT lead typing (a structural/placement bug)

Run: python3 verify_session.py --demo <demo>
"""
import argparse
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True)
    args = ap.parse_args()
    s = json.load(open(os.path.join(os.path.abspath(args.demo), "session_sync.json"),
                       encoding="utf-8"))
    turns = s["turns"]
    leads = [t for t in turns if not t["voice_leads_typing"]]
    unfit = [t for t in turns if not t["think_fits_gap"]]
    neg = [t for t in turns if t["intro_onset"] < 0] + (
        [{"index": "open"}] if s.get("open_onset", 0) < 0 else [])

    trimmed = [t for t in turns if t.get("think_trimmed")]
    print(f"session sync: {len(turns)} turns, video {s['video_total']}s, claude-ready {s['ready']}s")
    for t in turns:
        flag = "" if (t["voice_leads_typing"] and t["think_fits_gap"]) else "  <-- "
        flag += "" if t["voice_leads_typing"] else "VOICE-TRAILS "
        flag += "" if t["think_fits_gap"] else f"THINK-OVERRUNS even shortened (gap {t['real_gap']}s)"
        note = "  [think auto-shortened to fit]" if (t.get("think_trimmed") and t["think_fits_gap"]) else ""
        print(f"  turn {t['index']}: lead<type={t['voice_leads_typing']} "
              f"think_fits={t['think_fits_gap']} gap={t['real_gap']}s{flag}{note}")
    nbeats = len(s.get("open_beats", []))
    print(f"  open: {nbeats} launch beats   close @ {s.get('close_onset','-')}s   "
          f"min clip gap {s.get('min_gap','?')}s")

    overlaps = s.get("overlaps", [])
    tight = s.get("tight_gaps", [])
    if overlaps:
        print(f"  overlapping narration: {overlaps}")
    if tight:
        print(f"  too-tight gaps (< breath): " +
              ", ".join(f"{g['prev']}->{g['next']} {g['gap']}s" for g in tight))
    if leads or neg or overlaps:
        print(f"\nFAIL (not fixable): {len(leads)} turn(s) where voice trails typing, "
              f"{len(neg)} negative onset(s), {len(overlaps)} narration overlap(s) — "
              f"placement bug.")
        raise SystemExit(2)
    if unfit or tight:
        if unfit:
            print(f"\nFAIL (fixable): {len(unfit)} turn(s) whose think line overruns the gap "
                  f"even shortened (claude answered too fast). Shorten that think line or make "
                  f"the prompt longer, and re-record. Turns: {[t['index'] for t in unfit]}")
        if tight:
            print(f"\nFAIL (fixable): {len(tight)} narration gap(s) tighter than a breath — "
                  f"the previous sentence runs into the next. Widen the offending margin "
                  f"(BEAT_GAP/THINK_GUARD/close) and re-run.")
        raise SystemExit(1)
    msg = "PASS: voice leads every prompt; think fits every gap; all clips breathe"
    if trimmed:
        msg += f" ({len(trimmed)} think auto-shortened: turns {[t['index'] for t in trimmed]})"
    print(f"\n{msg}.")


if __name__ == "__main__":
    main()
