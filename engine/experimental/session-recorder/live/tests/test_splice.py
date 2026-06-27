import numpy as np
import splice


def test_freeze_source_picks_minimal_delta_frame():
    deltas = np.array([5.0, 4.0, 0.1, 3.0])   # index 2 is the calmest
    assert splice.calmest_frame(deltas) == 2


def test_plan_copies_hard_and_boot_freezes_soft():
    segs = [
        {"kind": "boot", "raw": [0.0, 2.0], "out_dur": 2.0},   # exact: copy only
        {"kind": "soft", "raw": [2.0, 4.0], "out_dur": 3.0},   # freeze 3s
        {"kind": "hard", "raw": [4.0, 8.0]},                    # copy
        {"kind": "soft", "raw": [8.0, 9.0], "out_dur": 0.5},   # freeze 0.5s
    ]
    ops = splice.plan(segs)
    assert ops[0]["op"] == "copy"
    assert ops[1]["op"] == "freeze" and abs(ops[1]["out_dur"] - 3.0) < 1e-9
    assert ops[2]["op"] == "copy"
    assert ops[3]["op"] == "freeze" and abs(ops[3]["out_dur"] - 0.5) < 1e-9


def test_boot_freeze_extends_when_out_dur_exceeds_raw():
    segs = [{"kind": "boot", "raw": [0.0, 2.0], "out_dur": 5.0}]   # +3s hold
    ops = splice.plan(segs)
    assert ops[0]["op"] == "copy"
    assert ops[1]["op"] == "freeze"
    assert ops[1]["at"] == "end" and abs(ops[1]["out_dur"] - 3.0) < 1e-9
