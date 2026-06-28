#!/usr/bin/env python3
"""record-session — one unified driver for the v6 session-recorder pipeline.

This single entry point replaces the two ad-hoc shell drivers:

  * run_v6.sh       -> the STANDARD pipeline (this script, default)
  * run_v6_tmux.sh  -> the ROBUST pipeline  (this script, --robust)

Pipeline stages (both paths):
    claude_sandbox.sh -> gen_capture_tape.py -> vhs (capture)
    -> author.py -> splice.py -> overlay.py -> panel.py -> lint.py

The --robust path additionally films claude INSIDE a dedicated-socket tmux that
VHS renders, while a BACKGROUND qmonitor.py answers ANY on-screen
AskUserQuestion. The answer policy is passed via the REAL process env
(VHS_ANSWERS) because a VHS tape `Env` line cannot escape quotes.

Hard-won subtleties preserved from the shell drivers:
  * export SR and HERE before vhs — the sandbox's claude-spawned project hooks
    resolve $SR/timelog.py and $HERE/vhs_stop_sentinel.sh.
  * scrub the inherited prompt env (PS1/PROMPT/_P9K_TTY/_P9K_SSH_TTY) before vhs;
    VHS defaults to bash and would otherwise dump an exported p10k PS1 full-screen.
  * remove the shared SR/session-timeline.jsonl before vhs.
  * --robust: VHS_ANSWERS MUST go via the process env, never a tape Env line.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# ── locations ────────────────────────────────────────────────────────────────
LIVE = Path(__file__).resolve().parent           # the live/ package dir
SR = LIVE.parent                                  # session-recorder/ (parent dir)
REPO = SR.parent.parent.parent                    # repo root (../../.. from SR)

#: prefer the repo venv python so the pipeline modules import their deps; fall
#: back to whatever interpreter is running this script.
_VENV_PY = REPO / ".venv" / "bin" / "python"
PY = str(_VENV_PY) if _VENV_PY.exists() else sys.executable

#: prompt env vars that must be scrubbed before handing control to vhs/bash.
_PROMPT_VARS = ("PS1", "PROMPT", "_P9K_TTY", "_P9K_SSH_TTY")

TMUX_SOCKET = "vhsq"   # dedicated tmux socket/server (never the user's default)
TMUX_NAME = "vhsq"     # tmux session name qmonitor polls

TMUX_CONF = (
    "# invisible tmux for VHS recording: no status bar, no mouse capture.\n"
    "set -g status off\n"
    "set -g mouse off\n"
)


# ── stage helpers ────────────────────────────────────────────────────────────
def _run(cmd, *, stage, env=None, cwd=None, hint=None):
    """Stream a stage; on failure print a clear message and exit non-zero."""
    print(f"-- {stage}: {' '.join(str(c) for c in cmd)}", flush=True)
    rc = subprocess.call([str(c) for c in cmd], env=env, cwd=cwd)
    if rc != 0:
        msg = f"\n!! stage FAILED: {stage} (exit {rc})"
        if hint:
            msg += f"\n   {hint}"
        print(msg, file=sys.stderr, flush=True)
        sys.exit(rc)


def _capture_env(demo: Path, *, answers: str | None = None, robust: bool = False) -> dict:
    """Build the vhs process env: scrub prompt vars, export SR/HERE, add answers."""
    env = os.environ.copy()
    for var in _PROMPT_VARS:
        env.pop(var, None)
    # The sandbox's claude-spawned project hooks resolve these.
    env["SR"] = str(SR)
    env["HERE"] = str(LIVE)
    if robust:
        env["VHS_QUESTION_MODE"] = "render"
        env["VHS_SIGNAL_DIR"] = str(demo)
        # default {"*":0} == always pick the FIRST option for unknown questions.
        env["VHS_ANSWERS"] = answers if answers is not None else '{"*":0}'
    elif answers is not None:
        # standard run_v6.sh sets no VHS_ANSWERS; only pass it if explicitly asked.
        env["VHS_ANSWERS"] = answers
    return env


def _wipe_timeline():
    """rip -f the shared SR/session-timeline.jsonl before vhs (idempotent)."""
    tl = SR / "session-timeline.jsonl"
    try:
        tl.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _post_capture(demo: Path, script: Path):
    """Stages identical across both paths: author -> splice -> overlay -> panel -> lint."""
    _run([PY, LIVE / "author.py", "--demo", demo, "--script", script], stage="author")
    _run([PY, LIVE / "splice.py", "--demo", demo], stage="splice")
    _run([PY, LIVE / "overlay.py", "--demo", demo], stage="overlay")
    _run([PY, LIVE / "panel.py", "--demo", demo], stage="panel")
    _run([PY, LIVE / "lint.py", "--demo", demo, "--filmstrip"], stage="lint")
    print(f"== done: {demo / 'session_panel.mp4'} ==", flush=True)


# ── pipelines ────────────────────────────────────────────────────────────────
def run_standard(demo: Path, script: Path, args) -> None:
    """The run_v6.sh flow."""
    print("== v6 pipeline ==", flush=True)
    # Phase 0a — isolated sandbox (idempotent)
    _run(["bash", LIVE / "claude_sandbox.sh", demo], stage="sandbox")
    # Phase 0b — minimal capture tape + capture.json (no voice)
    _run([
        PY, LIVE / "gen_capture_tape.py",
        "--demo", demo, "--script", script,
        "--width", args.width, "--height", args.height, "--font-size", args.font_size,
        "-o", demo / "session.tape",
    ], stage="gen_capture_tape")
    # Phase 0c — film the real TUI ONCE (claude launches here, and ONLY here).
    _wipe_timeline()
    env = _capture_env(demo, answers=args.answers, robust=False)
    _run(
        ["vhs", "session.tape"], stage="vhs (capture)", env=env, cwd=demo,
        hint=f"inspect the vhs output above and the tape at {demo / 'session.tape'}",
    )
    # Phase 1..3 — author/splice/overlay/panel/lint
    _post_capture(demo, script)


def run_robust(demo: Path, script: Path, args) -> None:
    """The run_v6_tmux.sh flow."""
    print("== v6 tmux pipeline ==", flush=True)
    # Phase 0a — isolated sandbox (idempotent)
    _run(["bash", LIVE / "claude_sandbox.sh", demo], stage="sandbox")
    # Phase 0a' — status-off tmux config so the rendered pane shows NO tmux chrome.
    (demo / "tmux.conf").write_text(TMUX_CONF)
    # Phase 0b — tmux-mode capture tape (the whole session runs inside tmux -L vhsq)
    _run([
        PY, LIVE / "gen_capture_tape.py",
        "--demo", demo, "--script", script,
        "--tmux", "--tmux-socket", TMUX_SOCKET,
        "--width", args.width, "--height", args.height, "--font-size", args.font_size,
        "-o", demo / "session.tape",
    ], stage="gen_capture_tape")
    # Phase 0c — film the real TUI ONCE inside tmux. claude launches here, ONLY here.
    _wipe_timeline()
    # Clean slate on our PRIVATE socket (never touches the user's default server).
    subprocess.call(["tmux", "-L", TMUX_SOCKET, "kill-server"],
                    stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    # Background safety net: qmonitor drives the on-screen selector for ANY question.
    qlog_path = demo / "qmonitor.log"
    qlog = open(qlog_path, "w")
    monitor = subprocess.Popen(
        [PY, str(LIVE / "qmonitor.py"),
         "--session", TMUX_NAME, "--socket", TMUX_SOCKET,
         "--signal-dir", str(demo), "--max-wait", "90"],
        stdout=qlog, stderr=subprocess.STDOUT,
    )
    print(f"-- qmonitor: background pid {monitor.pid} -> {qlog_path}", flush=True)
    try:
        env = _capture_env(demo, answers=args.answers, robust=True)
        _run(
            ["vhs", "session.tape"], stage="vhs (capture)", env=env, cwd=demo,
            hint=f"inspect the vhs output above and the monitor log at {qlog_path}",
        )
    finally:
        # Stop the monitor and tear down our private tmux server.
        (demo / ".qmonitor_stop").touch()
        monitor.terminate()
        try:
            monitor.wait(timeout=10)
        except subprocess.TimeoutExpired:
            monitor.kill()
        qlog.close()
        subprocess.call(["tmux", "-L", TMUX_SOCKET, "kill-server"],
                        stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    # Phase 1..3 — author/splice/overlay/panel/lint
    _post_capture(demo, script)


# ── cli ──────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="record-session",
        description="Record a narrated, sync-verified video of a real Claude Code "
                    "TUI session (v6 pipeline). One driver, two paths.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("demo", help="demo / sandbox dir (created by claude_sandbox.sh)")
    p.add_argument("script", help="script.json (one prompt per turn)")
    p.add_argument("--robust", action="store_true",
                   help="robust tmux+qmonitor path (run_v6_tmux.sh): film claude "
                        "inside a dedicated-socket tmux with a background answerer")
    p.add_argument("--answers", default=None, metavar="JSON",
                   help='auto-answer policy passed via VHS_ANSWERS, e.g. \'{"*":1}\' '
                        '(robust default: {"*":0} = first option for unknown Qs)')
    p.add_argument("--width", type=int, default=1200, help="capture width (px)")
    p.add_argument("--height", type=int, default=1080, help="capture height (px)")
    p.add_argument("--font-size", type=int, default=26, help="capture font size (px)")
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    demo = Path(args.demo).resolve()
    script = Path(args.script).resolve()
    demo.mkdir(parents=True, exist_ok=True)
    if not script.exists():
        print(f"!! script not found: {script}", file=sys.stderr)
        sys.exit(2)
    if args.robust:
        run_robust(demo, script, args)
    else:
        run_standard(demo, script, args)


if __name__ == "__main__":
    main()
