import threading

import qmonitor


def test_decides_keys_from_signal_and_parse():
    pending = {"target_index": 1, "target_label": "Bash (hello.sh)",
               "options": ["Python (hello.py)", "Bash (hello.sh)"]}
    parsed = {"showing": True, "options": ["Python (hello.py)", "Bash (hello.sh)"], "highlight": 0}
    assert qmonitor.decide_keystrokes(pending, parsed) == ["Down", "Enter"]


def test_reconciles_target_by_label_when_screen_order_differs():
    # the hook's target_index assumed one order, but the screen rendered another;
    # reconcile by LABEL against the on-screen options (robustness)
    pending = {"target_index": 1, "target_label": "Bash (hello.sh)",
               "options": ["Python (hello.py)", "Bash (hello.sh)"]}
    parsed = {"showing": True, "options": ["Bash (hello.sh)", "Python (hello.py)"], "highlight": 0}
    assert qmonitor.decide_keystrokes(pending, parsed) == ["Enter"]   # label is at on-screen idx 0


def test_falls_back_to_target_index_if_label_absent():
    pending = {"target_index": 1, "target_label": "Nope", "options": ["a", "b"]}
    parsed = {"showing": True, "options": ["a", "b"], "highlight": 0}
    assert qmonitor.decide_keystrokes(pending, parsed) == ["Down", "Enter"]


def test_no_keys_when_not_showing():
    assert qmonitor.decide_keystrokes({"target_index": 0}, {"showing": False}) == []


def test_tmux_argv_with_socket():
    assert qmonitor._tmux_argv("vhsq", "capture-pane", "-p", "-t", "s") == \
        ["tmux", "-L", "vhsq", "capture-pane", "-p", "-t", "s"]


def test_tmux_argv_without_socket():
    assert qmonitor._tmux_argv(None, "send-keys") == ["tmux", "send-keys"]


def test_plan_single_question_no_submit():
    pending = {"questions": [{"target_index": 1, "options": ["a", "b"]}]}
    assert qmonitor.plan_keystrokes(pending) == ["Down", "Enter"]   # single: no submit


def test_plan_two_questions_with_submit():
    pending = {"questions": [
        {"target_index": 0, "options": ["a", "b"]},
        {"target_index": 1, "options": ["x", "y"]}]}
    # Q1 default (Enter), Q2 second option (Down,Enter), then Submit (Enter)
    assert qmonitor.plan_keystrokes(pending) == ["Enter", "Down", "Enter", "Enter"]


def test_plan_wraps_legacy_single_signal():
    legacy = {"target_index": 1, "options": ["a", "b"]}   # old top-level shape
    assert qmonitor.plan_keystrokes(legacy) == ["Down", "Enter"]


def test_plan_groups_one_per_question_plus_submit():
    pending = {"questions": [
        {"target_index": 0, "options": ["a", "b"]},
        {"target_index": 1, "options": ["x", "y"]}]}
    # one group per question (Q1 default, Q2 second), then a submit group
    assert qmonitor.plan_groups(pending) == [["Enter"], ["Down", "Enter"], ["Enter"]]
    # plan_keystrokes is the flattened groups
    assert qmonitor.plan_keystrokes(pending) == ["Enter", "Down", "Enter", "Enter"]


def test_plan_groups_single_question_no_submit_group():
    pending = {"questions": [{"target_index": 1, "options": ["a", "b"]}]}
    assert qmonitor.plan_groups(pending) == [["Down", "Enter"]]


def test_multiselect_keys_toggle_then_submit():
    assert qmonitor._multiselect_keys([0]) == ["Space", "Right", "Enter"]
    assert qmonitor._multiselect_keys([0, 2]) == ["Space", "Down", "Down", "Space", "Right", "Enter"]
    assert qmonitor._multiselect_keys([1, 3]) == ["Down", "Space", "Down", "Down", "Space", "Right", "Enter"]


def test_plan_groups_single_multiselect_question():
    pending = {"questions": [{"multiSelect": True, "target_indices": [0, 2], "options": ["a", "b", "c", "d"]}]}
    assert qmonitor.plan_groups(pending) == [["Space", "Down", "Down", "Space", "Right", "Enter"]]


# ── native CLI menus (issue #1 bug 3): /theme, /rewind, /memory, `/plugin
# install`'s scope picker render the SAME selector footer/list widget as
# AskUserQuestion but are handled CLIENT-SIDE — no PreToolUse hook ever fires
# for them, so pending_q.json is NEVER written. qmonitor must detect and answer
# these by polling the pane directly, not by waiting on the signal file. ─────

_NATIVE_MENU_PANE = (
    "❯ 1. Dark mode\n"
    "  2. Light mode\n"
    "  3. Dark mode (colorblind-friendly)\n"
    "\n"
    "Enter to select · Up/down to navigate · Esc to cancel\n"
)

_NATIVE_MENU_PANE_HIGHLIGHT_1 = (
    "  1. Dark mode\n"
    "❯ 2. Light mode\n"
    "  3. Dark mode (colorblind-friendly)\n"
    "\n"
    "Enter to select · Up/down to navigate · Esc to cancel\n"
)


def test_native_menu_index_defaults_to_first_option():
    assert qmonitor._native_menu_index(["Dark mode", "Light mode"], {}) == 0


def test_native_menu_index_honors_star_override_by_index():
    assert qmonitor._native_menu_index(["Dark mode", "Light mode"], {"*": 1}) == 1


def test_native_menu_index_honors_star_override_by_label_substring():
    assert qmonitor._native_menu_index(["Dark mode", "Light mode"], {"*": "light"}) == 1


def test_native_menu_index_no_options_is_zero():
    assert qmonitor._native_menu_index([], {}) == 0


def test_decide_native_keystrokes_no_selector_showing():
    assert qmonitor.decide_native_keystrokes({"showing": False}, {}) == []


def test_decide_native_keystrokes_defaults_to_current_highlight():
    parsed = {"showing": True, "options": ["Dark mode", "Light mode"], "highlight": 0}
    assert qmonitor.decide_native_keystrokes(parsed, {}) == ["Enter"]


def test_decide_native_keystrokes_navigates_to_star_override():
    parsed = {"showing": True, "options": ["Dark mode", "Light mode"], "highlight": 1}
    assert qmonitor.decide_native_keystrokes(parsed, {"*": 0}) == ["Up", "Enter"]


def test_poll_action_idle_when_no_selector_showing():
    assert qmonitor.poll_action("$ some ordinary shell prompt\n", {}) == []


def test_poll_action_detects_native_menu_with_no_signal_file():
    # This is the exact blind spot: a native menu is on screen, no
    # pending_q.json exists (and never will), yet the pure decision logic
    # still produces keys to send.
    assert qmonitor.poll_action(_NATIVE_MENU_PANE, {}) == ["Enter"]


def test_poll_action_honors_answers_policy_for_native_menu():
    assert qmonitor.poll_action(_NATIVE_MENU_PANE_HIGHLIGHT_1, {"*": 0}) == ["Up", "Enter"]


def test_run_answers_native_menu_that_never_produces_a_pending_signal(tmp_path, monkeypatch):
    """Regression for issue #1 bug 3: --robust/qmonitor previously ONLY reacted
    to pending_q.json (written exclusively by the AskUserQuestion PreToolUse
    hook). A NATIVE CLI menu (/theme, /rewind, /memory, /plugin install's scope
    picker) never goes through that tool, so the file never appears and the OLD
    run() loop would poll os.path.exists forever without ever inspecting the
    pane — a genuine hang, not a regex mismatch.

    pending_q.json is deliberately NEVER created in this test (real tmp_path,
    nothing writes it) to prove run() answers from the pane alone. Guarded by a
    bounded thread-join so a pre-fix hang fails fast instead of blocking the
    suite."""
    sent = []

    def fake_capture(session, socket=None):
        return _NATIVE_MENU_PANE

    def fake_send(session, key, socket=None):
        sent.append(key)
        (tmp_path / ".qmonitor_stop").touch()  # tear down right after answering

    monkeypatch.setattr(qmonitor, "capture", fake_capture)
    monkeypatch.setattr(qmonitor, "send", fake_send)

    t = threading.Thread(
        target=qmonitor.run,
        args=("sess", str(tmp_path)),
        kwargs={"poll": 0.01, "key_gap": 0},
        daemon=True,
    )
    t.start()
    t.join(timeout=2.0)

    assert not t.is_alive(), "run() never inspected the pane for a native menu (blind spot)"
    assert sent == ["Enter"]
