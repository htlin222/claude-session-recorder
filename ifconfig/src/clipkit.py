#!/usr/bin/env python3
"""Lesson abstraction for the CLI-education pipeline.

A *lesson* is the ONLY thing that changes between videos: the narration, the
commands, the per-token panel annotations, and the throwaway environment those
commands run against. Everything else — the timing/sync model, tape generation,
panel compositing, scene transitions — is tool-agnostic and lives in build.py /
overlay.py. To teach a different CLI tool you write a new lesson; you never
touch the engine.

A lesson lives in  lessons/<name>/  and consists of:

    lesson.py   defines three module-level names:
                  SLUG   str  - output basename (dist/<SLUG>.mp4 / .srt / .html)
                  TITLE  str  - human title (logs / HTML player)
                  SCRIPT list - the timeline, built from S()/R()/CLR() below
    setup.sh    (re)creates this lesson's demo environment inside intermediate/
                in a known initial state; run once before each `vhs` render.

Lessons import the three builders from here:  `from lesson import S, R, CLR`
(this works because build.py runs with src/ on sys.path and loads the lesson
module by path — see load() below). Lessons are NOT meant to be run standalone.

Panel token roles -> colour (rendered by overlay.ROLE). These are generic, not
tied to any one tool:
    ord   an ordinary flag/option            (green)
    star  the scenario's KEY flag/idea       (peach)
    path  operands / paths / arguments       (mauve)
"""
import importlib.util
import os

# A continuous narration sentence (the voice never stops); an on-screen command
# to run; and a scene break that opens the right-hand explain panel.
S = lambda t: ("say", t)
R = lambda c: ("run", c)


def CLR(key=None, hero=None, toks=None):
    """Open a scene and carry its right-panel data.

    key  one-line headline for the panel (None = bare clear, no banner).
    hero the command to dissect token by token (None = no command this scene).
    toks [(substr, annotation, role), ...] — each revealed the instant its
         token finishes typing, so the narration walks the flags in order.
    """
    return ("clear", key, hero, toks or [])


def load_lesson(path):
    """Import a self-contained slug's lesson.py (at the slug-folder root) and
    return the validated module. In the portable per-slug layout there is exactly
    ONE lesson per folder, so we load it by path rather than by name from a shared
    lessons/ dir."""
    if not os.path.exists(path):
        raise SystemExit(f"lesson not found: {path}")
    spec = importlib.util.spec_from_file_location("lesson", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for attr in ("SLUG", "TITLE", "SCRIPT"):
        if not hasattr(mod, attr):
            raise SystemExit(f"lesson {path} is missing required `{attr}`")
    return mod
