import ledger


def test_output_timeline_accumulates_durations():
    segs = [
        {"kind": "soft", "raw": [0.0, 2.0], "out_dur": 3.0},   # stretched 2->3
        {"kind": "hard", "raw": [2.0, 6.0], "out_dur": 4.0},   # verbatim
        {"kind": "soft", "raw": [6.0, 7.0], "out_dur": 0.5},   # trimmed 1->0.5
    ]
    out = ledger.output_timeline(segs)
    assert out[0]["out"] == [0.0, 3.0]
    assert out[1]["out"] == [3.0, 7.0]
    assert out[2]["out"] == [7.0, 7.5]


def test_hard_segment_out_dur_defaults_to_raw_length():
    segs = [{"kind": "hard", "raw": [1.0, 4.0]}]   # no out_dur -> raw length
    out = ledger.output_timeline(segs)
    assert out[0]["out"] == [0.0, 3.0]
