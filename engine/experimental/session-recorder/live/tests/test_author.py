import json

import author


def test_tier2_think_kept_when_it_fits_the_measured_gap():
    d = author.fit_ride(voice_dur=2.0, gap=4.0)
    assert d["drop"] is False and d["dur"] <= 4.0


def test_tier2_think_dropped_when_even_trimmed_overruns():
    d = author.fit_ride(voice_dur=5.0, gap=1.0, first_clause_dur=2.0)
    assert d["drop"] is True


# ---------------------------------------------------------------------------
# Layer 2 — best-effort session-timeline.jsonl cross-check (issue #23
# postmortem; sibling of detect_anchors.py's Layer 1 deterministic floor).
# ---------------------------------------------------------------------------

def test_load_timeline_rows_missing_file_returns_empty_not_raise(tmp_path):
    # Absence must degrade gracefully — never a hard requirement/SPOF.
    assert author._load_timeline_rows(str(tmp_path / "nope.jsonl")) == []


def test_load_timeline_rows_malformed_file_returns_empty_not_raise(tmp_path):
    p = tmp_path / "session-timeline.jsonl"
    p.write_text("{not json\n", encoding="utf-8")
    assert author._load_timeline_rows(str(p)) == []


def test_load_timeline_rows_keeps_only_the_last_session(tmp_path):
    rows = [
        {"t": 1.0, "event": "SessionStart"},
        {"t": 2.0, "event": "UserPromptSubmit"},
        {"t": 10.0, "event": "SessionStart"},   # a second, later session
        {"t": 11.0, "event": "UserPromptSubmit"},
        {"t": 15.0, "event": "Stop"},
    ]
    p = tmp_path / "session-timeline.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    out = author._load_timeline_rows(str(p))
    assert len(out) == 3
    assert out[0]["event"] == "SessionStart" and out[0]["t"] == 10.0


def test_turn_wallclock_deltas_skips_instant_turns_without_shifting_the_rest():
    # Mirrors panel.py's _turn_stop_events regression: an instant turn fires
    # UserPromptSubmit but never Stop, so naive index-zipping would corrupt
    # every later turn's pairing.
    turns = [{"prompt": "/rename demo", "instant": True},
             {"prompt": "write fizzbuzz"}, {"prompt": "add a test"}]
    rows = [{"event": "UserPromptSubmit", "t": 1.0},
            {"event": "UserPromptSubmit", "t": 5.0},
            {"event": "UserPromptSubmit", "t": 9.0},
            {"event": "Stop", "t": 6.0}, {"event": "Stop", "t": 10.0}]
    deltas = author._turn_wallclock_deltas(turns, rows)
    assert 0 not in deltas
    assert deltas[1] == 1.0 and deltas[2] == 1.0


def test_turn_wallclock_deltas_omits_turns_it_cannot_correlate():
    # Fewer Stop events than real turns (a dropped/retried hook, or simply no
    # timeline at all) must shrink what's checked, never raise here.
    turns = [{"prompt": "a"}, {"prompt": "b"}]
    rows = [{"event": "UserPromptSubmit", "t": 1.0},
            {"event": "UserPromptSubmit", "t": 5.0},
            {"event": "Stop", "t": 3.0}]     # only ONE Stop for two real turns
    deltas = author._turn_wallclock_deltas(turns, rows)
    assert deltas == {0: 2.0}


def test_timeline_cross_check_passes_when_pixel_and_real_agree():
    det_turns = [{"submit": 6.34, "done": 14.455}]   # done-submit = 8.115s
    real_deltas = {0: 8.115}    # the real recording's own measured delta
    author.check_timeline_cross_check(det_turns, real_deltas)   # must not raise


def test_timeline_cross_check_raises_on_wild_disagreement():
    # The #23-CLASS failure mode from Layer 2's independent angle: a turn whose
    # pixel-detected response window is drastically shorter than what the real
    # session-timeline.jsonl says actually happened — a strong, independent
    # signal that something upstream (submit/done detection) is wrong, even if
    # it happened to satisfy Layer 1's own floor.
    det_turns = [{"submit": 6.0, "done": 7.0}]   # pixel says only 1.0s
    real_deltas = {0: 20.0}                       # real hook delta says 20.0s
    try:
        author.check_timeline_cross_check(det_turns, real_deltas)
        assert False, "expected SystemExit on wild pixel-vs-wallclock mismatch"
    except SystemExit as e:
        msg = str(e)
        assert "turn 0" in msg and "1.0" in msg and "20.0" in msg


def test_timeline_cross_check_tolerates_generous_drift_on_long_turns():
    # A long, heavy-output turn is exactly where detect_turns' own docstring
    # warns video/wall-clock drift can grow to "many seconds" — the tolerance
    # must stay generous enough that ordinary drift on a long turn never
    # false-positives.
    det_turns = [{"submit": 0.0, "done": 45.0}]   # pixel: 45.0s
    real_deltas = {0: 60.0}                        # real: 60.0s (15s drift, <30% tol)
    author.check_timeline_cross_check(det_turns, real_deltas)   # must not raise


def test_timeline_cross_check_absolute_floor_protects_short_turns():
    # A short turn's ordinary detection noise (the +0.3s/+0.5s scan slop baked
    # into detect_anchors' `done`) must never trip this on its own — the
    # absolute floor dominates the relative tolerance for small real deltas.
    det_turns = [{"submit": 0.0, "done": 2.5}]     # pixel: 2.5s
    real_deltas = {0: 1.5}                          # real: 1.5s (1.0s off, well <5.0s floor)
    author.check_timeline_cross_check(det_turns, real_deltas)   # must not raise
