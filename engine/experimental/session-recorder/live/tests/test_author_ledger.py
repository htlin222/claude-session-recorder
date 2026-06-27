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
