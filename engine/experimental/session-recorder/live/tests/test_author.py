import author


def test_tier2_think_kept_when_it_fits_the_measured_gap():
    d = author.fit_ride(voice_dur=2.0, gap=4.0)
    assert d["drop"] is False and d["dur"] <= 4.0


def test_tier2_think_dropped_when_even_trimmed_overruns():
    d = author.fit_ride(voice_dur=5.0, gap=1.0, first_clause_dur=2.0)
    assert d["drop"] is True
