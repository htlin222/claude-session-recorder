import splice, ledger


def test_reconcile_rewrites_out_windows_and_shifts_beats():
    # planned: seg0 [0,3], seg1 [3,7], seg2 [7,9]; realized longer: 3.2, 4.1, 2.05
    led = {"meta": {"vtot_out": 9.0, "segments": [
        {"kind": "boot", "raw": [0, 2], "out": [0.0, 3.0], "out_dur": 3.0},
        {"kind": "hard", "raw": [2, 6], "out": [3.0, 7.0], "out_dur": 4.0},
        {"kind": "soft", "raw": [6, 7], "out": [7.0, 9.0], "out_dur": 2.0},
    ]}, "beats": [
        # a beat hosted by seg1 (planned [3,7]) at voice.start 4.0
        {"id": "b1", "kind": "think", "mode": "ride", "drop": False,
         "voice": {"clip": "x", "start": 4.0, "end": 5.0},
         "visual": {"start": 3.0, "end": 7.0}, "panel": {"switch_at": 3.0}},
    ]}
    splice.reconcile(led, [3.2, 4.1, 2.05])
    s = led["meta"]["segments"]
    assert s[0]["out"] == [0.0, 3.2]
    assert s[1]["out"] == [3.2, 7.3]
    assert s[2]["out"] == [7.3, 9.35]
    assert abs(led["meta"]["vtot_out"] - 9.35) < 1e-6
    # the think beat sat in seg1 (planned start 3.0 -> realized 3.2): shift +0.2
    b = led["beats"][0]
    assert abs(b["voice"]["start"] - 4.2) < 1e-6
    assert abs(b["visual"]["start"] - 3.2) < 1e-6


def test_reconcile_no_change_when_realized_equals_planned():
    led = {"meta": {"vtot_out": 5.0, "segments": [
        {"kind": "boot", "raw": [0, 2], "out": [0.0, 2.0], "out_dur": 2.0},
        {"kind": "soft", "raw": [2, 3], "out": [2.0, 5.0], "out_dur": 3.0},
    ]}, "beats": [
        {"id": "b", "kind": "intro", "mode": "lead", "drop": False,
         "voice": {"clip": "x", "start": 2.5, "end": 4.0},
         "visual": {"start": 5.0, "end": 5.0}, "panel": {"switch_at": 2.5}},
    ]}
    splice.reconcile(led, [2.0, 3.0])
    assert led["beats"][0]["voice"]["start"] == 2.5   # unchanged
