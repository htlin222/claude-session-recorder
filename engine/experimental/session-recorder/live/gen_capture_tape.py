#!/usr/bin/env python3
"""gen_capture_tape.py — script.json -> a MINIMAL VHS tape that films a real
Claude Code TUI for the v6 deterministic pipeline (Phase 0: capture).

The v6 change vs v5's gen_session_tape.py: the PER-TURN parts carry NO voice
here. v5 synthesized intro/think/outro up front and SIZED the soft Sleeps to fit
each clip; v6 instead captures the turns with FIXED tiny pads and re-times them
later by splicing freeze-frames against the synthesized narration.

The ONE exception is the LAUNCH. The launch is the deterministic shell region
(it runs BEFORE `claude` exists, so there is no nondeterministic think gap and
no reason to capture-then-splice it). So — exactly like v5 — the launch typing
is VOICE-PACED here: each flag is narrated FIRST, then its token is typed, so
the boot animation advances WITH the narration instead of holding one static
frame for ~15s while the launch narration plays. The launch voice clips are
synthesized in main() and their raw onsets recorded in capture.json for author
to reuse (it does NOT re-synth the launch). The per-turn parts stay voice-free.

It films `terminal_raw.mp4` and writes a `capture.json` describing the structure
detect_anchors needs: n turns, per-turn `type_dur`, prompts, launch token list.

Inputs : script.json (see script.example.json) — only `launch.base`,
         `launch.flags[].arg`, and `turns[].prompt` are read here; the voice
         fields (intro/think/outro/say/note/close) are ignored at this stage.
Outputs: <demo>/session.tape + <demo>/capture.json

Prereq : run claude_sandbox.sh <demo> first; render the tape from <demo>/.
Example:
  ./claude_sandbox.sh /tmp/sess
  python3 gen_capture_tape.py --demo /tmp/sess --script script.example.json
  cd /tmp/sess && vhs session.tape   # -> terminal_raw.mp4 + session-timeline.jsonl
"""
import argparse
import json
import os
import subprocess

import qnav

THEMES = {"dark": "Catppuccin Mocha", "light": "Catppuccin Latte"}
PAD = 0.4          # fixed tiny soft pad around each action (no voice sizing)
DONE_HOLD = 3.0    # hold after each turn's Stop sentinel so the SETTLED result is
                   # captured stable (else detection/tail-freeze land on the still-
                   # running frame and the ending freezes mid-execution)
INSTANT_SETTLE = 1.8   # fixed settle Sleep for a turn whose prompt is handled
                       # ENTIRELY client-side (no model/agent turn runs, so the
                       # Stop hook — and its VHS_TURN_DONE_N sentinel — never
                       # fires; Wait+Screen would just burn the full turn-timeout).
                       # 1.8s is enough for the client-side UI to redraw (banner /
                       # mode switch / clear) before the tape moves on; DONE_HOLD
                       # still runs afterward to hold the settled frame.

# NATIVE_MENU_SETTLE (issue #17): /theme, /rewind, /memory, /plugin install DO
# paint an on-screen menu (unlike the no-menu INSTANT_COMMANDS above) — but
# selecting an option STILL fires no Stop hook (confirmed via a live tmux
# probe), so they need the same "skip the sentinel Wait" treatment. The
# difference: under --robust/--tmux, a background qmonitor.py is the one
# actually driving that menu (see qmonitor._answer_one), and the tape must not
# move on to the next turn's typing before qmonitor's cycle has finished.
# Sized from qmonitor's own defaults (max_wait=60s is just its own per-wait
# ceiling, not a target): read_dwell (2.5s, dwell before the first keystroke)
# + a generous 5 keystrokes at key_gap (0.8s) for a single-level menu with a
# handful of options (Down x<=4 + Enter) = ~4.0s + a couple of poll (0.3s)
# cycles for the post-answer confirmation match (~0.6s). That's ~7.1s in the
# realistic case; round up to 10s for comfortable headroom without anywhere
# approaching qmonitor's own 60-90s worst-case ceilings (which would defeat
# the point of not hanging the capture wait).
NATIVE_MENU_SETTLE = 10.0

# Slash commands handled ENTIRELY client-side by Claude Code — no model turn
# happens, so no Stop hook fires for them. Matched on the prompt's LEADING
# token (handles args, e.g. "/model opus", "/rename foo"). A value of True
# means the command is instant regardless of its args; a set means only those
# specific first-arg subcommands are instant (e.g. "/tui fullscreen" is, but
# other "/tui ..." subcommands may still invoke the model).
INSTANT_COMMANDS = {
    "/rename": True,
    "/branch": True,
    "/context": True,
    "/usage": True,
    "/clear": True,
    "/model": True,
    "/effort": True,
    "/fast": {"on", "off"},
    "/tui": {"fullscreen"},
}


# Slash commands that DO paint a native on-screen menu (the same selector
# widget AskUserQuestion uses — qnav.FOOTER_RE/qparse recognize it) but STILL
# fire no Stop hook once an option is picked (issue #17: confirmed via a live
# tmux probe for /theme; qmonitor.py's docstring/#14 lists the same set as the
# native-menu commands it polls for and answers). Same leading-token +
# optional-subcommand-set shape as INSTANT_COMMANDS. `/plugin` has OTHER
# subcommands (list, uninstall, ...) that do NOT show the scope-picker menu —
# only "install" does, so it's matched conservatively as a subcommand set,
# not `True`.
NATIVE_MENU_COMMANDS = {
    "/theme": True,
    "/rewind": True,
    "/memory": True,
    "/plugin": {"install"},
}


def _match_command_table(prompt, table):
    """Shared leading-token (+ optional required subcommand) matcher used by
    both _is_instant_command and _is_native_menu_command: `table` maps a
    leading token to either True (any/no args match) or a set of the ONLY
    second-token subcommands that match."""
    parts = prompt.strip().split()
    if not parts or not parts[0].startswith("/"):
        return False
    spec = table.get(parts[0])
    if spec is None:
        return False
    if spec is True:
        return True
    return len(parts) > 1 and parts[1] in spec


def _is_instant_command(prompt):
    """True iff `prompt` is one of the known ENTIRELY-client-side/instant slash
    commands (see INSTANT_COMMANDS) — such a turn never fires the Stop hook, so
    the capture tape must not Wait+Screen on its sentinel."""
    return _match_command_table(prompt, INSTANT_COMMANDS)


def _is_native_menu_command(prompt):
    """True iff `prompt` is one of the known NATIVE-menu slash commands (see
    NATIVE_MENU_COMMANDS) — these DO paint an on-screen menu (qmonitor.py
    drives it under --robust), but STILL fire no Stop hook, so the capture
    tape must not Wait+Screen on its sentinel either (issue #17)."""
    return _match_command_table(prompt, NATIVE_MENU_COMMANDS)


PRELUDE = 2.0      # Sleep before the launch typing (shell prompt settles)
PRE_ENTER = 0.4    # beat after typing finishes, before Enter
LBREATH = 0.5      # breath after each voice-paced launch token (== ledger BREATH)
QSEE = 1.5         # dwell on the rendered AskUserQuestion selector (viewer reads it)
QSTEP = 0.5        # beat between selector navigation keys (highlight move is visible)

VOICE = "zh-TW-HsiaoChenNeural"
RATE = "+0%"


def vhs_type(text):
    """Return a list of one or more `Type '...'`/`Type "..."` lines that,
    typed back-to-back, reproduce `text` exactly.

    VHS's tape grammar has no backslash-escape for quotes inside a `Type
    "..."` line, so a literal `"` (or `'`) in the text would otherwise break
    the line with `Invalid command: ...`. Pick whichever delimiter `text`
    doesn't contain; when it contains BOTH (e.g. a `--mcp-config` JSON blob
    mixing `'` and `"`), split into consecutive `Type` lines, switching
    delimiter each time the OTHER delimiter char is encountered so no line's
    body ever contains its own delimiter."""
    if '"' not in text:
        return [f'Type "{text}"']
    if "'" not in text:
        return [f"Type '{text}'"]
    lines = []
    cur = ""
    delim = '"' if text[0] != '"' else "'"
    for ch in text:
        if ch == delim:
            lines.append(f"Type {delim}{cur}{delim}")
            delim = "'" if delim == '"' else '"'
            cur = ch
        else:
            cur += ch
    lines.append(f"Type {delim}{cur}{delim}")
    return lines


def synth(text, out_mp3):           # I/O boundary (mirrors author.synth)
    subprocess.run(["edge-tts", "--voice", VOICE, "--rate", RATE,
                    "--text", text, "--write-media", out_mp3],
                   check=True, capture_output=True)
    return _dur(out_mp3)


def _dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout or 0)


def render(spec, demo, width, height, font_size, word_delay,
           startup_to=60, turn_to=120, theme="Catppuccin Mocha",
           launch_voice=None, launch_outro=None, tmux=None):
    """Pure: build (tape_str, plan) from spec. Writes NOTHING to disk.

    `launch_voice` (optional): a list of `{token, text, mp3, dur}` for the
    base+each-flag launch beats; `launch_outro` an optional `{text, mp3, dur}`.
    When provided, the launch is VOICE-PACED — each token's narration plays
    (`Sleep <dur>`) BEFORE the token is typed, so the boot animation advances
    WITH the narration instead of being freeze-extended for ~15s. The launch is
    the deterministic shell region (it runs before `claude` exists, so there is
    no nondeterministic think gap), so sizing it to the voice here is safe.
    When None, the legacy fixed-PAD path is used (unit tests / back-compat).

    `tmux` (optional): `{"socket": <name>, "name": <session>}`. When set, the
    WHOLE claude session is filmed INSIDE a dedicated-socket, status-off tmux
    (a robustness safety net: a bg `qmonitor.py` can answer ANY on-screen
    AskUserQuestion). The tmux START is emitted INVISIBLY (Hide…Show) BEFORE the
    launch, so the recording resumes on a clean in-pane shell prompt and the
    flag-by-flag CLI lesson (`Type "claude --flags"`) is preserved untouched.
    The answer policy (VHS_ANSWERS) is NEVER a tape Env — it can carry chars VHS
    cannot parse, so the driver passes it via the real process env instead."""
    turns = spec["turns"]
    cfg = os.path.join(os.path.abspath(demo), ".cfg")
    timeline = os.path.join(os.path.abspath(demo), "session-timeline.jsonl")

    lc = spec.get("launch", {"base": "claude", "flags": []})
    base = lc.get("base", "claude")
    flags = lc.get("flags", [])
    tokens = [base] + [f["arg"] for f in flags]

    L = []
    a = L.append
    a("# Auto-generated by gen_capture_tape.py — minimal prompts-only capture tape")
    a("# (no voice, fixed pads). Prereq: claude_sandbox.sh <demo>.")
    a("Output terminal_raw.mp4")
    a("")
    a(f"Set FontSize {font_size}")
    a(f"Set Width {width}")
    a(f"Set Height {height}")
    a(f'Set Theme "{theme}"')
    a("Set TypingSpeed 0ms        # word-by-word reveal via explicit Sleeps")
    a("")
    a('Env VHS_DEMO "1"')
    a(f'Env CLAUDE_CONFIG_DIR "{cfg}"')
    a(f'Env VHS_TIMELINE "{timeline}"')
    # Clean SHELL PROMPT. The killer: VHS defaults to bash, which inherits the
    # EXPORTED zsh-syntax `PS1` from the p10k shell this runs in and renders it as
    # literal `${_p9k_…}` garbage full-screen at boot AND on Ctrl+C exit — both
    # uglifying the opening/closing frames and reading as two extra full-bright
    # "prompt submissions" that break detect_turns (4 detected vs 2). Overriding
    # PS1/PROMPT in the tape kills the dump regardless of which shell VHS picks.
    # ZDOTDIR (clean .zshrc) is kept as defense-in-depth for the zsh path.
    a('Env PS1 "❯ "')
    a('Env PROMPT "❯ "')
    a(f'Env ZDOTDIR "{os.path.join(cfg, "zdotdir")}"')
    # Prompt-suggestion ghost text: when a reply reads like an invitation to a
    # next step, Claude Code populates that suggestion as grey ghost text in
    # the empty input box. This has coincided with the NEXT scripted turn's
    # typing silently failing to register (idle for the full Wait timeout).
    # Disabling suggestions during capture made the symptom disappear.
    a('Env CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION "false"')
    # When a turn expects an AskUserQuestion, the tape must navigate a LIVE selector,
    # so claude runs in render-mode (the hook lets the selector paint instead of
    # auto-answering). Default stays "auto" (hang-proof) when no turn asks.
    has_question = any(t.get("question") for t in turns)
    if has_question:
        a('Env VHS_QUESTION_MODE "render"')
        a(f'Env VHS_SIGNAL_DIR "{os.path.abspath(demo)}"')
    a("")
    if tmux:
        # tmux MODE: start the dedicated-socket, status-off tmux INVISIBLY so the
        # recording resumes on a clean in-pane shell prompt. The Env lines above
        # are inherited by `exec $SHELL` here, so the in-tmux prompt stays clean,
        # and the launch typing below runs INSIDE this pane (CLI lesson preserved).
        sock, name = tmux["socket"], tmux["name"]
        conf = os.path.join(os.path.abspath(demo), "tmux.conf")
        a("Hide")
        a(f'Type "tmux -L {sock} -f {conf} new-session -A -s {name} '
          "'exec $SHELL'\"")
        a("Enter")
        a("Sleep 800ms")
        a("Show")
        a("")
    a(f"Sleep {PRELUDE:.0f}s                   # let the shell prompt settle")
    launch_plan = {"tokens": tokens, "base": base, "flags": flags}
    if launch_voice:
        # VOICE-PACED launch: narrate each token FIRST (Sleep<dur>), THEN type it,
        # then a breath. Tracks cumulative raw tape time so each beat's onset `at`
        # (when its narration Sleep begins) is recorded for author to reuse. The
        # outro plays during the boot Wait, so it needs no extra Sleep here — only
        # its onset (the Enter time) is recorded.
        cur = float(PRELUDE)
        beats_plan = []
        for bi, lv in enumerate(launch_voice):
            tok, d = lv["token"], float(lv["dur"])
            at = round(cur, 3)
            note = "narrate intro" if bi == 0 else "narrate flag, token not shown yet"
            a(f"Sleep {d:.3f}s   # {note}")
            for line in vhs_type(tok if bi == 0 else " " + tok):
                a(line)
            a(f"Sleep {LBREATH:.3f}s   # breath after the token appears")
            beats_plan.append({"token": tok, "text": lv.get("text", ""),
                               "mp3": lv["mp3"], "dur": round(d, 3), "at": at})
            cur += d + LBREATH
        a("Enter")
        a(f"Wait+Screen@{startup_to}s /shift\\+tab|for shortcuts/")
        launch_plan["beats"] = beats_plan
        if launch_outro:
            launch_plan["outro"] = {"text": launch_outro.get("text", ""),
                                    "mp3": launch_outro["mp3"],
                                    "dur": round(float(launch_outro["dur"]), 3),
                                    "at": round(cur, 3)}    # rides boot from Enter
    else:
        # LEGACY fixed-PAD launch: typed token-by-token with a fixed PAD between
        # tokens. No narration (back-compat / unit tests).
        for ti, tok in enumerate(tokens):
            for line in vhs_type(tok if ti == 0 else " " + tok):
                a(line)
            a(f"Sleep {PAD:.3f}s   # fixed pad after token")
        a("Enter")
        a(f"Wait+Screen@{startup_to}s /shift\\+tab|for shortcuts/")
    a("")

    plan = {
        "launch": launch_plan,
        "pre_enter": PRE_ENTER, "prelude": PRELUDE, "pad": PAD,
        "turns": [],
    }
    for i, t in enumerate(turns, 1):
        words = t["prompt"].split(" ")
        type_dur = round(len(words) * word_delay / 1000.0, 3)
        a(f"# --- Turn {i} ---")
        a(f"Sleep {PAD:.3f}s   # pre-prompt pad")
        for w, word in enumerate(words):
            for line in vhs_type(word if w == 0 else " " + word):
                a(line)
            a(f"Sleep {word_delay}ms")
        a(f"Sleep {PRE_ENTER:.3f}s          # beat before Enter")
        a("Enter")
        instant = _is_instant_command(t["prompt"])
        # native-menu commands (/theme, /rewind, /memory, /plugin install):
        # DO paint an on-screen menu, but fire no Stop hook either — so they
        # need the same sentinel-skip as `instant` above (issue #17). This
        # check does NOT depend on `tmux` (whether a Stop hook fires is a
        # property of the COMMAND, true in both --robust and standard mode);
        # only the SETTLE DURATION below is mode-dependent, since only
        # --robust mode actually runs a qmonitor to drive the menu.
        native_menu = _is_native_menu_command(t["prompt"])
        turn_plan = {"index": i, "prompt": t["prompt"], "type_dur": type_dur}
        if instant or native_menu:
            # ENTIRELY client-side command (e.g. /rename, /fast on) OR a
            # native-menu command (e.g. /theme): no model turn runs, so
            # VHS_TURN_DONE_{i} never prints — mark it distinctly so
            # downstream stages (e.g. panel.py's UserPromptSubmit/Stop
            # alignment) don't expect a Stop-hook JSONL entry for this turn.
            # Both cases share the exact same "instant" flag/shape so every
            # downstream consumer only has to know about ONE key.
            turn_plan["instant"] = True
        else:
            turn_plan["sentinel"] = f"VHS_TURN_DONE_{i}"
        question = t.get("question")
        if question:
            # WAIT for the live AskUserQuestion selector to paint (qnav.FOOTER_RE),
            # then dwell so the viewer reads it, then NAVIGATE to the chosen option
            # (Down/Up x delta) with a beat between keys so the highlight move is
            # visible and a beat before the final Enter selects. THEN fall through to
            # the sentinel wait. qnav.FOOTER_RE is a VHS-SAFE substring (`to
            # navigate`): VHS's tape parser cannot handle a literal `/` (no `\/`
            # escape) nor the Unicode arrows `↑↓` inside a Wait+Screen regex.
            a(f"Wait+Screen@{turn_to}s /{qnav.FOOTER_RE}/   "
              "# AskUserQuestion selector footer appeared")
            a(f"Sleep {QSEE:.3f}s   # dwell on the question (viewer reads it)")
            keys = qnav.keys_to_select(question["answer_index"], 0)
            for ki, key in enumerate(keys):
                if ki > 0:
                    a(f"Sleep {QSTEP:.3f}s   # beat so the highlight move is visible")
                a(key)
            turn_plan["question"] = {"answer_index": question["answer_index"]}
        if instant and not native_menu:
            # No Stop hook will ever fire for this turn — Wait+Screen on its
            # sentinel would reliably time out (burning the full turn_to
            # timeout). Use a short fixed settle Sleep instead.
            a(f"Sleep {INSTANT_SETTLE:.3f}s   # client-side command settles "
              "instantly — no Stop hook/sentinel will ever fire for it")
            # Record the ACTUAL settle duration used (issue #18): two
            # "instant"-flagged turns back-to-back can merge into one detected
            # pixel group downstream (no thinking-gap to split on), and
            # detect_anchors.py recovers by re-deriving the split points from
            # this KNOWN scripted timing rather than raising. Both the
            # no-menu (here) and native-menu (below) paths share the same
            # "instant" flag/shape but can use DIFFERENT settle durations, so
            # the recovery must read the one actually used per-turn instead of
            # assuming INSTANT_SETTLE universally.
            turn_plan["settle"] = INSTANT_SETTLE
        elif native_menu:
            # Same "no Stop hook will ever fire" reasoning as `instant`, but
            # this command paints a real on-screen menu first. Under
            # --robust/--tmux, a background qmonitor.py is the one actually
            # navigating that menu (poll for footer -> dwell -> keystrokes ->
            # confirm poll) — the tape must give it real wall-clock time to
            # finish BEFORE typing the next turn's prompt into what could
            # still be an open menu. In STANDARD (non-tmux) mode there is no
            # qmonitor at all, so the menu never gets navigated regardless of
            # how long we sleep here (that scenario is not supported by this
            # fix — see issue #17); since there's no real answer-cycle to
            # wait out, fall back to the short INSTANT_SETTLE so we at least
            # don't burn the full turn-timeout on an unreachable sentinel.
            settle = NATIVE_MENU_SETTLE if tmux else INSTANT_SETTLE
            a(f"Sleep {settle:.3f}s   # native menu (e.g. /theme) settles — "
              "no Stop hook/sentinel will ever fire for it either")
            turn_plan["settle"] = settle    # see the `instant` branch's comment
        else:
            a(f"Wait+Screen@{turn_to}s /VHS_TURN_DONE_{i}/   # HARD axis: real think gap")
        # HOLD on the COMPLETED frame after the Stop sentinel prints, so the
        # finished result (claude's final message + the `VHS_TURN_DONE` line) is
        # captured STABLE. Without this the tape tore down ~0.4s after the
        # sentinel, so `done` detection + the tail freeze landed on the still-
        # running frame BEFORE the result settled — the video then froze on a
        # "Running… / Drizzling" frame instead of the result.
        a(f"Sleep {DONE_HOLD:.3f}s   # hold on the settled result + sentinel")
        a("")
        plan["turns"].append(turn_plan)
    # teardown
    a("Sleep 500ms")
    a("Ctrl+C")
    a("Sleep 500ms")
    a("Ctrl+C")
    a("Sleep 1s")
    return "\n".join(L) + "\n", plan


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", required=True, help="sandbox dir (from claude_sandbox.sh)")
    ap.add_argument("--script", required=True, help="script.json (prompt per turn)")
    ap.add_argument("-o", "--output", default=None, help="tape path (default <demo>/session.tape)")
    ap.add_argument("--theme", choices=THEMES, default="dark")
    ap.add_argument("--font-size", type=int, default=27)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--word-delay", type=int, default=220, help="ms between prompt words")
    ap.add_argument("--startup-timeout", type=int, default=60)
    ap.add_argument("--turn-timeout", type=int, default=120)
    ap.add_argument("--tmux", action="store_true",
                    help="film the session INSIDE a dedicated-socket tmux "
                         "(a bg qmonitor.py answers any on-screen question)")
    ap.add_argument("--tmux-socket", default="vhsq",
                    help="dedicated tmux socket/session name for --tmux")
    args = ap.parse_args()
    spec = json.load(open(args.script, encoding="utf-8"))
    tape_path = args.output or os.path.join(args.demo, "session.tape")

    # Synthesize the LAUNCH voice up front (this is the only voice the capture
    # tape needs — the launch is the deterministic shell region, so its typing is
    # paced to the narration here; the per-turn intro/think/outro stay voice-free).
    lc = spec.get("launch", {}) or {}
    launch_voice, launch_outro = None, None
    if lc.get("intro") or any(f.get("say") for f in lc.get("flags", [])):
        voice_dir = os.path.join(args.demo, "_voice")
        os.makedirs(voice_dir, exist_ok=True)
        base = lc.get("base", "claude")
        launch_voice = []
        intro = lc.get("intro", "")
        bm = os.path.join(voice_dir, "open_intro.mp3")
        bd = synth(intro, bm) if intro else 0.0
        launch_voice.append({"token": base, "text": intro,
                             "mp3": os.path.relpath(bm, args.demo), "dur": round(bd, 3)})
        for k, f in enumerate(lc.get("flags", [])):
            say, arg = f.get("say", ""), f["arg"]
            m = os.path.join(voice_dir, f"open_flag{k}.mp3")
            d = synth(say, m) if say else 0.0
            launch_voice.append({"token": arg, "text": say,
                                 "mp3": os.path.relpath(m, args.demo), "dur": round(d, 3)})
        outro_txt = lc.get("outro", "")
        if outro_txt:
            om = os.path.join(voice_dir, "open_outro.mp3")
            launch_outro = {"text": outro_txt, "mp3": os.path.relpath(om, args.demo),
                            "dur": round(synth(outro_txt, om), 3)}

    tmux = {"socket": args.tmux_socket, "name": args.tmux_socket} if args.tmux else None
    tape, plan = render(spec, args.demo, args.width, args.height, args.font_size,
                        args.word_delay, args.startup_timeout, args.turn_timeout,
                        THEMES[args.theme], launch_voice=launch_voice,
                        launch_outro=launch_outro, tmux=tmux)
    open(tape_path, "w").write(tape)
    json.dump(plan, open(os.path.join(args.demo, "capture.json"), "w"),
              ensure_ascii=False, indent=2)
    print(f"wrote {tape_path}  ({len(spec['turns'])} turns)")
    print(f"wrote {os.path.join(args.demo, 'capture.json')}")


if __name__ == "__main__":
    main()
