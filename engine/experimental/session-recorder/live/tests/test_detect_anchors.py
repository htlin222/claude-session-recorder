import numpy as np

import detect_anchors as da


def test_detect_turns_guided_drops_spinner_peaks():
    # A real recording read a 2-turn demo as 5 submissions: each turn's true
    # typing peak (input box FILLED, ~near max) was flanked by SECONDARY peaks
    # from the streaming-response spinner leaking into the band (moderately
    # bright, > half-max). Guided selection must keep the 2 STRONGEST (real)
    # peaks and drop the spinner ones — not raise on the 5-vs-2 mismatch.
    inp = np.zeros(90)
    inp[10:14] = 400.0   # turn 1 typing (box filled)
    inp[25:29] = 250.0   # spinner after turn 1 (leaks above half-max=200)
    inp[45:49] = 390.0   # turn 2 typing (box filled)
    inp[60:64] = 300.0   # spinner
    inp[75:79] = 220.0   # spinner
    full = np.full(90, 100.0)
    turns = [{"type_dur": 0.5}, {"type_dur": 0.5}]
    out = da.detect_turns(full, inp, n=2, turns=turns, pre_enter=0.4)
    assert len(out) == 2
    submits = [round(t["submit"], 2) for t in out]
    # the two TALL peaks end at frames 14 and 49 -> 14/12.5=1.12, 49/12.5=3.92
    assert submits == [1.12, 3.92]
    # the spinner submits (29,64,79 /12.5 = 2.32/5.12/6.32) are NOT selected
    assert 2.32 not in submits and 5.12 not in submits


def test_merge_same_burst_groups_fuses_wrap_split_typing():
    # Issue #22 repro (real --robust capture, 27-word/3-line prompt): a long
    # prompt that wraps the input box onto a new line makes the auto-located
    # FIXED band lose the just-typed line and briefly show the fresh (blank)
    # wrapped line, so ONE continuous typing burst reads as TWO near-max
    # "submissions" with a short, RISING gap between them (never idle). Real
    # measurements: peaks 379 and 351 out of fmax 379 (ratios 1.00/0.93), 19
    # frames (1.52s) apart, climbing from 43 to 175 within that gap.
    inp = np.zeros(60)
    inp[10:14] = 400.0                                  # first wrap piece
    for i, v in zip(range(14, 19), np.linspace(20, 150, 5)):
        inp[i] = v                                       # short RISING dip: still typing
    inp[19:30] = 390.0                                   # second wrap piece (the real submit)
    fmax = float(inp.max())
    groups = [(10, 14), (19, 30)]
    assert da._merge_same_burst_groups(groups, inp, fmax) == [(10, 30)]


def test_merge_same_burst_groups_leaves_distinct_turns_alone():
    # A genuinely separate (if fast) next turn must NOT be swept into the
    # same merge just because it also has a near-max peak and a short gap —
    # the discriminator is whether the gap is IDLE (flat) or actively
    # refilling. Mirrors the gap shape used by
    # test_detect_turns_recovers_merged_consecutive_instant_group (flat 0
    # between two real submissions).
    inp = np.zeros(60)
    inp[10:14] = 400.0
    inp[30:34] = 390.0                                   # flat/idle gap in between: real turn
    fmax = float(inp.max())
    groups = [(10, 14), (30, 34)]
    assert da._merge_same_burst_groups(groups, inp, fmax) == groups


def test_merge_same_burst_groups_leaves_weak_spinner_leak_alone():
    # Companion sanity check: a moderate-peak spinner leak (well under the
    # near-max floor) must never be fused in, regardless of gap length —
    # that disambiguation is left entirely to the STRONGEST-peak selection
    # below, unchanged.
    inp = np.zeros(60)
    inp[10:14] = 400.0
    inp[20:24] = 250.0                                   # spinner leak: short gap, weak peak
    fmax = float(inp.max())
    groups = [(10, 14), (20, 24)]
    assert da._merge_same_burst_groups(groups, inp, fmax) == groups


def test_detect_turns_wrap_split_no_longer_starves_neighbouring_turns():
    # End-to-end repro of the actual failure: a 3-turn demo where turn 1's
    # long prompt wraps into 2 near-max pieces (see the merge tests above)
    # and turn 2 is a WEAK real submission (peak just over half-max, like a
    # native-menu turn such as "/theme" — its content never fills the input
    # box the way typed text does). Before the fix, the naive "4 raw groups
    # for 3 turns -> keep the 3 STRONGEST peaks" selection kept BOTH wrap
    # pieces (peaks 385/390) and dropped turn 2's real (weaker, peak 220)
    # group instead — corrupting turn 1's own submit (took the FIRST wrap
    # piece's end, far too early) and starving its `done` search window
    # (bounded by the SECOND wrap piece's start, only ~1s later), while turn
    # 2 was wrongly assigned the second wrap piece's end as its own submit.
    N = 180
    inp = np.zeros(N)
    inp[10:14] = 400.0                                   # turn 0 (real) -> submit 1.12
    inp[40:55] = 385.0                                   # turn 1 wrap piece 1
    for i, v in zip(range(55, 68), np.linspace(20, 150, 13)):
        inp[i] = v                                        # still typing: rising, never idle
    inp[68:90] = 390.0                                   # turn 1 wrap piece 2 (the real submit)
    inp[130:134] = 220.0                                 # turn 2 (real, weak) -> submit 10.72
    full = np.full(N, 100.0)
    turns = [{"type_dur": 0.5}, {"type_dur": 1.0}, {"type_dur": 0.3}]
    out = da.detect_turns(full, inp, n=3, turns=turns, pre_enter=0.4)
    submits = [round(t["submit"], 3) for t in out]
    # turn 1 submits at the SECOND (real) wrap piece's end, not the first;
    # turn 2 keeps its own (weak) real group instead of losing it.
    assert submits == [1.12, 7.2, 10.72]


def test_detect_turns_raises_when_fewer_than_n():
    # FEWER groups than expected is a genuine miss — still raise (guided only
    # trims an OVERSHOOT, it never invents submissions).
    inp = np.zeros(60)
    inp[10:14] = 400.0
    full = np.full(60, 100.0)
    try:
        da.detect_turns(full, inp, n=2, turns=[{"type_dur": 0.5}] * 2, pre_enter=0.4)
        assert False, "expected SystemExit on under-detection"
    except SystemExit:
        pass


def test_detect_turns_recovers_merged_consecutive_instant_group():
    # Issue #18 repro: 2 normal turns, then 2 client-side INSTANT commands
    # back-to-back ("/context" then "/fast on"), with no real (model-invoking)
    # turn between them. Instant turns have no thinking-gap, so the intervening
    # settle+typing period never drops the input band below half-max long
    # enough to split — the merged span reads as ONE continuous group covering
    # BOTH turns' typing+Enter, so the naive detector finds 3 groups where 4
    # turns are expected. The recovery must split it back into 2 using the
    # KNOWN scripted timing (INSTANT_SETTLE + pre_enter + type_dur), not by
    # re-detecting pixels (there's no pixel signal left to re-detect from).
    N = 140
    inp = np.zeros(N)
    inp[10:14] = 400.0     # turn 0 (normal) typing peak -> submit @ 14/12.5=1.12
    inp[30:34] = 390.0     # turn 1 (normal) typing peak -> submit @ 34/12.5=2.72
    # turns 2+3 (instant, back-to-back) merged into ONE continuous span: no
    # thinking gap to split on. Constructed so the merge point (frame 70) is
    # exactly where INSTANT_SETTLE(1.8) + pre_enter(0.4) + turn3's
    # type_dur(0.6) = 2.8s = 35 frames back from the merged span's end (105).
    inp[60:105] = 400.0
    full = np.full(N, 100.0)
    turns = [
        {"type_dur": 0.5},
        {"type_dur": 0.5},
        {"type_dur": 0.4, "instant": True},   # "/context"
        {"type_dur": 0.6, "instant": True},   # "/fast on"
    ]
    out = da.detect_turns(full, inp, n=4, turns=turns, pre_enter=0.4)
    assert len(out) == 4
    submits = [round(t["submit"], 2) for t in out]
    assert submits == [1.12, 2.72, 5.6, 8.4]


def test_detect_turns_recovers_merged_group_using_per_turn_settle():
    # Issue #17 (landed alongside #18) gave NATIVE-MENU commands (e.g.
    # "/theme") the exact same `instant` flag/shape as no-menu instant
    # commands, but they can use a LONGER settle (NATIVE_MENU_SETTLE under
    # --tmux) than the no-menu INSTANT_SETTLE — gen_capture_tape.py records
    # the settle it actually used per-turn (`turns[i]["settle"]`). The
    # recovery MUST read that per-turn value rather than assuming one
    # constant, or a merged run starting with a native-menu turn would be
    # split at the wrong offset.
    N = 220
    inp = np.zeros(N)
    inp[10:14] = 400.0      # turn 0 (normal) typing peak -> submit @ 1.12
    inp[50:200] = 400.0     # turns 1+2 (instant, back-to-back) merged
    full = np.full(N, 100.0)
    turns = [
        {"type_dur": 0.5},
        {"type_dur": 0.3, "instant": True, "settle": 10.0},   # e.g. "/theme"
        {"type_dur": 0.4, "instant": True},                    # e.g. "/clear"
    ]
    out = da.detect_turns(full, inp, n=3, turns=turns, pre_enter=0.4)
    assert len(out) == 3
    submits = [round(t["submit"], 2) for t in out]
    # turn 1's submit is derived using ITS OWN settle (10.0), not the
    # INSTANT_SETTLE (1.8) default: 200/12.5 - (10.0+0.4+0.4) = 16.0 - 10.8 = 5.2
    assert submits == [1.12, 5.2, 16.0]


def test_detect_turns_raises_when_instant_shortfall_not_fully_explained():
    # A shortfall that ISN'T fully explained by consecutive-instant merges must
    # still raise — recovery is only allowed when the math checks out exactly,
    # never as a blanket excuse to swallow a genuine detection miss. Here only
    # ONE group is detected for 3 turns (shortfall=2), but the instant run
    # (turns 1+2) can only ever explain a shortfall of 1.
    inp = np.zeros(60)
    inp[10:14] = 400.0
    full = np.full(60, 100.0)
    turns = [{"type_dur": 0.5}, {"type_dur": 0.4, "instant": True},
             {"type_dur": 0.6, "instant": True}]
    try:
        da.detect_turns(full, inp, n=3, turns=turns, pre_enter=0.4)
        assert False, "expected SystemExit: shortfall not fully explained by instant merge"
    except SystemExit:
        pass


def test_detect_turns_recovers_partial_merge_within_mixed_settle_run():
    # Issue #21 repro: 3 consecutive instant-flagged turns with MIXED settle
    # durations — a native-menu turn ("/theme", NATIVE_MENU_SETTLE=10.0)
    # immediately followed by two plain instant turns ("/context", "/fast
    # on", each INSTANT_SETTLE=1.8) back-to-back. #20's recovery treated the
    # WHOLE 3-turn run as one atomic collapse candidate (either all 3 merge
    # into 1 group, or none do) — but real pixel behavior is a PARTIAL merge:
    # /theme's long settle keeps it its own visually-distinct group, while
    # /context + /fast on's short settle each DO merge into one group. So the
    # detector sees 4 raw groups for 5 turns (shortfall=1), which the old
    # "full run of 3 collapses -> shortfall of 2" math can't match — the
    # fix must instead recover via the same-settle SUB-run (/context +
    # /fast on only) and leave /theme's own group alone.
    N = 140
    inp = np.zeros(N)
    inp[10:14] = 400.0     # turn 0 (normal) typing peak -> submit @ 1.12
    inp[30:34] = 390.0     # turn 1 (normal) typing peak -> submit @ 2.72
    inp[45:49] = 380.0     # turn 2 ("/theme") own distinct peak -> submit @ 3.92
    # turns 3+4 ("/context" + "/fast on", back-to-back, both INSTANT_SETTLE)
    # merge into ONE continuous span: no thinking gap to split on. Same
    # construction as test_detect_turns_recovers_merged_consecutive_instant_group
    # (merge point at frame 70 = INSTANT_SETTLE(1.8)+pre_enter(0.4)+turn4's
    # type_dur(0.6) = 2.8s = 35 frames back from the merged span's end (105)).
    inp[60:105] = 400.0
    full = np.full(N, 100.0)
    turns = [
        {"type_dur": 0.5},
        {"type_dur": 0.5},
        {"type_dur": 0.3, "instant": True, "settle": 10.0},    # "/theme"
        {"type_dur": 0.4, "instant": True, "settle": 1.8},     # "/context"
        {"type_dur": 0.6, "instant": True, "settle": 1.8},     # "/fast on"
    ]
    out = da.detect_turns(full, inp, n=5, turns=turns, pre_enter=0.4)
    assert len(out) == 5
    submits = [round(t["submit"], 2) for t in out]
    assert submits == [1.12, 2.72, 3.92, 5.6, 8.4]


def test_detect_turns_recovers_full_collapse_of_same_settle_run_of_three():
    # Companion to the mixed-settle case above: a run of 3 consecutive
    # instant turns that ALL share the same (short) settle DOES fully
    # collapse into one detected group (the #20 case) — the fix must not
    # regress this: the whole-run collapse attempt should still succeed on
    # its own, with no need to fall back to sub-run splitting.
    N = 160
    inp = np.zeros(N)
    inp[50:140] = 400.0    # all 3 instant turns merge into ONE continuous span
    full = np.full(N, 100.0)
    turns = [
        {"type_dur": 0.5, "instant": True, "settle": 1.8},
        {"type_dur": 0.6, "instant": True, "settle": 1.8},
        {"type_dur": 0.6, "instant": True},
    ]
    out = da.detect_turns(full, inp, n=3, turns=turns, pre_enter=0.4)
    assert len(out) == 3
    submits = [round(t["submit"], 2) for t in out]
    assert submits == [5.6, 8.4, 11.2]


def test_detect_turns_raises_when_mixed_settle_shortfall_not_explained():
    # A genuine detection miss inside a mixed-settle instant run must still
    # raise — neither the original whole-run collapse attempt NOR the new
    # same-settle sub-run fallback may swallow a shortfall neither of them
    # can exactly account for.
    inp = np.zeros(60)
    inp[10:14] = 400.0   # only ONE raw group detected for all 5 turns
    full = np.full(60, 100.0)
    turns = [
        {"type_dur": 0.5},
        {"type_dur": 0.5},
        {"type_dur": 0.3, "instant": True, "settle": 10.0},
        {"type_dur": 0.4, "instant": True, "settle": 1.8},
        {"type_dur": 0.6, "instant": True, "settle": 1.8},
    ]
    try:
        da.detect_turns(full, inp, n=5, turns=turns, pre_enter=0.4)
        assert False, "expected SystemExit: shortfall not fully explained by any partition"
    except SystemExit:
        pass


def test_detect_turns_last_turn_done_never_exceeds_raw_video_length():
    # Real repro: the LAST turn's group can run all the way to the raw
    # capture's final analyzed frame when the recording stops mid-interaction
    # (e.g. a native menu like "/theme" still open, no Enter-clear ever
    # observed). `submit` then just means "the recording ended here", so the
    # existing submit+0.3s floor must not be allowed to push `done` past the
    # video's own length — that produced a `done` > vtot, which downstream
    # turned into a negative-width (or invalid) tail freeze window.
    N = 40
    inp = np.zeros(N)
    inp[10:N] = 220.0    # group runs off the end of the analyzed video: no clear seen
    full = np.full(N, 100.0)
    turns = [{"type_dur": 0.3}]
    out = da.detect_turns(full, inp, n=1, turns=turns, pre_enter=0.4)
    vtot = N / da.FPS
    assert out[0]["done"] <= vtot
    # one frame of slack left so a degenerate tail freeze still has a real
    # frame to source from (mirrors BootStrategy's "at end" -1 frame convention)
    assert out[0]["done"] <= round(vtot - 1.0 / da.FPS, 3)


def test_raw_segments_boot_then_alternating_soft_hard():
    turns = [{"typing_start": 4.0, "submit": 6.0, "done": 9.0},
             {"typing_start": 12.0, "submit": 13.0, "done": 17.0}]
    segs = da.raw_segments(ready=2.0, turns=turns, vtot=20.0)
    assert [s["kind"] for s in segs] == ["boot", "soft", "hard", "soft", "hard", "soft"]
    assert segs[0]["raw"] == [0.0, 2.0]                       # boot = [0, ready]
    assert segs[0]["raw"][0] == 0.0 and segs[-1]["raw"][1] == 20.0
    for a, b in zip(segs, segs[1:]):                          # contiguous
        assert a["raw"][1] == b["raw"][0]


def test_hard_segment_spans_typing_start_to_done():
    turns = [{"typing_start": 4.0, "submit": 6.0, "done": 9.0}]
    segs = da.raw_segments(ready=2.0, turns=turns, vtot=12.0)
    hard = [s for s in segs if s["kind"] == "hard"][0]
    assert hard["raw"] == [4.0, 9.0]
    assert hard["turn_idx"] == 0


def test_raw_segments_clamps_typing_start_before_ready():
    # ready (4.0) AFTER the derived typing_start (3.0): no negative/overlap allowed
    turns = [{"typing_start": 3.0, "submit": 6.0, "done": 12.0}]
    segs = da.raw_segments(ready=4.0, turns=turns, vtot=20.0)
    for s in segs:
        assert s["raw"][1] >= s["raw"][0]            # no negative-length segment
    for a, b in zip(segs, segs[1:]):
        assert a["raw"][1] == b["raw"][0]            # contiguous, non-overlapping
    hard = [s for s in segs if s["kind"] == "hard"][0]
    assert hard["raw"][0] >= 4.0                     # hard starts at/after ready


def test_raw_segments_monotonic_across_turns_with_estimate_overlap():
    # turn 2's typing_start estimate (11.0) falls before turn 1's done (12.0)
    turns = [{"typing_start": 5.0, "submit": 6.0, "done": 12.0},
             {"typing_start": 11.0, "submit": 13.0, "done": 18.0}]
    segs = da.raw_segments(ready=2.0, turns=turns, vtot=25.0)
    for s in segs:
        assert s["raw"][1] >= s["raw"][0]
    for a, b in zip(segs, segs[1:]):
        assert a["raw"][1] == b["raw"][0]
