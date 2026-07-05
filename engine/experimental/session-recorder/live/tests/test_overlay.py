import pytest

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


# ---------------------------------------------------------------------------
# chunk_cues(): re-slicing the caption layer within a beat's FIXED voice
# window (see issue #4 — the window itself must never move, only how the
# text is carved up inside it).
# ---------------------------------------------------------------------------

LONG_NARRATION = (
    "我們先來看看這個專案的整體架構，它主要分成三個部分，分別是前端、後端，以及資料庫。"
    "前端使用 React 搭配 TypeScript 開發，後端則是用 Python 寫的 API 服務，"
    "資料庫選用 PostgreSQL 來儲存使用者資料，並且設計了完整的備份機制。"
    "接下來我們會依序介紹每一個部分的實作細節，並且說明它們之間如何互相溝通與協作，"
    "這樣大家對整個系統就會有一個清楚完整的認識了。"
)


def test_chunk_cues_short_beat_collapses_to_one_cue_spanning_full_window():
    # A short beat doesn't need splitting at all — chunk_cues() must reduce
    # to exactly the old one-cue-per-beat behaviour: same window, same text.
    cues = overlay.chunk_cues("用 opus", 1.0, 2.0)
    assert cues == [(1.0, 2.0, "用 opus")]


def test_chunk_cues_long_beat_splits_into_multiple_readable_sub_cues():
    start, end = 0.0, 40.0
    cues = overlay.chunk_cues(LONG_NARRATION, start, end)

    assert len(cues) > 1

    # the fixed voice window is preserved exactly: first cue starts at the
    # beat's onset, last cue ends at the beat's offset, no gaps/overlaps.
    assert cues[0][0] == start
    assert cues[-1][1] == end
    for (_, e1, _), (s2, _, _) in zip(cues, cues[1:]):
        assert e1 == s2

    # durations sum EXACTLY to the original fixed window — re-slicing the
    # caption layer must never change the audio-reconciled voice timing.
    total_dur = sum(e - s for s, e, _ in cues)
    assert total_dur == pytest.approx(end - start)

    # concatenating the sub-cues reproduces the beat text verbatim — no
    # characters dropped or added by the chunker.
    assert "".join(c for _, _, c in cues) == LONG_NARRATION

    # every cue meets the reading-speed floor and (bar the documented
    # merge-back trade-off) stays near the char-count budget.
    for s, e, c in cues:
        assert (e - s) >= overlay.MIN_CUE_DUR - 1e-9
        assert overlay.cjk_width(c) <= overlay.MAX_CUE_UNITS + 10  # merge slack


def test_chunk_cues_merges_short_trailing_fragments_to_respect_min_dur():
    # Eight comma-separated clauses, no sentence punctuation, crammed into a
    # short 3s window: splitting on 、，, alone would yield 8 sub-cues each
    # ~0.375s — well under MIN_CUE_DUR (1.2s) and unreadably brief. The
    # merge-back rule must fold short fragments into their neighbours until
    # every remaining cue clears the min_dur floor.
    text = "早安，你好，再見，謝謝，晚安，掰掰，加油，辛苦了"
    start, end = 0.0, 3.0
    cues = overlay.chunk_cues(text, start, end, min_dur=1.2)

    assert len(cues) < 8
    assert all((e - s) >= 1.2 - 1e-9 for s, e, _ in cues)
    assert cues[0][0] == start
    assert cues[-1][1] == end
    assert sum(e - s for s, e, _ in cues) == pytest.approx(end - start)
    assert "".join(c for _, _, c in cues) == text


def test_chunk_cues_single_leftover_chunk_cannot_grow_past_the_fixed_window():
    # Degenerate case: window is shorter than min_dur itself. There's only
    # one chunk to begin with (text too short to split), so it simply gets
    # the whole (tiny) window — it can't be stretched past the ledger's
    # audio-reconciled [start, end].
    cues = overlay.chunk_cues("嗨", 0.0, 0.5, min_dur=1.2)
    assert cues == [(0.0, 0.5, "嗨")]


def test_build_srt_renumbers_cues_across_the_whole_file_not_per_beat():
    beats = [
        {"voice": {"clip": "_voice/intro_1.mp3", "start": 0.0, "end": 40.0},
         "text": LONG_NARRATION, "drop": False},
        {"voice": {"clip": "_voice/outro_1.mp3", "start": 41.0, "end": 42.0},
         "text": "完成了", "drop": False},
    ]
    srt = overlay.build_srt(beats)
    blocks = srt.strip("\n").split("\n\n")
    numbers = [int(b.split("\n", 1)[0]) for b in blocks]

    # numbering is one contiguous 1..N sequence across every beat's sub-cues,
    # not restarted at 1 for the second beat.
    assert numbers == list(range(1, len(numbers) + 1))
    assert len(numbers) > 2   # the long beat alone produced multiple cues
    assert "完成了" in srt
