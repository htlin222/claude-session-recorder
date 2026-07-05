#!/usr/bin/env python3
"""detect_anchors.py — Phase 0: derive the ledger's HARD fields from the filmed
terminal video. Reuses the v5 detection core (signals / detect_ready /
detect_turns / dur) VERBATIM — it is the validated, stress-tested ground truth
(survives multi-turn file-writing). The NEW work is `raw_segments(...)`, which
turns each detected per-turn (typing_start, submit, done) into the alternating
SOFT/HARD segment partition the splice stage consumes, plus a `detect(...)` I/O
entry point.

Needs numpy (run with the repo venv: .venv/bin/python detect_anchors.py ...).
"""
import argparse
import json
import os
import subprocess

import numpy as np

FF = "/opt/homebrew/bin/ffmpeg"
FPS = 12.5

# Mirrors gen_capture_tape.py's INSTANT_SETTLE: the fixed settle Sleep after an
# INSTANT (client-side-only) turn's Enter, before the next turn's typing
# begins. Duplicated here (not imported) so this stays a pure-logic module per
# CONTRIBUTING.md ("Pure logic is unit-tested. ... I/O stays thin.") — keep the
# two values in sync if gen_capture_tape.py's ever changes.
INSTANT_SETTLE = 1.8


def dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout or 0)


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
    # AUTO-LOCATE the input line: it's the most temporally-DYNAMIC band in the
    # bottom region (typing swings its brightness hardest), while the status line
    # is near-constant and the BG baseline is uniform. So no hand-tuned band is
    # needed across font sizes / terminal heights — pick the bottom variance peak.
    rng = (f.max(axis=0) - f.min(axis=0)).mean(axis=1)          # per-row dynamic range
    lo, hi = int(0.80 * sh), int(0.95 * sh)
    peak = lo + int(np.argmax(rng[lo:hi]))
    hw = int(0.016 * sh)                                         # TIGHT: just the input box,
    r0, r1 = max(0, peak - hw), min(sh, peak + hw + 1)           # else response content leaks in
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


def _consecutive_instant_runs(turns):
    """Maximal (start, end) index ranges (inclusive, 0-based) of >=2 consecutive
    turns flagged `instant` in script order (see gen_capture_tape.py's
    INSTANT_COMMANDS / turn_plan["instant"]). These are the ONLY turns with no
    real thinking-gap between one Enter and the next turn's typing, so they are
    the only ones a merged-group shortfall can legitimately be explained by."""
    runs, i, n = [], 0, len(turns)
    while i < n:
        if turns[i].get("instant"):
            j = i
            while j + 1 < n and turns[j + 1].get("instant"):
                j += 1
            if j > i:
                runs.append((i, j))
            i = j + 1
        else:
            i += 1
    return runs


def _split_merged_instant_group(group, turns, start, end, pre_enter):
    """Split ONE detected group that merged consecutive instant turns
    turns[start..end] into `end - start + 1` (a, b) sub-groups, using the
    KNOWN scripted timing (INSTANT_SETTLE + pre_enter + each turn's type_dur)
    instead of re-detecting the split points from pixels — there is no pixel
    signal to re-detect from; that absence is exactly the failure mode being
    recovered from.

    group[1] (the merged span's end) is trusted as the LAST turn's true submit
    frame — it's the last real pixel event before the recording goes idle.
    Earlier turns' submit frames are derived by walking BACKWARD from it: the
    real-time gap between two consecutive instant turns' Enters is exactly
    that turn's settle Sleep (after the earlier Enter) + pre_enter (beat
    before the later Enter) + the later turn's type_dur (its typing
    duration) — all deterministic, scripted quantities. The settle duration
    isn't always INSTANT_SETTLE: a NATIVE-MENU instant turn (e.g. "/theme",
    see gen_capture_tape.py's NATIVE_MENU_COMMANDS) shares the exact same
    `instant` flag/shape but can use a longer settle (NATIVE_MENU_SETTLE under
    --tmux) — gen_capture_tape.py records the ACTUAL settle it used per-turn
    in `turns[i]["settle"]`, so read that instead of assuming one constant."""
    merged_a, merged_b = group
    b = {end: merged_b}
    for idx in range(end - 1, start - 1, -1):
        settle = turns[idx].get("settle", INSTANT_SETTLE)
        gap = settle + pre_enter + turns[idx + 1].get("type_dur", 1.0)
        b[idx] = b[idx + 1] - round(gap * FPS)
    a = {start: merged_a}
    for idx in range(start + 1, end + 1):
        a[idx] = b[idx - 1]     # bounds the PRECEDING sub-turn's `done` search
    return [(a[idx], b[idx]) for idx in range(start, end + 1)]


def _settle_of(turn):
    return turn.get("settle", INSTANT_SETTLE)


def _split_runs_by_settle(runs, turns):
    """Split each maximal instant run into maximal SUB-runs of >=2 consecutive
    turns that share the same recorded `settle` value (issue #21). A run's
    turns don't all necessarily merge as one block: turns[idx]["settle"] is
    the sleep AFTER idx's own Enter, i.e. it governs whether idx visually
    merges with idx+1. Within one flagged-instant run, a boundary where the
    settle changes (e.g. a NATIVE_MENU_SETTLE turn sitting next to
    INSTANT_SETTLE turns) is a real dividing line — the long-settle turn is
    its own visually-distinct submission — so only genuinely same-settle
    stretches are collapse candidates; a lone turn between two differently-
    settled neighbors never merges with anything."""
    sub = []
    for s, e in runs:
        i = s
        while i <= e:
            j = i
            while j + 1 <= e and _settle_of(turns[j]) == _settle_of(turns[j + 1]):
                j += 1
            if j > i:
                sub.append((i, j))
            i = j + 1
    return sub


def _try_recover_with_runs(runs, groups, turns, n, pre_enter):
    """Attempt the merge-recovery for one candidate list of (start, end)
    instant-run ranges. Returns a corrected, full-length `groups` list on
    success, or None if this particular partition doesn't (fully) explain
    the shortfall."""
    if not runs:
        return None
    collapsed = sum(e - s for s, e in runs)   # groups saved if EVERY run fully merged
    if len(groups) + collapsed != n:
        return None    # shortfall not exactly explained by these run merges

    # Map each turn index -> the detected-group "slot" it should occupy, in
    # temporal order, collapsing every run onto a single slot.
    run_of = {idx: (s, e) for s, e in runs for idx in range(s, e + 1)}
    slots, i = [], 0
    while i < len(turns):
        if i in run_of:
            s, e = run_of[i]
            slots.append((s, e))
            i = e + 1
        else:
            slots.append((i, i))
            i += 1
    if len(slots) != len(groups):
        return None     # sanity: the mapping must consume exactly the detected groups

    new_groups = []
    for (s, e), g in zip(slots, groups):
        if e > s:
            new_groups.extend(_split_merged_instant_group(g, turns, s, e, pre_enter))
        else:
            new_groups.append(g)
    return new_groups


def _recover_merged_instant_groups(groups, turns, n, pre_enter):
    """When len(groups) < n, try to explain the shortfall as one or more
    detected groups having merged a run of consecutive INSTANT turns (no
    thinking-gap to split on). Returns a corrected, full-length `groups` list
    on success, or None if the shortfall isn't (fully) explained this way — a
    genuine detection miss must still raise, never get silently papered over.

    Tries the WHOLE maximal instant run as one collapse candidate first (the
    original #20 recovery, unchanged — a run where every turn shares the same
    settle, e.g. two plain INSTANT_SETTLE turns, or the existing
    per-turn-settle test, only ever has this one possible partition anyway).
    If that doesn't exactly explain the shortfall, falls back to treating
    only same-settle SUB-runs within the maximal run as collapse candidates
    (issue #21) — a run can partially merge when settle durations differ
    within it, e.g. `/theme` (long settle) immediately followed by
    `/context`+`/fast on` (short settle, back-to-back): only the latter two
    merge, `/theme` stays its own detected group."""
    runs = _consecutive_instant_runs(turns)
    recovered = _try_recover_with_runs(runs, groups, turns, n, pre_enter)
    if recovered is not None:
        return recovered
    sub_runs = _split_runs_by_settle(runs, turns)
    if sub_runs == runs:
        return None    # no finer partition possible; already tried it above
    return _try_recover_with_runs(sub_runs, groups, turns, n, pre_enter)


def _merge_same_burst_groups(groups, inp, fmax):
    """Fuse adjacent groups that are really ONE continuous typing burst split by
    a transient dip, not two submissions. A long prompt that wraps
    the input box onto a new line makes the auto-located band (a FIXED, ~5-row
    window near the bottom — see `signals()`) briefly show a near-empty row: the
    just-typed line's content shifts out of the tracked band and the freshly
    wrapped (still-blank) line takes its place, so the band's brightness drops
    to near-baseline and climbs again as the next line fills — the EXACT
    rise-then-clear pixel shape `detect_turns` uses to mean "Enter cleared the
    box", even though the user never stopped typing (confirmed against a real
    27-word/3-line --robust capture: two "submits" 1.52s apart, both >=0.92 of
    the global peak, while the actual next turn's typing hadn't even started).

    Distinguish this from a genuine pair of DIFFERENT (but quick, back-to-back)
    turns — which can ALSO show a short gap with near-max peaks either side, so
    gap-length and peak-strength alone don't separate the two cases — using
    what a REAL Enter does that a wrap never does: it makes the box actually go
    IDLE. A real gap sits flat at (near) its post-clear floor for its whole
    length (nothing is being typed); a wrap dip instead keeps CLIMBING almost
    immediately, because the very same typing burst is still going — measured:
    the real dip fell 379->43 then was back up to 175 just 18 frames later,
    never resting. So on top of:
    - SHORT gap: at most ~2s, generous vs. the ~1.5s wrap dip measured (a real
      turn boundary always has at least a settle/think/PAD gap of several
      seconds; back-to-back INSTANT turns are handled separately and never show
      a partial dip like this — see `_recover_merged_instant_groups`);
    - both flanking peaks genuinely NEAR-MAX (typed text fills the box either
      side of the wrap), whereas spinner/response leakage peaks measurably
      lower (the existing `test_detect_turns_guided_drops_spinner_peaks`
      fixture never exceeds 0.75 of fmax);
    also require the gap to be RISING, not idle: the band's value right before
    the next group resumes must sit well above its value right after the
    previous group cleared."""
    GAP_CAP = round(2.0 * FPS)             # generous vs. the ~1.5s wrap dip measured
    STRONG = 0.8 * fmax                    # near-max only; spinner leakage tops out ~0.75x
    CLIMB = 0.2 * fmax                     # must be actively refilling, not idle
    merged = list(groups[:1])
    for a, b in groups[1:]:
        pa, pb = merged[-1]
        if (a - pb <= GAP_CAP
                and float(inp[pa:pb].max()) >= STRONG
                and float(inp[a:b].max()) >= STRONG
                and float(inp[a - 1]) - float(inp[pb]) >= CLIMB):
            merged[-1] = (pa, b)
        else:
            merged.append((a, b))
    return merged


def detect_turns(full, inp, n, turns, pre_enter):
    """Detect each turn's (typing_start, submit, done) FROM THE VIDEO — the only
    reliable ground truth (VHS video time drifts from the hook wall-clock by many
    seconds during heavy output, so the timeline can't be mapped to video time).

    The discriminator for a SUBMIT is a sharp PEAK: typing fills the input box to
    near its maximum brightness, then Enter clears it. Lingering response content
    in the band sits only MODERATELY bright and never peaks; the welcome flicker
    and the idle state peak low too. So the contiguous runs where the band exceeds
    HALF its global max are exactly the N prompt submissions — this separates a
    turn's typing from the previous turn's response output, which a simpler
    above-threshold span would merge. typing_start is derived from the tape's
    known typing duration; `done` is the last big jump in full-screen content
    before the next turn."""
    fmax = float(inp.max()) or 1.0
    above = inp > 0.5 * fmax
    groups, i, N = [], 0, len(inp)
    while i < N:
        if above[i]:
            j = i
            while j < N and (above[j] or (j + 6 < N and above[j:j + 6].any())):
                j += 1                                   # tolerate <=0.5s dips
            groups.append((i, j))
            i = j
        else:
            i += 1
    # Fuse wrap-split same-burst groups BEFORE any n-vs-count reasoning below —
    # otherwise a long wrapped prompt's own typing masquerades as an extra
    # (wrong) submission and can starve/mis-time real neighbouring turns.
    groups = _merge_same_burst_groups(groups, inp, fmax)
    # GUIDED selection: some response content (a streaming spinner / answer line)
    # can leak a SECONDARY peak into the tight band that clears half-max, so a turn
    # yields >1 group and the blind count overshoots (measured: a 2-turn demo read
    # as 5). We always KNOW n, so when there are MORE than n groups keep the n with
    # the STRONGEST peak — a real submission FILLS the input box to near-max while
    # spinner/response leakage peaks lower — back in temporal order. A count BELOW
    # n is still a genuine detection miss and raises.
    if len(groups) > n:
        strongest = sorted(groups, key=lambda g: float(inp[g[0]:g[1]].max()),
                           reverse=True)[:n]
        groups = sorted(strongest, key=lambda g: g[0])
    # FEWER than n: consecutive INSTANT turns (e.g. "/context" immediately
    # followed by "/fast on") have no thinking-gap between them, so the merged
    # span can read as ONE group instead of several. Recover using the known
    # scripted timing rather than raising outright — but ONLY when the
    # shortfall is fully explained by such a merge (see
    # _recover_merged_instant_groups); otherwise this is a genuine detection
    # miss and must still raise below.
    if len(groups) < n:
        recovered = _recover_merged_instant_groups(groups, turns, n, pre_enter)
        if recovered is not None:
            groups = recovered
    if len(groups) != n:
        raise SystemExit(f"detected {len(groups)} prompt submissions, expected {n}. "
                         f"Tune the input band / thresholds, or the recording differs.")
    cmax = float(full.max()) or 1.0
    vtot = round(N / FPS, 3)                              # raw video's own end
    out = []
    for k, (a, b) in enumerate(groups):
        submit = round(b / FPS, 3)                       # box fullest -> Enter clears
        typing_start = round(max(0.0, submit - turns[k].get("type_dur", 1.0) - pre_enter), 3)
        nxt = (groups[k + 1][0] / FPS) if k + 1 < len(groups) else vtot
        last = b
        for m in range(b + 1, min(int(nxt * FPS), N)):
            if full[m] - full[m - 1] > 0.04 * cmax:      # content still growing
                last = m
        done = round(min(nxt - 0.3, last / FPS + 0.5), 3)
        done = max(round(submit + 0.3, 3), done)
        # The LAST turn's group can run all the way to the raw capture's own
        # final frame (b == N) when the recording ends before a slow/manual
        # interaction — e.g. a native menu, like "/theme", still open when the
        # tape stops — never showing a real Enter-clear to detect. `submit`
        # then really just means "recording ended here", so the +0.3s floor
        # above must not be allowed to claim time the raw video doesn't have.
        # Leave one frame of slack (mirrors BootStrategy's "at end" freeze
        # source in strategies.py) so a degenerate zero-length tail still has
        # a real frame to source its freeze from, instead of asking ffmpeg for
        # a frame at/past the file's reported duration.
        if k + 1 == len(groups):
            done = min(done, round(vtot - 1.0 / FPS, 3))
        out.append({"typing_start": typing_start, "submit": submit, "done": done})
    return out


def raw_segments(ready, turns, vtot):
    """Partition raw-video time into MONOTONIC, non-overlapping segments. boot
    [0,ready] is the launch animation (verbatim); each turn's [typing_start,done]
    is hard (verbatim); idle gaps + tail are soft (freeze-stretchable). typing_start
    is a tape ESTIMATE (submit - type_dur - pre_enter) and can fall before `ready`
    or a previous `done`, so every boundary is clamped to the running cursor — a
    degenerate (zero-length) soft gap is allowed (splice freezes a single frame)."""
    ready = max(0.0, ready)
    segs = [{"kind": "boot", "raw": [0.0, ready], "role": "boot"}]
    cursor = ready
    for i, t in enumerate(turns):
        ts = max(t["typing_start"], cursor)          # can't type before ready/prev done
        done = max(t["done"], ts)                     # monotonic
        segs.append({"kind": "soft", "raw": [cursor, ts], "role": "pre", "turn_idx": i})
        segs.append({"kind": "hard", "raw": [ts, done], "turn_idx": i,
                     "submit": min(max(t["submit"], ts), done)})
        cursor = done
    segs.append({"kind": "soft", "raw": [cursor, max(cursor, vtot)], "role": "tail"})
    return segs


def detect(demo, video, plan):
    """I/O entry: run signals/detect on <demo>/<video>, return
    {ready, turns:[{typing_start,submit,done}], vtot, segments}. Writes nothing —
    author.py owns the ledger. Reuses the v5 detection verbatim."""
    path = os.path.join(demo, video)
    vtot = dur(path)
    full, inp = signals(path)
    ready = detect_ready(full)
    det = detect_turns(full, inp, len(plan["turns"]), plan["turns"],
                       plan.get("pre_enter", 0.4))
    return {"ready": ready, "turns": det, "vtot": round(vtot, 3),
            "segments": raw_segments(ready, det, vtot)}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", required=True, help="demo dir with terminal_raw.mp4 + capture.json")
    ap.add_argument("--video", default="terminal_raw.mp4")
    args = ap.parse_args()
    with open(os.path.join(args.demo, "capture.json")) as fh:
        plan = json.load(fh)
    out = detect(args.demo, args.video, plan)
    print(json.dumps(out["segments"], indent=2))


if __name__ == "__main__":
    main()
