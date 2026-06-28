import os
import subprocess
import pytest

FF = "/opt/homebrew/bin/ffmpeg"

pytestmark = pytest.mark.skipif(
    not os.path.exists(FF), reason="ffmpeg not available")


def _has_audio(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=codec_type", "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout
    return "audio" in out


def test_mux_adds_voice_at_ledger_onsets(tmp_path):
    import overlay, ledger
    demo = str(tmp_path)
    voice = os.path.join(demo, "_voice")
    os.makedirs(voice, exist_ok=True)
    # 5s silent testsrc video
    subprocess.run([FF, "-y", "-f", "lavfi", "-i",
                    "testsrc=size=320x180:rate=12.5:duration=5",
                    "-pix_fmt", "yuv420p", os.path.join(demo, "terminal.mp4")],
                   check=True, capture_output=True)
    # two 1s sine clips
    for name, freq in (("a.mp3", 440), ("b.mp3", 660)):
        subprocess.run([FF, "-y", "-f", "lavfi", "-i",
                        f"sine=frequency={freq}:duration=1",
                        os.path.join(voice, name)], check=True, capture_output=True)
    led = {"beats": [
        {"id": "x", "kind": "intro", "text": "前", "drop": False,
         "voice": {"clip": "_voice/a.mp3", "start": 1.0, "end": 2.0}},
        {"id": "y", "kind": "outro", "text": "後", "drop": False,
         "voice": {"clip": "_voice/b.mp3", "start": 3.0, "end": 4.0}},
    ], "meta": {}}
    ledger.save(os.path.join(demo, "ledger.json"), led)

    n = overlay.mux(demo)
    assert n == 2
    out = os.path.join(demo, "session.mp4")
    assert os.path.exists(out)
    assert _has_audio(out)
