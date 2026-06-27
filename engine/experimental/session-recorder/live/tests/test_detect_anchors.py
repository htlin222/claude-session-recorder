import detect_anchors as da


def test_raw_segments_alternate_soft_hard_and_cover_video():
    # boot ends at 2.0; two turns; video total 20.0
    turns = [{"typing_start": 4.0, "submit": 6.0, "done": 9.0},
             {"typing_start": 12.0, "submit": 13.0, "done": 17.0}]
    segs = da.raw_segments(ready=2.0, turns=turns, vtot=20.0)
    kinds = [s["kind"] for s in segs]
    # boot(soft) | type+gap(hard) | settle(soft) | type+gap(hard) | tail(soft)
    assert kinds == ["soft", "hard", "soft", "hard", "soft"]
    # contiguous + covers [0, vtot]
    assert segs[0]["raw"][0] == 0.0 and segs[-1]["raw"][1] == 20.0
    for a, b in zip(segs, segs[1:]):
        assert a["raw"][1] == b["raw"][0]


def test_hard_segment_spans_typing_start_to_done():
    turns = [{"typing_start": 4.0, "submit": 6.0, "done": 9.0}]
    segs = da.raw_segments(ready=2.0, turns=turns, vtot=12.0)
    hard = [s for s in segs if s["kind"] == "hard"][0]
    assert hard["raw"] == [4.0, 9.0]
    assert hard["turn_idx"] == 0
