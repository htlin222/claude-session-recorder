import ledger


def _beat(start, end, drop=False):
    return {"voice": {"start": start, "end": end},
            "visual": {"start": start, "end": end},
            "panel": {"switch_at": start}, "drop": drop}


def test_clean_sequence_has_no_violations():
    beats = [_beat(0, 2), _beat(2.5, 4), _beat(4.5, 6)]
    assert ledger.serialization_violations(beats) == []


def test_overlap_is_a_violation():
    beats = [_beat(0, 2), _beat(1.5, 3)]   # second starts before first ends
    v = ledger.serialization_violations(beats)
    assert len(v) == 1 and v[0]["gap"] < 0


def test_too_tight_gap_is_a_violation():
    beats = [_beat(0, 2), _beat(2.2, 4)]   # 0.2s < BREATH(0.5)
    assert len(ledger.serialization_violations(beats)) == 1


def test_dropped_beats_are_skipped():
    beats = [_beat(0, 2), _beat(2.1, 3, drop=True), _beat(2.6, 5)]
    assert ledger.serialization_violations(beats) == []
