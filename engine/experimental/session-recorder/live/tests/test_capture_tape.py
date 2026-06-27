import gen_capture_tape as g

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
