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
import qparse


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


def capture(session):
    """The current tmux pane text for `session`."""
    return subprocess.run(
        ["tmux", "capture-pane", "-p", "-t", session],
        capture_output=True, text=True,
    ).stdout


def send(session, key):
    """send-keys one key (e.g. 'Down', 'Enter') to the tmux `session`."""
    subprocess.run(["tmux", "send-keys", "-t", session, key])


def _log(msg):
    print(f"[qmonitor] {msg}", file=sys.stderr, flush=True)


def _answer_one(session, pending, max_wait, poll, key_gap):
    """Wait for the selector, send the reconciled keystrokes, wait for the
    confirmation line. Guards every wait with max_wait so it never hangs."""
    # poll the pane until the selector is live (or give up)
    deadline = time.time() + max_wait
    parsed = None
    while time.time() < deadline:
        parsed = qparse.parse_selector(capture(session))
        if parsed.get("showing"):
            break
        time.sleep(poll)
    if not parsed or not parsed.get("showing"):
        _log("selector never showed; moving on")
        return

    keys = decide_keystrokes(pending, parsed)
    _log(f"selecting {pending.get('target_label')!r} via {keys}")
    for key in keys:
        send(session, key)
        time.sleep(key_gap)  # let the highlight move be visible on the recording

    # wait (briefly) for claude's confirmation line that the answer registered
    confirm_deadline = time.time() + max_wait
    while time.time() < confirm_deadline:
        if qnav.ANSWERED_RE and re.search(qnav.ANSWERED_RE, capture(session)):
            _log("answer confirmed")
            return
        time.sleep(poll)
    _log("no confirmation seen; moving on")


def run(session, signal_dir, max_wait=60.0, poll=0.3, key_gap=0.4):
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
        _answer_one(session, pending, max_wait, poll, key_gap)
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
    ap.add_argument("--max-wait", type=float, default=60.0,
                    help="max seconds to wait on any single screen condition")
    args = ap.parse_args()
    run(args.session, args.signal_dir, max_wait=args.max_wait)


if __name__ == "__main__":
    main()
