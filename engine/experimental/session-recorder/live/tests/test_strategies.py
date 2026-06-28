import strategies


def test_registry_covers_the_three_kinds():
    assert set(strategies.REGISTRY) == {"hard", "boot", "soft"}


def test_verbatim_classification():
    assert strategies.strategy_for_kind("hard").verbatim is True
    assert strategies.strategy_for_kind("boot").verbatim is True
    assert strategies.strategy_for_kind("soft").verbatim is False


def test_tail_soft_freezes_from_start_not_calmest():
    # the tail's raw range runs through the Ctrl+C teardown into a blank shell;
    # it must freeze the RESULT (its start), not the globally-calmest frame.
    tail = {"kind": "soft", "role": "tail", "raw": [40.0, 47.0], "out_dur": 12.0}
    ops = strategies.strategy_for(tail).splice_ops(tail)
    assert ops[0]["freeze_from"] == "start"

def test_non_tail_soft_has_no_freeze_from():
    pre = {"kind": "soft", "role": "pre", "raw": [4.0, 6.0], "out_dur": 5.0}
    assert "freeze_from" not in strategies.strategy_for(pre).splice_ops(pre)[0]


def test_hard_copies_verbatim():
    ops = strategies.strategy_for({"kind": "hard", "raw": [4.0, 8.0]}).splice_ops(
        {"kind": "hard", "raw": [4.0, 8.0]})
    assert ops == [{"op": "copy", "raw": [4.0, 8.0]}]


def test_boot_copies_then_end_freezes_the_overflow():
    seg = {"kind": "boot", "raw": [0.0, 2.0], "out_dur": 5.0}
    ops = strategies.strategy_for(seg).splice_ops(seg)
    assert ops[0]["op"] == "copy"
    assert ops[1]["op"] == "freeze" and ops[1]["at"] == "end"
    assert abs(ops[1]["out_dur"] - 3.0) < 1e-9


def test_boot_no_freeze_when_out_dur_equals_raw():
    seg = {"kind": "boot", "raw": [0.0, 2.0], "out_dur": 2.0}
    assert len(strategies.strategy_for(seg).splice_ops(seg)) == 1   # copy only


def test_soft_freezes_for_out_dur():
    seg = {"kind": "soft", "raw": [2.0, 4.0], "out_dur": 3.0}
    ops = strategies.strategy_for(seg).splice_ops(seg)
    assert ops == [{"op": "freeze", "raw": [2.0, 4.0], "out_dur": 3.0}]


def test_unknown_kind_raises():
    import pytest
    with pytest.raises(KeyError):
        strategies.strategy_for({"kind": "wormhole", "raw": [0, 1]})
