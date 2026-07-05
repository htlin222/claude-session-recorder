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
