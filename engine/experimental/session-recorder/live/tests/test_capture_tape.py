import gen_capture_tape as g
import qnav  # noqa  (ensure importable)

SPEC = {
    "launch": {"base": "claude", "flags": [{"arg": "--model opus"}]},
    "turns": [{"prompt": "write fizzbuzz"}, {"prompt": "add a test"}],
}


def test_tape_has_minimal_fixed_pads_and_no_voice(tmp_path):
    tape, plan = g.render(SPEC, demo=str(tmp_path), width=1200, height=1080,
                          font_size=26, word_delay=220)
    # one sentinel wait per turn, in order
    assert "VHS_TURN_DONE_1" in tape and "VHS_TURN_DONE_2" in tape
    # launch typed token-by-token: base then each flag
    assert 'Type "claude"' in tape and 'Type " --model opus"' in tape
    # NO voice-sized sleeps: pads are the fixed PAD constant only
    assert f"Sleep {g.PAD:.3f}s" in tape
    # capture.json carries type_dur per turn for typing_start derivation
    assert plan["turns"][0]["type_dur"] > 0
    assert plan["turns"][0]["prompt"] == "write fizzbuzz"
    assert len(plan["turns"]) == 2


def test_capture_plan_lists_launch_tokens(tmp_path):
    _tape, plan = g.render(SPEC, demo=str(tmp_path), width=1200, height=1080,
                           font_size=26, word_delay=220)
    assert plan["launch"]["tokens"] == ["claude", "--model opus"]


def test_render_voice_paces_the_launch(tmp_path):
    # When launch_voice is supplied, the launch is sized to the NARRATION (each
    # flag is narrated FIRST via a Sleep<dur>, THEN the token is typed) — not the
    # fixed PAD. This kills the v6 boot freeze (capture too short for the voice).
    launch_voice = [
        {"token": "claude", "text": "啟動", "mp3": "_voice/open_intro.mp3", "dur": 1.7},
        {"token": "--model opus", "text": "用 opus", "mp3": "_voice/open_flag0.mp3", "dur": 2.3},
    ]
    launch_outro = {"text": "進入畫面", "mp3": "_voice/open_outro.mp3", "dur": 1.9}
    tape, plan = g.render(SPEC, demo=str(tmp_path), width=1200, height=1080,
                          font_size=26, word_delay=220,
                          launch_voice=launch_voice, launch_outro=launch_outro)
    # voice-paced Sleeps for the launch narration durations (NOT the fixed PAD)
    assert "Sleep 1.700s" in tape and "Sleep 2.300s" in tape
    # the token is typed AFTER its narrate-Sleep (voice leads the visual)
    intro_sleep = tape.index("Sleep 1.700s")
    type_claude = tape.index('Type "claude"')
    assert intro_sleep < type_claude
    flag_sleep = tape.index("Sleep 2.300s")
    type_flag = tape.index('Type " --model opus"')
    assert flag_sleep < type_flag
    # capture-plan launch beats carry INCREASING raw onsets (`at`)
    beats = plan["launch"]["beats"]
    assert len(beats) == 2
    ats = [b["at"] for b in beats]
    assert ats == sorted(ats) and ats[0] < ats[1]
    assert beats[0]["at"] == g.PRELUDE        # base beat narrates at the prelude
    assert beats[0]["mp3"] == "_voice/open_intro.mp3"
    # outro rides the boot; its onset is the Enter time (after the last flag)
    outro = plan["launch"]["outro"]
    assert outro["at"] > ats[-1]


def test_tape_overrides_inherited_prompt(tmp_path):
    # regression: VHS defaults to bash and inherits the EXPORTED p10k `PS1`,
    # rendering it as full-screen `${_p9k_…}` garbage that uglified the frame and
    # broke detect_turns with false submissions. The tape MUST override PS1/PROMPT
    # (the verified fix) regardless of shell; ZDOTDIR is kept as zsh defense.
    tape, _plan = g.render(SPEC, demo=str(tmp_path), width=1200, height=1080,
                           font_size=26, word_delay=220)
    assert 'Env PS1' in tape and 'Env PROMPT' in tape
    assert 'Env ZDOTDIR' in tape


def test_tape_disables_prompt_suggestion_ghost_text(tmp_path):
    # regression: Claude Code's prompt-suggestion feature can populate grey
    # ghost text in the empty input box when a reply reads like an invitation
    # to a next step. On at least two occasions this coincided with the NEXT
    # scripted turn's typing silently failing to register (terminal sat idle
    # on the ghost suggestion for the full Wait timeout, no typed chars, no
    # reply). Disabling suggestions during capture made the symptom disappear
    # across dozens of subsequent recordings.
    tape, _plan = g.render(SPEC, demo=str(tmp_path), width=1200, height=1080,
                           font_size=26, word_delay=220)
    assert 'Env CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION "false"' in tape


def test_question_turn_waits_for_selector_then_navigates(tmp_path):
    spec = {
        "launch": {"base": "claude", "flags": [{"arg": "--model opus"}]},
        "turns": [{"prompt": "ask me to pick", "question": {"answer_index": 1}}],
    }
    tape, plan = g.render(spec, demo=str(tmp_path), width=1200, height=1080,
                          font_size=26, word_delay=220)
    # after the prompt Enter: wait for the selector footer (VHS-safe ASCII span),
    # then navigate, then sentinel
    assert f"/{qnav.FOOTER_RE}/" in tape        # Wait+Screen on the selector footer
    assert "↑" not in tape                       # no Unicode arrows (VHS parser chokes)
    i_wait = tape.index(qnav.FOOTER_RE)
    i_down = tape.index("Down", i_wait)         # qnav: answer_index 1 -> one Down + Enter
    i_done = tape.index("VHS_TURN_DONE_1")
    assert i_wait < i_down < i_done
    # the plan records the question for the downstream stages
    assert plan["turns"][0]["question"]["answer_index"] == 1
    # render-mode env so the hook lets the selector paint
    assert 'Env VHS_QUESTION_MODE "render"' in tape


def test_non_question_turn_has_no_selector_wait(tmp_path):
    spec = {"launch": {"base": "claude", "flags": []},
            "turns": [{"prompt": "just do it"}]}
    tape, _ = g.render(spec, demo=str(tmp_path), width=1200, height=1080,
                       font_size=26, word_delay=220)
    assert qnav.FOOTER_RE not in tape
    assert 'VHS_QUESTION_MODE' not in tape


def test_tmux_mode_starts_an_invisible_tmux_before_launch(tmp_path):
    # tmux mode: the whole claude session runs inside a dedicated-socket,
    # status-off tmux. The tmux START must be INVISIBLE (Hide ... Show) and must
    # come BEFORE the CLI-lesson launch so `Type "claude"` is preserved on screen.
    tape, _plan = g.render(SPEC, demo=str(tmp_path), width=1200, height=1080,
                           font_size=26, word_delay=220,
                           tmux={"socket": "vhsq", "name": "vhsq"})
    assert "Hide" in tape and "Show" in tape
    assert "tmux -L vhsq" in tape
    # the Hide/tmux/Show block is BEFORE the first claude launch token
    i_hide = tape.index("Hide")
    i_tmux = tape.index("tmux -L vhsq")
    i_show = tape.index("Show")
    i_claude = tape.index('Type "claude"')
    assert i_hide < i_tmux < i_show < i_claude
    # references the driver-written tmux.conf and the socket-named session
    assert "tmux.conf" in tape and "-s vhsq" in tape
    # the answer policy is NEVER a tape Env (the driver passes it via process env)
    assert "VHS_ANSWERS" not in tape


def test_non_tmux_render_has_no_hide_or_tmux(tmp_path):
    # back-compat: without tmux config the tape is byte-identical to before —
    # no Hide/Show, no dedicated-socket tmux start.
    tape, _ = g.render(SPEC, demo=str(tmp_path), width=1200, height=1080,
                       font_size=26, word_delay=220)
    assert "Hide" not in tape
    assert "tmux -L" not in tape


# --- quote-escaping regressions -------------------------------------------
#
# VHS's tape grammar has no backslash-escape for quotes inside a `Type "..."`
# line, so a turn prompt or launch flag arg containing a literal `"` (or `'`,
# or BOTH) used to break the line with `Invalid command: ...`. These tests
# extract the actual `Type <delim>...<delim>` lines VHS would execute and
# replay them (concatenating bodies in order) to prove the ORIGINAL string is
# reproduced byte-for-byte, and that no line is malformed (unbalanced or with
# the delimiter char leaking into its own body — either of which VHS's parser
# cannot handle).

def _replay_type_lines(tape, start_marker, end_marker):
    """Simulate what VHS would type for every `Type <delim>...<delim>` line
    between `start_marker` and `end_marker`, concatenated in order."""
    start = tape.index(start_marker)
    end = tape.index(end_marker, start)
    segment = tape[start:end]
    typed = ""
    for line in segment.splitlines():
        line = line.strip()
        if not line.startswith("Type "):
            continue
        rest = line[len("Type "):]
        delim = rest[0]
        assert delim in "\"'", f"Type line has no valid delimiter: {line!r}"
        assert rest[-1] == delim, f"Type line is unbalanced: {line!r}"
        body = rest[1:-1]
        assert delim not in body, (
            f"delimiter {delim!r} leaked into its own Type body: {line!r}")
        typed += body
    return typed


def test_turn_prompt_with_only_double_quotes_round_trips(tmp_path):
    prompt = 'say "hello world" now'
    spec = {"launch": {"base": "claude", "flags": []}, "turns": [{"prompt": prompt}]}
    tape, _plan = g.render(spec, demo=str(tmp_path), width=1200, height=1080,
                           font_size=26, word_delay=220)
    replayed = _replay_type_lines(tape, "# --- Turn 1 ---", "Enter")
    assert replayed == prompt


def test_turn_prompt_with_only_single_quotes_round_trips(tmp_path):
    prompt = "say 'hello world' now"
    spec = {"launch": {"base": "claude", "flags": []}, "turns": [{"prompt": prompt}]}
    tape, _plan = g.render(spec, demo=str(tmp_path), width=1200, height=1080,
                           font_size=26, word_delay=220)
    replayed = _replay_type_lines(tape, "# --- Turn 1 ---", "Enter")
    assert replayed == prompt


def test_launch_flag_with_mixed_quotes_round_trips(tmp_path):
    # the exact failure mode from the bug report: a value mixing BOTH ' and "
    # can't be wrapped in either delimiter alone.
    arg = ('--mcp-config \'{"mcpServers":{"docs":{"type":"http",'
           '"url":"https://example.com/mcp"}}}\'')
    spec = {"launch": {"base": "claude", "flags": [{"arg": arg}]},
             "turns": [{"prompt": "hello"}]}
    tape, plan = g.render(spec, demo=str(tmp_path), width=1200, height=1080,
                          font_size=26, word_delay=220)
    assert plan["launch"]["tokens"] == ["claude", arg]
    replayed = _replay_type_lines(tape, "Sleep 2s", "Wait+Screen")
    assert replayed == "claude" + " " + arg


def test_turn_prompt_with_mixed_quotes_round_trips(tmp_path):
    prompt = '''say "it's" fine'''
    spec = {"launch": {"base": "claude", "flags": []}, "turns": [{"prompt": prompt}]}
    tape, _plan = g.render(spec, demo=str(tmp_path), width=1200, height=1080,
                           font_size=26, word_delay=220)
    replayed = _replay_type_lines(tape, "# --- Turn 1 ---", "Enter")
    assert replayed == prompt


def test_instant_command_turn_skips_the_stop_sentinel_wait(tmp_path):
    # regression: a turn whose prompt is handled ENTIRELY client-side (e.g.
    # /rename, /fast on) never triggers a model turn, so the Stop hook (and
    # its VHS_TURN_DONE_N sentinel) never fires. Wait+Screen@.../VHS_TURN_DONE_N/
    # would reliably burn the full turn-timeout for that turn. Such a turn must
    # get a short fixed Sleep instead, while normal (model-invoking) turns
    # still get the real sentinel wait.
    spec = {
        "launch": {"base": "claude", "flags": []},
        "turns": [
            {"prompt": "/rename demo"},
            {"prompt": "write fizzbuzz"},
            {"prompt": "/fast on"},
        ],
    }
    tape, plan = g.render(spec, demo=str(tmp_path), width=1200, height=1080,
                          font_size=26, word_delay=220)
    # turn 1 (/rename demo) — NO sentinel wait for it
    assert "VHS_TURN_DONE_1" not in tape
    # turn 2 (write fizzbuzz) — still a real Wait+Screen sentinel
    assert f"Wait+Screen@120s /VHS_TURN_DONE_2/" in tape
    # turn 3 (/fast on) — NO sentinel wait for it either
    assert "VHS_TURN_DONE_3" not in tape
    # instant turns get a short fixed settle Sleep instead
    assert f"Sleep {g.INSTANT_SETTLE:.3f}s" in tape
    # capture.json marks the instant turns distinctly so downstream stages
    # (e.g. panel.py's UserPromptSubmit/Stop alignment) know not to expect a
    # Stop-hook JSONL entry for them
    assert plan["turns"][0]["instant"] is True
    assert "instant" not in plan["turns"][1]
    assert plan["turns"][2]["instant"] is True
    # the real turn still carries its sentinel field
    assert plan["turns"][1]["sentinel"] == "VHS_TURN_DONE_2"
    assert "sentinel" not in plan["turns"][0]


def test_instant_command_detection_handles_args_and_known_commands(tmp_path):
    # leading-token match, robust to arguments; only known client-side/instant
    # commands are treated this way — anything else (including plain text that
    # merely starts with a slash-like word) still gets the real sentinel wait.
    for prompt in ["/model opus", "/branch feature-x", "/context", "/usage",
                   "/clear", "/tui fullscreen", "/effort high", "/fast off"]:
        assert g._is_instant_command(prompt), prompt
    for prompt in ["write fizzbuzz", "/explain this code", "/tui split"]:
        assert not g._is_instant_command(prompt), prompt


# --- issue #17: native CLI menus (gap between #1c/#16 and #1d/#14) --------
#
# /theme, /rewind, /memory and /plugin install DO render an on-screen menu
# (unlike the no-menu INSTANT_COMMANDS above), but — confirmed via a live
# tmux probe — selecting an option still fires NO Stop hook event. So the
# capture tape must ALSO skip Wait+Screen on VHS_TURN_DONE_N for these turns,
# same as the no-menu instant commands, but the settle Sleep must be long
# enough for qmonitor's background answer cycle (poll -> dwell -> keystrokes
# -> confirm poll) to actually finish under --robust/--tmux, where a real
# qmonitor is driving the menu.

def test_native_menu_command_detection_handles_args_and_known_commands():
    for prompt in ["/theme", "/theme dark", "/rewind", "/memory",
                   "/plugin install some-plugin"]:
        assert g._is_native_menu_command(prompt), prompt
    # /plugin has OTHER subcommands that don't show the scope-picker menu —
    # only "install" does; be conservative and don't treat the rest as such.
    for prompt in ["write fizzbuzz", "/explain this code", "/plugin",
                   "/plugin list", "/plugin uninstall foo", "/model opus"]:
        assert not g._is_native_menu_command(prompt), prompt


def test_native_menu_turn_skips_the_stop_sentinel_wait_under_robust_tmux(tmp_path):
    spec = {
        "launch": {"base": "claude", "flags": []},
        "turns": [
            {"prompt": "/theme"},
            {"prompt": "write fizzbuzz"},
            {"prompt": "/plugin install foo"},
        ],
    }
    tape, plan = g.render(spec, demo=str(tmp_path), width=1200, height=1080,
                          font_size=26, word_delay=220,
                          tmux={"socket": "vhsq", "name": "vhsq"})
    # turn 1 (/theme) — NO sentinel wait; qmonitor answers the menu, but no
    # Stop hook ever fires for it, so Wait+Screen would just time out.
    assert "VHS_TURN_DONE_1" not in tape
    # turn 2 (write fizzbuzz) — still a real Wait+Screen sentinel
    assert "Wait+Screen@120s /VHS_TURN_DONE_2/" in tape
    # turn 3 (/plugin install foo) — NO sentinel wait either
    assert "VHS_TURN_DONE_3" not in tape
    # under tmux/robust mode, the settle Sleep is the LONGER native-menu one
    # (long enough for qmonitor's real answer cycle), not the short
    # no-menu INSTANT_SETTLE.
    assert f"Sleep {g.NATIVE_MENU_SETTLE:.3f}s" in tape
    assert g.NATIVE_MENU_SETTLE > g.INSTANT_SETTLE
    # capture.json marks these turns "instant" too (same flag/shape the
    # no-menu instant-command path already uses, so downstream stages —
    # panel.py's UserPromptSubmit/Stop alignment, detect_anchors.py — stay
    # compatible without needing to learn a second key).
    assert plan["turns"][0]["instant"] is True
    assert "instant" not in plan["turns"][1]
    assert plan["turns"][2]["instant"] is True
    assert "sentinel" not in plan["turns"][0]
    assert plan["turns"][1]["sentinel"] == "VHS_TURN_DONE_2"


def test_native_menu_turn_uses_short_settle_without_tmux(tmp_path):
    # STANDARD (non-robust) mode has no qmonitor running at all, so a /theme
    # turn's menu never gets navigated regardless of how long we sleep — the
    # capture is already broken for this scenario. But the Stop hook still
    # never fires either way, so we must not hang the capture wait on a
    # sentinel that will never print. Since there's no answer cycle to wait
    # out here, use the short no-menu INSTANT_SETTLE rather than the longer
    # robust-mode NATIVE_MENU_SETTLE.
    spec = {"launch": {"base": "claude", "flags": []},
            "turns": [{"prompt": "/theme"}]}
    tape, plan = g.render(spec, demo=str(tmp_path), width=1200, height=1080,
                          font_size=26, word_delay=220, tmux=None)
    assert "VHS_TURN_DONE_1" not in tape
    assert f"Sleep {g.INSTANT_SETTLE:.3f}s" in tape
    assert f"Sleep {g.NATIVE_MENU_SETTLE:.3f}s" not in tape
    assert plan["turns"][0]["instant"] is True
