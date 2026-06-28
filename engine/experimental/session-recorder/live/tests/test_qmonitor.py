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
