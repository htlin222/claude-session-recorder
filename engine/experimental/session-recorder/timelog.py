#!/usr/bin/env python3
"""Claude Code hook: append (time, event, detail) for each fired hook event to a
JSONL timeline. Wired to many events in .claude/settings.json (see README).

Claude Code provides NO timestamp in the hook payload, so we capture our own
(epoch seconds, ms precision). Post-hoc, gen_voiceover.py turns this timeline
into a timecode-matched narration of the session. The hook never blocks.

Reads the hook JSON on stdin; writes to session-recorder/session-timeline.jsonl.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "session-timeline.jsonl")


def detail(d):
    """One concise human bit describing this event, for the voiceover."""
    ev = d.get("hook_event_name", "")
    tool = d.get("tool_name")
    if tool:                                    # PreToolUse / PostToolUse / ...
        ti = d.get("tool_input", {}) or {}
        bit = (ti.get("command") or ti.get("file_path") or ti.get("path")
               or ti.get("pattern") or ti.get("description") or "")
        return f"{tool} {str(bit)[:100]}".strip()
    return {
        "UserPromptSubmit": (d.get("prompt", "")[:120]),
        "SessionStart": d.get("source", ""),
        "SessionEnd": d.get("end_reason", ""),
        "Notification": d.get("message", "")[:120],
        "SubagentStart": d.get("agent_type", ""),
        "TaskCreated": d.get("task_name", ""),
        "TaskCompleted": d.get("task_name", ""),
        "FileChanged": f"{d.get('change_type','')} {d.get('file_path','')}",
    }.get(ev, "")


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:                           # noqa: BLE001
        d = {}
    rec = {
        "t": round(time.time(), 3),
        "event": d.get("hook_event_name", "unknown"),
        "detail": detail(d),
    }
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:                           # never let logging break the session
        pass
    sys.exit(0)                                 # exit 0, no stdout -> non-blocking


if __name__ == "__main__":
    main()
