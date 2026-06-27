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

    print(f"session sync: {len(turns)} turns, video {s['video_total']}s, claude-ready {s['ready']}s")
    for t in turns:
        flag = "" if (t["voice_leads_typing"] and t["think_fits_gap"]) else "  <-- "
        flag += "" if t["voice_leads_typing"] else "VOICE-TRAILS "
        flag += "" if t["think_fits_gap"] else f"THINK-OVERRUNS(gap {t['real_gap']}s, atempo {t['think_atempo']})"
        print(f"  turn {t['index']}: lead<type={t['voice_leads_typing']} "
              f"think_fits={t['think_fits_gap']} gap={t['real_gap']}s{flag}")
    if "open_onset" in s:
        print(f"  open @ {s['open_onset']}s   close @ {s.get('close_onset','-')}s")

    overlaps = s.get("overlaps", [])
    if overlaps:
        print(f"  overlapping narration: {overlaps}")
    if leads or neg or overlaps:
        print(f"\nFAIL (not fixable): {len(leads)} turn(s) where voice trails typing, "
              f"{len(neg)} negative onset(s), {len(overlaps)} narration overlap(s) — "
              f"placement bug.")
        raise SystemExit(2)
    if unfit:
        print(f"\nFAIL (fixable): {len(unfit)} turn(s) whose think voice overruns the real "
              f"gap even compressed. Shorten those think lines (or make the prompt take "
              f"longer) and re-record. Turns: {[t['index'] for t in unfit]}")
        raise SystemExit(1)
    print("\nPASS: voice leads every prompt; every think voice fits its gap.")


if __name__ == "__main__":
    main()
