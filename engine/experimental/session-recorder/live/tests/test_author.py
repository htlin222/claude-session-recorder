import author


def test_tier1_soft_length_holds_voice_plus_gaps():
    out = author.soft_len_lead(voice_dur=2.7)
    assert out >= 2.7 + author.INTRO_GAP


def test_tier2_think_kept_when_it_fits_the_measured_gap():
    d = author.fit_ride(voice_dur=2.0, gap=4.0)
    assert d["drop"] is False and d["dur"] <= 4.0


def test_tier2_think_dropped_when_even_trimmed_overruns():
    d = author.fit_ride(voice_dur=5.0, gap=1.0, first_clause_dur=2.0)
    assert d["drop"] is True


def test_tier3_outro_dropped_when_it_would_crowd_next_tier1():
    d = author.fit_soft_droppable(voice_dur=2.0, room=0.3)
    assert d["drop"] is True


def test_tier3_outro_kept_when_room_is_enough():
    d = author.fit_soft_droppable(voice_dur=2.0, room=5.0)
    assert d["drop"] is False and d["dur"] == 2.0
