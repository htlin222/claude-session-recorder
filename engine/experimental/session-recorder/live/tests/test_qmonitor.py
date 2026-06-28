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
