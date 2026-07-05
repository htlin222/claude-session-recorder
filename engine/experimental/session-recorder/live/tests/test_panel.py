import os

import pytest

import panel

HAVE_PIL = panel.Image is not None
HAVE_FONT = os.path.exists(panel.CJK)


def test_keyframe_times_read_from_ledger_not_redetected():
    led = {"meta": {"segments": [
        {"kind": "boot", "turn_idx": -1, "out": [0.0, 6.0]},
        {"kind": "soft", "role": "pre", "turn_idx": 0, "out": [6.0, 9.0]},
        {"kind": "hard", "turn_idx": 0, "raw": [9.0, 14.0], "submit": 11.0, "out": [9.0, 14.0]},
        {"kind": "soft", "role": "tail", "out": [14.0, 16.0]},
    ]}, "beats": [
        {"kind": "launch_flag", "turn_idx": -1, "panel": {"switch_at": 0.5}, "drop": False},
        {"kind": "launch_flag", "turn_idx": -1, "panel": {"switch_at": 2.0}, "drop": False},
        {"kind": "intro", "turn_idx": 0, "panel": {"switch_at": 6.5}, "drop": False},
        {"kind": "think", "turn_idx": 0, "visual": {"start": 11.0, "end": 14.0},
         "panel": {"switch_at": 11.0}, "drop": False},
    ]}
    keys = panel.keyframe_times(led)
    launch = [round(k["t"], 1) for k in keys if k["type"] == "launch"]
    assert launch == [0.5, 2.0]                       # two flag reveals from the ledger
    assert any(k["type"] == "turn_header" and abs(k["t"] - 6.5) < 1e-9 for k in keys)
    assert any(k["type"] == "conclusion" and abs(k["t"] - 14.0) < 1e-9 for k in keys)


@pytest.mark.skipif(not (HAVE_PIL and HAVE_FONT), reason="needs Pillow + Hiragino font")
def test_render_panels_are_valid_images(tmp_path):
    from PIL import Image

    flags = [{"arg": "--model opus", "say": "用 opus 模型"}]
    lp = tmp_path / "launch.png"
    panel.launch_panel("claude", flags, 1).save(lp)
    tp = tmp_path / "turn.png"
    panel.turn_panel(1, 2, "請它寫一個函式", [{"tool": "Write", "target": "a.py"}],
                     1, "完成了").save(tp)
    for p in (lp, tp):
        assert p.exists()
        with Image.open(p) as im:
            assert im.size == (panel.PANEL_W, panel.H)


@pytest.mark.skipif(not (HAVE_PIL and HAVE_FONT), reason="needs Pillow + Hiragino font")
def test_wrap_handles_embedded_newlines():
    """textlength() raises ValueError on any string containing '\\n' — real
    tool-result text (a `target` or `conclusion`) can legitimately contain
    embedded newlines, so _wrap must collapse them before measuring."""
    img, d = panel._new()
    font = panel.F(panel.MONO, 18)

    multiline = "line one\nline two\nline three"
    lines = panel._wrap(d, multiline, font, 200)
    assert lines  # produced *some* wrapped output
    assert all("\n" not in ln for ln in lines)

    # \r\n (CRLF) must degrade the same way, not leave stray \r behind
    crlf = "first\r\nsecond\r\nthird"
    lines = panel._wrap(d, crlf, font, 200)
    assert lines
    assert all("\r" not in ln and "\n" not in ln for ln in lines)

    # all-whitespace / all-newline input must not raise and not IndexError;
    # newlines collapse to spaces (still valid, non-crashing output)
    whitespace_only = panel._wrap(d, "\n\n\n", font, 200)
    assert all("\n" not in ln for ln in whitespace_only)
    assert panel._wrap(d, "", font, 200) == []


@pytest.mark.skipif(not (HAVE_PIL and HAVE_FONT), reason="needs Pillow + Hiragino font")
def test_turn_panel_survives_multiline_target_and_conclusion():
    """Reproduces the real trigger: a tool's `target` or the turn's
    `conclusion` — actual Claude tool-result/reply content the script author
    doesn't control — contains a literal newline."""
    events = [{"tool": "Write", "target": "a.py\ndef f():\n    pass"}]
    conclusion = "Done.\nSecond line of the reply.\nThird line."
    img = panel.turn_panel(1, 2, "請它寫一個函式", events, 1, conclusion)
    assert img.size == (panel.PANEL_W, panel.H)
