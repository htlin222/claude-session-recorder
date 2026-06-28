import author, ledger


def test_built_ledger_satisfies_the_invariant(monkeypatch):
    monkeypatch.setattr(author, "synth", lambda text, out: 2.0)
    monkeypatch.setattr(author, "_dur", lambda p: 2.0)
    anchors = {"ready": 2.0, "vtot": 30.0,
               "turns": [{"typing_start": 4.0, "submit": 6.0, "done": 12.0}],
               "segments": None}
    script = {"launch": {"base": "claude",
                         "flags": [{"arg": "--model opus", "say": "用 opus"}],
                         "intro": "啟動", "outro": "進入畫面"},
              "turns": [{"prompt": "x", "intro": "請它寫", "think": "思考中",
                         "outro": "完成了"}],
              "close": "結束"}
    led = author.build_ledger(demo="/tmp/ignored", script=script, anchors=anchors,
                              write=False)
    assert ledger.serialization_violations(led["beats"]) == []
    t1 = [b for b in led["beats"] if b["tier"] == 1]
    assert t1 and all(not b["drop"] for b in t1)


def test_captured_launch_no_freeze_extend(monkeypatch):
    # NEW path: when the capture carried voice-paced launch beats (at/mp3/dur),
    # author REUSES them and copies the boot 1:1 — NO freeze-extend. Each
    # launch_flag's voice is placed at its captured raw onset.
    monkeypatch.setattr(author, "synth", lambda text, out: 1.0)
    monkeypatch.setattr(author, "_dur", lambda p: 1.0)
    # onsets as the voice-paced tape would record them: base@2.0 (PRELUDE),
    # then +dur+breath each; Enter (outro onset) after the last flag. ready=9.0
    # is the real boot finish, > the outro end 7.7, so the boot needs no extend.
    anchors = {"ready": 9.0, "vtot": 40.0, "segments": None,
               "turns": [{"typing_start": 12.0, "submit": 14.0, "done": 20.0}],
               "launch_beats": [
                   {"token": "claude", "text": "啟動",
                    "mp3": "_voice/open_intro.mp3", "dur": 1.7, "at": 2.0},
                   {"token": "--model opus", "text": "用 opus",
                    "mp3": "_voice/open_flag0.mp3", "dur": 2.0, "at": 4.2}],
               "launch_outro": {"text": "進入畫面",
                                "mp3": "_voice/open_outro.mp3", "dur": 1.0, "at": 6.7}}
    script = {"launch": {"base": "claude",
                         "flags": [{"arg": "--model opus", "say": "用 opus"}],
                         "intro": "啟動", "outro": "進入畫面"},
              "turns": [{"prompt": "x", "intro": "請它寫", "think": "思考中",
                         "outro": "完成了"}], "close": "結束"}
    led = author.build_ledger(demo="/tmp/ignored", script=script, anchors=anchors,
                              write=False)
    boot = next(s for s in led["meta"]["segments"] if s["kind"] == "boot")
    raw_len = round(boot["raw"][1] - boot["raw"][0], 3)
    # boot is hard-copied 1:1 (no freeze-extend; outro end 7.7 < raw_len 9.0)
    assert round(boot["out"][1] - boot["out"][0], 3) == raw_len == 9.0
    lf = [b for b in led["beats"] if b["kind"] == "launch_flag"]
    # each launch_flag voice starts at its captured raw onset (boot out == raw)
    starts = {round(b["voice"]["start"], 3) for b in lf}
    assert {2.0, 4.2}.issubset(starts)
    assert ledger.serialization_violations(led["beats"]) == []


def test_captured_launch_outro_clears_turn0_intro_by_a_breath(monkeypatch):
    # Regression (real recording): when the boot finishes ~when the launch OUTRO
    # ends (ready <= outro_end), the boot must extend to outro_end + BREATH so the
    # outro tail doesn't overlap turn-0's intro in the next soft segment (the bug
    # was a -0.004s sub-frame overlap that FAILED lint).
    monkeypatch.setattr(author, "synth", lambda text, out: 1.0)
    monkeypatch.setattr(author, "_dur", lambda p: 1.0)
    anchors = {"ready": 7.0, "vtot": 40.0, "segments": None,   # boot ends at 7.0
               "turns": [{"typing_start": 12.0, "submit": 14.0, "done": 20.0}],
               "launch_beats": [
                   {"token": "claude", "text": "啟動",
                    "mp3": "_voice/open_intro.mp3", "dur": 1.7, "at": 2.0},
                   {"token": "--model opus", "text": "用 opus",
                    "mp3": "_voice/open_flag0.mp3", "dur": 2.0, "at": 4.2}],
               # outro ends at 7.7 — PAST ready (7.0): without the +BREATH the
               # next soft segment would start at 7.7 and the turn-0 intro overlap.
               "launch_outro": {"text": "進入畫面",
                                "mp3": "_voice/open_outro.mp3", "dur": 1.0, "at": 6.7}}
    script = {"launch": {"base": "claude",
                         "flags": [{"arg": "--model opus", "say": "用 opus"}],
                         "intro": "啟動", "outro": "進入畫面"},
              "turns": [{"prompt": "x", "intro": "請它寫", "think": "思考中",
                         "outro": "完成了"}], "close": "結束"}
    led = author.build_ledger(demo="/tmp/ignored", script=script, anchors=anchors,
                              write=False)
    assert ledger.serialization_violations(led["beats"]) == []
    boot = next(s for s in led["meta"]["segments"] if s["kind"] == "boot")
    # boot extends to the outro end (7.7) + a BREATH so the next beat is clear
    assert boot["out"][1] >= 7.7 + ledger.BREATH - 1e-6


def test_intro_leads_typing_and_think_rides_the_gap(monkeypatch):
    monkeypatch.setattr(author, "synth", lambda text, out: 1.5)
    monkeypatch.setattr(author, "_dur", lambda p: 1.5)
    anchors = {"ready": 2.0, "vtot": 40.0, "segments": None,
               "turns": [{"typing_start": 5.0, "submit": 7.0, "done": 15.0}]}
    script = {"launch": {"flags": [], "intro": "啟動"},
              "turns": [{"prompt": "x", "intro": "請它寫一個函式",
                         "think": "正在思考", "outro": "完成"}], "close": "結束"}
    led = author.build_ledger("/tmp/ignored", script, anchors, write=False)
    intro = next(b for b in led["beats"] if b["kind"] == "intro")
    # intro voice ends at or before the typing window starts (leads typing)
    assert intro["voice"]["end"] <= intro["visual"]["start"] + 1e-6
    think = next(b for b in led["beats"] if b["kind"] == "think")
    # think voice sits inside its hard visual window (rides the gap)
    assert think["voice"]["start"] >= think["visual"]["start"] - 1e-6
    assert think["voice"]["end"] <= think["visual"]["end"] + 1e-6
