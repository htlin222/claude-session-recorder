import overlay


def test_srt_cues_come_straight_from_ledger_voice_windows():
    beats = [
        {"voice": {"clip": "_voice/intro_1.mp3", "start": 1.0, "end": 3.0},
         "text": "請它寫", "drop": False},
        {"voice": None, "text": "", "drop": True},          # dropped -> no cue
        {"voice": {"clip": "_voice/outro_1.mp3", "start": 5.0, "end": 7.0},
         "text": "完成了", "drop": False},
    ]
    srt = overlay.build_srt(beats)
    assert "00:00:01,000 --> 00:00:03,000" in srt
    assert "請它寫" in srt and "完成了" in srt
    assert srt.count("-->") == 2     # the dropped beat produced no cue


def test_launch_subtitle_is_clean_no_slot_prefix():
    # the launch beat's display text is the BARE narration (the slot-prefix only
    # lives in the beat id, never in the subtitle the viewer reads).
    beats = [
        {"voice": {"clip": "_voice/open_flag0.mp3", "start": 1.0, "end": 2.0},
         "text": "用 opus", "drop": False},
    ]
    srt = overlay.build_srt(beats)
    assert "用 opus" in srt
    assert "flag0:用 opus" not in srt


def test_srt_orders_by_voice_start():
    beats = [
        {"voice": {"clip": "a", "start": 5.0, "end": 6.0}, "text": "後", "drop": False},
        {"voice": {"clip": "b", "start": 1.0, "end": 2.0}, "text": "前", "drop": False},
    ]
    srt = overlay.build_srt(beats)
    assert srt.index("前") < srt.index("後")
