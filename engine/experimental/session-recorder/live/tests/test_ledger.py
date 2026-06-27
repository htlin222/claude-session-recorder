import ledger


def test_beat_id_is_stable_6_hex():
    a = ledger.beat_id("intro", 0, "先請 Claude 寫 FizzBuzz")
    b = ledger.beat_id("intro", 0, "先請 Claude 寫 FizzBuzz")
    assert a == b and len(a) == 6
    assert all(c in "0123456789abcdef" for c in a)


def test_beat_id_changes_with_payload():
    assert ledger.beat_id("think", 1, "x") != ledger.beat_id("think", 1, "y")
    assert ledger.beat_id("intro", 0, "x") != ledger.beat_id("intro", 1, "x")


def test_beat_end_is_max_of_active_channels():
    beat = {"voice": {"start": 1.0, "end": 3.0},
            "visual": {"start": 3.2, "end": 5.0},
            "panel": {"switch_at": 1.0}}
    assert ledger.beat_end(beat) == 5.0


def test_beat_end_ignores_dropped_voice():
    beat = {"voice": None,
            "visual": {"start": 2.0, "end": 4.0},
            "panel": {"switch_at": 2.0}}
    assert ledger.beat_end(beat) == 4.0


def test_beat_start_is_min_of_active_channels():
    beat = {"voice": {"start": 1.0, "end": 3.0},
            "visual": {"start": 3.2, "end": 5.0},
            "panel": {"switch_at": 0.8}}
    assert ledger.beat_start(beat) == 0.8


def test_beat_start_ignores_dropped_voice():
    beat = {"voice": None, "visual": {"start": 2.0, "end": 4.0},
            "panel": {"switch_at": 2.0}}
    assert ledger.beat_start(beat) == 2.0
