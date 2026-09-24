import io
import stat

import pytest
from PIL import Image

from digital_human.backends.lipsync import FakeLipSync
from digital_human.ffmpeg import FFmpeg
from digital_human.models import JobRecord, JobStatus
from digital_human.store import Store


def test_queued_job_is_failed_on_restart(tmp_path):
    media = FFmpeg()
    first = Store(tmp_path, media, 1.0, 25)
    first.save_job(
        JobRecord(
            job_id="queued-job",
            avatar_id="a" * 64,
            text="你好",
            voice="Vivian",
            language="Chinese",
            request_digest="d" * 64,
        )
    )
    second = Store(tmp_path, media, 1.0, 25)
    recovered = second.get_job("queued-job")
    assert recovered is not None
    assert recovered.status == JobStatus.FAILED
    assert recovered.error_code == "server_restarted"


def test_store_uses_private_permissions(tmp_path):
    store = Store(tmp_path / "private", FFmpeg(), 1.0, 25)

    assert stat.S_IMODE(store.root.stat().st_mode) == 0o700
    assert stat.S_IMODE(store.avatars.stat().st_mode) == 0o700
    assert stat.S_IMODE(store.jobs.stat().st_mode) == 0o700
    assert stat.S_IMODE(store.db.stat().st_mode) == 0o600


def test_store_does_not_change_permissions_of_existing_data_root(tmp_path, caplog):
    root = tmp_path / "shared"
    root.mkdir()
    root.chmod(0o755)

    store = Store(root, FFmpeg(), 1.0, 25)

    assert stat.S_IMODE(root.stat().st_mode) == 0o755
    assert stat.S_IMODE(store.avatars.stat().st_mode) == 0o700
    assert stat.S_IMODE(store.db.stat().st_mode) == 0o600
    assert "leaving its permissions unchanged" in caplog.text


def test_canonical_png_rejects_decompression_bomb_warning(monkeypatch):
    out = io.BytesIO()
    Image.new("RGB", (16, 16)).save(out, "PNG")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)

    with pytest.raises(ValueError, match="invalid or unsafe image"):
        Store.canonical_png(out.getvalue())
