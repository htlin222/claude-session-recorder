#!/usr/bin/env python3
"""qnav.py — pure helpers for driving the Claude Code AskUserQuestion selector.

The selector highlights option 1 first; Down/Up move it; Enter selects. These are
shared by the VHS-scripted path (the tape emits the keys) and the tmux bg-monitor
(it send-keys them). Detection regexes (confirmed against a real render) live here
so every driver matches the same patterns."""

# the selector footer — unique to a LIVE AskUserQuestion selector (don't match
# option words; those also appear in the echoed prompt before the selector paints)
FOOTER_RE = r"↑/↓ to navigate"
# claude's post-selection confirmation line
ANSWERED_RE = r"User answered Claude's questions"


def keys_to_select(target_index, highlight=0):
    """The key sequence to move the highlight from `highlight` to the 0-based
    `target_index` and select it: Down/Up x |delta| then Enter."""
    delta = target_index - highlight
    key = "Down" if delta > 0 else "Up"
    return [key] * abs(delta) + ["Enter"]
