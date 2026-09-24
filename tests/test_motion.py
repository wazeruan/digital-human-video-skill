from pathlib import Path

from digital_human.backends.motion import LivePortraitMotion, StaticMotion
from digital_human.ffmpeg import FFmpeg


def test_liveportrait_keeps_venv_interpreter_path(tmp_path):
    repo = tmp_path / "LivePortrait"
    repo.mkdir()
    driving = tmp_path / "d0.mp4"
    driving.write_bytes(b"")
    configured = Path("vendor/LivePortrait/.venv/bin/python")
    backend = LivePortraitMotion(FFmpeg(), repo, str(configured), driving, "rev")
    assert backend.python.endswith("vendor/LivePortrait/.venv/bin/python")
    assert backend.revision.startswith("liveportrait:rev:driver=")
    assert ":multiplier=1.0:" in backend.revision


def test_static_motion_revision():
    assert StaticMotion(FFmpeg()).revision == "static-v1"
