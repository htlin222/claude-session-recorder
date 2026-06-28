import qparse

SCREEN = """ ☐ Language

Which language should I use for the hello world program?

❯ 1. Python (hello.py)
     Write hello world as a Python script named hello.py
  2. Bash (hello.sh)
     Write hello world as a Bash script named hello.sh
  3. Type something.
────────────────────────────────────────────────────────────────
  4. Chat about this

Enter to select · ↑/↓ to navigate · Esc to cancel"""

NOT_A_QUESTION = "❯ write a python function\n  bypass permissions on"


def test_parses_a_live_selector():
    r = qparse.parse_selector(SCREEN)
    assert r["showing"] is True
    assert r["header"] == "Language"
    assert r["options"] == ["Python (hello.py)", "Bash (hello.sh)"]   # synthetic rows excluded
    assert r["highlight"] == 0                                         # ❯ on option 1 (0-based)


def test_highlight_tracks_the_caret():
    moved = SCREEN.replace("❯ 1. Python", "  1. Python").replace("  2. Bash", "❯ 2. Bash")
    r = qparse.parse_selector(moved)
    assert r["highlight"] == 1


def test_non_selector_screen_reports_not_showing():
    r = qparse.parse_selector(NOT_A_QUESTION)
    assert r["showing"] is False


def test_options_exclude_synthetic_rows():
    r = qparse.parse_selector(SCREEN)
    assert "Type something." not in r["options"]
    assert "Chat about this" not in r["options"]
