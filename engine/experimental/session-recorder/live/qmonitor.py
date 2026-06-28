#!/usr/bin/env python3
"""qmonitor.py — drive the on-screen AskUserQuestion selector for the robust path.

claude runs in a tmux session (VHS renders it). The PreToolUse hook (render mode)
writes pending_q.json when a question fires. This monitor polls that signal, polls
the tmux pane until the selector is live (qparse), reconciles the target answer
against the ACTUAL on-screen option order (by label — robust to reordering), and
`tmux send-keys` the navigation + Enter. Pure decision in decide_keystrokes; the
run() loop is the I/O."""
import argparse
import json
import os
import re
import subprocess
import sys
import time

import qnav


def _as_questions(pending):
    """Normalise a pending signal to a list of question dicts. Accepts the new
    multi-question shape ({"questions": [...]}) and, for backward-compat, an
    old-style single-question signal (target_index/options at the top level)."""
    if isinstance(pending, dict) and pending.get("questions") is not None:
        return pending["questions"]
    return [pending]


def plan_keystrokes(pending):
    """The FULL key sequence to answer every question in `pending` up front.

    A multi-question AskUserQuestion renders one tab per question and
    AUTO-ADVANCES to the next tab on each answer-Enter, landing on a final Submit
    tab after the last question. The highlight resets to option 1 on each new
    question, so each question contributes qnav.keys_to_select(target, 0)
    (= Down×target + Enter). When there is more than one question, one extra
    Enter submits on the Submit tab. A SINGLE question has no Submit tab — its
    answer-Enter selects and closes, so no trailing Enter.

    Pure; the on-screen order matches the hook's tool_input order and the
    auto-advance is deterministic, so the whole plan is computable from the
    signal alone. multiSelect is not yet exercised by the spike."""
    return [k for group in plan_groups(pending) for k in group]


def plan_groups(pending):
    """Like plan_keystrokes but GROUPED: one key-group per question, plus a final
    one-Enter Submit group when there is more than one question. The monitor
    dwells BETWEEN groups (each Enter auto-advances to a fresh tab) so the viewer
    can read each question before it is answered on the recording."""
    questions = _as_questions(pending)
    groups = []
    for q in questions:
        # TODO multiSelect: Space-toggle each picked option before Enter; for now
        # treat a multiSelect question's target as a single pick (Down×target + Enter).
        groups.append(qnav.keys_to_select(q.get("target_index", 0), 0))
    if len(questions) > 1:
        groups.append(["Enter"])  # Submit tab
    return groups


def decide_keystrokes(pending, parsed):
    """The keys to select the pending target on the CURRENT screen. Reconcile the
    target by LABEL against the on-screen options (fall back to the signal's
    target_index); then qnav from the current highlight. [] if no selector."""
    if not parsed.get("showing"):
        return []
    options = parsed.get("options", [])
    label = pending.get("target_label")
    if label in options:
        idx = options.index(label)
    else:
        idx = min(pending.get("target_index", 0), max(0, len(options) - 1))
    return qnav.keys_to_select(idx, parsed.get("highlight", 0))


def _tmux_argv(socket, *args):
    """The tmux argv, prepending `-L <socket>` when `socket` is set. Pure: the
    tmux mode uses a DEDICATED socket (`-L vhsq`) so it never collides with the
    user's default tmux server (which also breaks env inheritance)."""
    return ["tmux"] + (["-L", socket] if socket else []) + list(args)


def capture(session, socket=None):
    """The current tmux pane text for `session`."""
    return subprocess.run(
        _tmux_argv(socket, "capture-pane", "-p", "-t", session),
        capture_output=True, text=True,
    ).stdout


def send(session, key, socket=None):
    """send-keys one key (e.g. 'Down', 'Enter') to the tmux `session`."""
    subprocess.run(_tmux_argv(socket, "send-keys", "-t", session, key))


def _log(msg):
    print(f"[qmonitor] {msg}", file=sys.stderr, flush=True)


def _answer_one(session, pending, max_wait, poll, key_gap, socket=None,
                read_dwell=2.5):
    """Wait for the selector, send the whole multi-question keystroke plan, wait
    for the confirmation line. Guards every wait with max_wait so it never hangs.

    The plan is computed up front from the signal (plan_keystrokes): the
    on-screen question order matches the hook's tool_input order and the selector
    auto-advances deterministically, so we don't need to re-parse the screen
    between questions. We only wait for FOOTER_RE to confirm the selector is
    live before sending."""
    # poll the pane until the selector footer is live (or give up)
    deadline = time.time() + max_wait
    live = False
    while time.time() < deadline:
        if re.search(qnav.FOOTER_RE, capture(session, socket)):
            live = True
            break
        time.sleep(poll)
    if not live:
        _log("selector never showed; moving on")
        return

    groups = plan_groups(pending)
    _log(f"answering {len(_as_questions(pending))} question(s) via {groups}")
    for group in groups:
        # DWELL first so the viewer can READ the question (each prior Enter
        # auto-advanced to a fresh tab), then send this question's keys slowly so
        # the highlight move + selection is visible on the recording.
        time.sleep(read_dwell)
        for key in group:
            send(session, key, socket)
            time.sleep(key_gap)

    # wait (briefly) for claude's confirmation line that the answer registered
    confirm_deadline = time.time() + max_wait
    while time.time() < confirm_deadline:
        if qnav.ANSWERED_RE and re.search(qnav.ANSWERED_RE, capture(session, socket)):
            _log("answer confirmed")
            return
        time.sleep(poll)
    _log("no confirmation seen; moving on")


def run(session, signal_dir, socket=None, max_wait=60.0, poll=0.3, key_gap=0.8,
        read_dwell=2.5):
    """Watch `signal_dir` for pending_q.json; for each, drive the on-screen
    selector. Stop when `<signal_dir>/.qmonitor_stop` appears. Never spins
    forever: every wait is bounded by max_wait."""
    pending_path = os.path.join(signal_dir, "pending_q.json")
    stop_path = os.path.join(signal_dir, ".qmonitor_stop")
    while not os.path.exists(stop_path):
        if not os.path.exists(pending_path):
            time.sleep(poll)
            continue
        try:
            with open(pending_path) as f:
                pending = json.load(f)
        except Exception as e:  # malformed/partial write — drop it and continue
            _log(f"bad pending_q.json ({e}); removing")
            _safe_remove(pending_path)
            continue
        _answer_one(session, pending, max_wait, poll, key_gap, socket, read_dwell)
        _safe_remove(pending_path)


def _safe_remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session", required=True, help="tmux session/target")
    ap.add_argument("--signal-dir", required=True,
                    help="dir where the hook writes pending_q.json")
    ap.add_argument("--socket", default=None,
                    help="dedicated tmux socket name (tmux -L <socket>)")
    ap.add_argument("--max-wait", type=float, default=60.0,
                    help="max seconds to wait on any single screen condition")
    ap.add_argument("--read-dwell", type=float, default=2.5,
                    help="seconds to dwell on each question before answering it "
                         "(lets the viewer read it on the recording)")
    ap.add_argument("--key-gap", type=float, default=0.8,
                    help="seconds between keystrokes (highlight move is visible)")
    args = ap.parse_args()
    run(args.session, args.signal_dir, socket=args.socket, max_wait=args.max_wait,
        key_gap=args.key_gap, read_dwell=args.read_dwell)


if __name__ == "__main__":
    main()
