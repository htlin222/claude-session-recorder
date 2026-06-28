#!/usr/bin/env python3
"""qparse.py — pure parser for the Claude Code AskUserQuestion selector.

The robust path runs a background monitor that reads the terminal via
`tmux capture-pane -p`. From that snapshot it must decide: is a selector showing,
what are the (model-authored) options, and which row is highlighted. This module
does exactly that and nothing else — it operates on a string, so it's trivially
testable against a REAL captured render (see tests/test_qparse.py).

The selector renders like:

     ☐ Language

    Which language should I use for the hello world program?

    ❯ 1. Python (hello.py)
         Write hello world as a Python script named hello.py
      2. Bash (hello.sh)
         Write hello world as a Bash script named hello.sh
      3. Type something.
    ─────────────────────────────────────────────────────────
      4. Chat about this

    Enter to select · ↑/↓ to navigate · Esc to cancel

The highlighted row is prefixed with `❯ ` (U+276F); the header line starts with
`☐ ` (U+2610). Claude always appends two SYNTHETIC rows after its own options —
`Type something.` and `Chat about this` — which we exclude from the parsed list.
"""

import re

import qnav

# the box-unchecked glyph that leads the header line
CHECKBOX = "☐"  # ☐
# the highlight caret that leads the selected option
CARET = "❯"  # ❯

# a numbered option line: optional caret, the number, then the label.
_OPTION_RE = re.compile(r"^\s*(?:" + CARET + r"\s+)?(\d+)\.\s+(.+?)\s*$")
# the header line: `☐ <header>`
_HEADER_RE = re.compile(r"^\s*" + CHECKBOX + r"\s+(.+?)\s*$")

# synthetic rows Claude always appends — never real options
_SYNTHETIC_EXACT = {"Type something."}
_SYNTHETIC_PREFIX = ("Chat about this",)


def _is_synthetic(label):
    if label in _SYNTHETIC_EXACT:
        return True
    return any(label.startswith(p) for p in _SYNTHETIC_PREFIX)


def parse_selector(text):
    """Parse a captured pane snapshot.

    Returns ``{"showing": False}`` when no live selector footer is present.
    Otherwise returns ``{"showing": True, "header", "question", "options",
    "highlight"}`` where ``options`` are the model's labels (synthetic rows
    excluded) and ``highlight`` is the 0-based index of the caret-marked option
    among those kept (0 if no caret is found)."""
    if re.search(qnav.FOOTER_RE, text) is None:
        return {"showing": False}

    lines = text.splitlines()

    # header (optional): first `☐ <header>` line
    header = None
    header_line_idx = None
    for i, line in enumerate(lines):
        m = _HEADER_RE.match(line)
        if m:
            header = m.group(1)
            header_line_idx = i
            break

    # question (optional, best-effort): first non-empty line after the header
    question = None
    if header_line_idx is not None:
        for line in lines[header_line_idx + 1:]:
            if line.strip():
                question = line.strip()
                break

    # options: scan numbered rows, keep the model's, track the caret
    options = []
    highlight = 0
    for line in lines:
        m = _OPTION_RE.match(line)
        if not m:
            continue
        label = m.group(2)
        if _is_synthetic(label):
            continue
        if CARET in line:
            highlight = len(options)
        options.append(label)

    return {
        "showing": True,
        "header": header,
        "question": question,
        "options": options,
        "highlight": highlight,
    }
