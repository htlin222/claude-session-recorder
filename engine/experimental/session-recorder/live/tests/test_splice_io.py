import os
import shutil
import subprocess
import pytest

FF = "/opt/homebrew/bin/ffmpeg"

pytestmark = pytest.mark.skipif(
    not os.path.exists(FF), reason="ffmpeg not available")


def _probe_dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout or 0)


def test_splice_output_duration_matches_plan(tmp_path):
    import splice, ledger
    raw = str(tmp_path / "terminal_raw.mp4")
    # 6s synthetic raw clip
    subprocess.run([FF, "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=12.5:duration=6",
                    "-pix_fmt", "yuv420p", raw], check=True, capture_output=True)
    # 1 copy [0,2] + 1 freeze soft [2,4]->3s + 1 copy hard [4,6]  => out total 7s
    led = {"beats": [], "meta": {"vtot_out": 7.0, "segments": [
        {"kind": "boot", "raw": [0.0, 2.0], "out_dur": 2.0, "out": [0.0, 2.0]},
        {"kind": "soft", "raw": [2.0, 4.0], "out_dur": 3.0, "out": [2.0, 5.0]},
        {"kind": "hard", "raw": [4.0, 6.0], "out": [5.0, 7.0]},
    ]}}
    ledger.save(str(tmp_path / "ledger.json"), led)
    splice.splice(str(tmp_path))
    out = str(tmp_path / "terminal.mp4")
    assert os.path.exists(out)
    assert abs(_probe_dur(out) - 7.0) < 0.3
