#!/usr/bin/env python3
"""autoanswer_questions.py — a PreToolUse hook that AUTO-ANSWERS the
AskUserQuestion tool so an automated/recorded `claude` session never blocks on an
interactive clarification prompt.

Why: the v6 recording pipeline drives a real `claude` TUI from a scripted tape
(type prompt -> wait for the Stop sentinel). If the inner claude calls
AskUserQuestion, the TUI blocks waiting for a human, the tape's Wait+Screen times
out, the Stop sentinel never prints, and the recording fails.

How: Claude Code hooks cannot inject a synthetic tool RESULT at PreToolUse (only
PostToolUse has updatedToolOutput, which fires too late). The viable lever is to
DENY the tool at PreToolUse and feed the chosen answer back as the deny REASON —
claude reads the reason and proceeds as if answered. This hook reads the
AskUserQuestion tool_input, picks an answer per question (the first option by
default, or a per-header override from $VHS_ANSWERS), and denies with a reason
that states the answer explicitly so claude continues with it.

Wire it (project .claude/settings.json):
  "PreToolUse": [ { "matcher": "AskUserQuestion",
    "hooks": [ { "type": "command", "command": "python3 \"$HERE/autoanswer_questions.py\"" } ] } ]

$VHS_ANSWERS (optional): JSON object mapping a question's `header` (or its text)
to the desired option label, e.g. {"Auth method":"OAuth"}. Unmatched questions
fall back to the first option.

Input (PreToolUse stdin), AskUserQuestion tool_input shape:
  {"questions":[{"question":"...","header":"...","multiSelect":false,
                 "options":[{"label":"...","description":"..."}]}]}
Output (stdout, exit 0): a PreToolUse deny carrying the chosen answers.
"""
import json
import os
import sys


def target_index_for(question, answers):
    """Return the 0-based index into the question's options chosen by the
    override logic. An override is looked up by the question's `header`, then its
    `question` text, then the catch-all key "*". The override value may be:
      * an int (or digit string) -> that option INDEX (force a non-default
        without knowing the labels — robust for demos; negatives wrap), or
      * a string -> the option whose label equals it, else contains it
        (case-insensitive substring), else ignored.
    Falls back to 0 (the first option). Returns None when there are no options."""
    opts = question.get("options") or []
    labels = [o.get("label", "") for o in opts if o.get("label")]
    if not labels:
        return None
    override = (answers.get(question.get("header"))
               or answers.get(question.get("question"))
               or answers.get("*"))
    if override is not None:
        if isinstance(override, int) or (isinstance(override, str) and override.lstrip("-").isdigit()):
            idx = int(override)
            if -len(labels) <= idx < len(labels):
                return idx % len(labels)
        elif isinstance(override, str):
            for i, lab in enumerate(labels):
                if lab == override:
                    return i
            for i, lab in enumerate(labels):
                if override.lower() in lab.lower():
                    return i
    return 0


def _labels(question):
    """The non-empty option labels for a question, in order."""
    return [o.get("label", "") for o in (question.get("options") or []) if o.get("label")]


def _pick(question, answers):
    """Choose an option label for one question. Thin wrapper over
    target_index_for so the index and label logic never drift."""
    labels = _labels(question)
    if not labels:
        return None
    return labels[target_index_for(question, answers)]


def choose_answers(tool_input, answers):
    """Map each question to (header/question, chosen label). Pure — unit tested."""
    out = []
    for q in tool_input.get("questions", []):
        label = _pick(q, answers)
        if label is not None:
            out.append({"header": q.get("header") or q.get("question", ""),
                        "answer": label})
    return out


def deny_payload(chosen):
    """A PreToolUse deny whose reason states the auto-selected answers so claude
    proceeds with them instead of waiting for a human."""
    if chosen:
        picks = "; ".join(f"{c['header']} -> {c['answer']}" for c in chosen)
        reason = ("[non-interactive recording] Auto-answered on the user's behalf: "
                  f"{picks}. Treat these as the user's chosen answers and continue "
                  "without asking again.")
    else:
        reason = ("[non-interactive recording] No interactive questions are "
                  "available; make a reasonable assumption and continue.")
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}


def allow_payload():
    """A PreToolUse allow so the AskUserQuestion selector renders on screen and an
    external driver answers it (render mode)."""
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
    }}


def handle(data, answers, mode, signal_dir):
    """Dispatch on mode.

    `auto`   -> DENY carrying the chosen answers (recording proceeds invisibly,
                never hangs). Writes NO signal file.
    `render` -> ALLOW (so the selector renders) and write a `pending_q.json`
                signal under signal_dir describing the FIRST question + options +
                the chosen target, so an external driver can pick it on screen.
    """
    tool_input = data.get("tool_input", {}) or {}
    questions = tool_input.get("questions", []) or []
    if mode == "render":
        if questions:
            q = questions[0]
            labels = _labels(q)
            ti = target_index_for(q, answers) or 0
            rec = {
                "header": q.get("header", ""),
                "question": q.get("question", ""),
                "options": labels,
                "target_index": ti,
                "target_label": labels[ti] if labels else None,
                "multiSelect": q.get("multiSelect", False),
            }
            os.makedirs(signal_dir, exist_ok=True)
            with open(os.path.join(signal_dir, "pending_q.json"), "w") as f:
                json.dump(rec, f)
        return allow_payload()
    # auto (default)
    chosen = choose_answers(tool_input, answers)
    return deny_payload(chosen)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    try:
        answers = json.loads(os.environ.get("VHS_ANSWERS", "") or "{}")
    except Exception:
        answers = {}
    if not isinstance(answers, dict):
        answers = {}
    mode = os.environ.get("VHS_QUESTION_MODE", "auto")
    signal_dir = os.environ.get("VHS_SIGNAL_DIR") or os.getcwd()
    out = handle(data, answers, mode, signal_dir)
    if out is not None:
        json.dump(out, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
