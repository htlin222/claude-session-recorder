import re

import qnav


def test_keys_to_select_down_then_enter():
    assert qnav.keys_to_select(0, 0) == ["Enter"]
    assert qnav.keys_to_select(1, 0) == ["Down", "Enter"]
    assert qnav.keys_to_select(2, 0) == ["Down", "Down", "Enter"]


def test_keys_to_select_up_when_highlight_below_target():
    assert qnav.keys_to_select(0, 2) == ["Up", "Up", "Enter"]
    assert qnav.keys_to_select(1, 3) == ["Up", "Up", "Enter"]


def test_detection_patterns_match_the_real_ui():
    footer = "Enter to select · ↑/↓ to navigate · Esc to cancel"
    assert re.search(qnav.FOOTER_RE, footer)
    answered = "⏺ User answered Claude's questions:"
    assert re.search(qnav.ANSWERED_RE, answered)
    # the footer pattern must NOT match an ordinary screen
    assert not re.search(qnav.FOOTER_RE, "❯ write a python function")
