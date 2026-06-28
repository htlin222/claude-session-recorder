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
