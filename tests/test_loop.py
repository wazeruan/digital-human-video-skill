import io
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from digital_human.api import create_app
from digital_human.backends.lipsync import CachedLoop
from digital_human.backends.motion import LivePortraitMotion, StaticMotion
from digital_human.backends.tts import MLXQwenTTS
from digital_human.config import Settings
from digital_human.ffmpeg import FFmpeg


def test_local_loop_uses_real_tts_and_never_contacts_musetalk(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("loop mode contacted MuseTalk")
    monkeypatch.setattr("httpx.get", forbidden)
    monkeypatch.setattr("httpx.post", forbidden)
    app = create_app(Settings(backend="local", render_mode="loop",
                              motion_backend="liveportrait", data_dir=tmp_path))
    assert isinstance(app.state.service.tts, MLXQwenTTS)
    loop = app.state.service.lipsync
    assert isinstance(loop, CachedLoop)
    assert loop.health()["audio_driven"] is False
    source, output = tmp_path / "loop.mp4", tmp_path / "out.mp4"
    source.write_bytes(b"cached-motion")
    loop.render("avatar", tmp_path / "unused.wav", source, output)
    assert output.read_bytes() == source.read_bytes()
    with pytest.raises(RuntimeError, match="missing or empty"):
        loop.prepare("avatar", tmp_path / "missing.mp4")


def test_loop_requires_animated_motion():
    with pytest.raises(ValueError, match="requires motion_backend=liveportrait"):
        Settings(render_mode="loop", motion_backend="static")


def test_loop_driver_cache_tracks_content_and_strength(tmp_path):
    driver = tmp_path / "driver.pkl"
    driver.write_bytes(b"first")
    backend = LivePortraitMotion(FFmpeg(), tmp_path, "python", driver, "model", 0.6)
    first = backend.revision
    driver.write_bytes(b"second")
    assert backend.revision != first
    second = backend.revision
    backend.driving_multiplier = 0.7
    assert backend.revision != second


def test_loop_api_renders_without_musetalk(tmp_path, monkeypatch):
    # Exercise real FFmpeg/queue/API, replacing only model-heavy face animation.
    monkeypatch.setattr("digital_human.api.LivePortraitMotion",
                        lambda media, *args: StaticMotion(media))
    app = create_app(Settings(backend="fake", render_mode="loop",
                              motion_backend="liveportrait", data_dir=tmp_path))
    image = io.BytesIO()
    Image.new("RGB", (512, 512), "blue").save(image, "PNG")
    with TestClient(app) as client:
        avatar = client.post("/v1/avatars", files={"image": ("a.png", image.getvalue(), "image/png")})
        assert avatar.status_code == 201
        avatar_id = avatar.json()["avatar_id"]
        invalid = client.post("/v1/renders", json={"avatar_id": avatar_id, "text": "一" * 21})
        assert invalid.status_code == 422
        response = client.post("/v1/renders", json={"avatar_id": avatar_id, "text": "你好呀"})
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        for _ in range(100):
            job = client.get(f"/v1/jobs/{job_id}").json()
            if job["status"] in {"succeeded", "failed"}:
                break
            time.sleep(0.05)
        assert job["status"] == "succeeded", job
        assert client.get(f"/v1/jobs/{job_id}/result").headers["content-type"] == "video/mp4"
