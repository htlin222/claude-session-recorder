import detect_anchors as da


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
