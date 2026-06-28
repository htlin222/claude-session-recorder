import lint


def _led(beats):
    return {"beats": beats, "meta": {}}


def test_lint_passes_clean_ledger():
    beats = [
        {"id": "a", "kind": "intro", "tier": 1, "mode": "lead", "drop": False,
         "voice": {"start": 0.0, "end": 2.0}, "visual": {"start": 2.3, "end": 4.0},
         "panel": {"switch_at": 0.0}},
        {"id": "b", "kind": "think", "tier": 2, "mode": "ride", "drop": False,
         "voice": {"start": 4.6, "end": 6.0}, "visual": {"start": 4.5, "end": 8.0},
         "panel": {"switch_at": 0.0}},
    ]
    report = lint.check(_led(beats))
    assert report["ok"] is True and report["violations"] == []


def test_lint_flags_ride_voice_outside_visual():
    beats = [{"id": "b", "kind": "think", "tier": 2, "mode": "ride", "drop": False,
              "voice": {"start": 4.5, "end": 9.0},          # ends after visual.end
              "visual": {"start": 4.5, "end": 8.0}, "panel": {"switch_at": 4.5}}]
    report = lint.check(_led(beats))
    assert report["ok"] is False
    assert any("ride" in v for v in report["violations"])


def test_lint_flags_missing_tier1():
    beats = [{"id": "a", "kind": "intro", "tier": 1, "mode": "lead", "drop": True,
              "voice": None, "visual": {"start": 2.0, "end": 4.0},
              "panel": {"switch_at": 2.0}}]
    report = lint.check(_led(beats))
    assert report["ok"] is False
    assert any("tier-1" in v.lower() for v in report["violations"])


def test_lint_flags_lead_voice_not_leading():
    beats = [{"id": "a", "kind": "intro", "tier": 1, "mode": "lead", "drop": False,
              "voice": {"start": 0.0, "end": 3.0},          # ends after visual.start
              "visual": {"start": 2.0, "end": 4.0}, "panel": {"switch_at": 0.0}}]
    report = lint.check(_led(beats))
    assert report["ok"] is False
    assert any("lead" in v.lower() for v in report["violations"])
