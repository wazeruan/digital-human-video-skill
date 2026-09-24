from __future__ import annotations

import io
import time

from fastapi.testclient import TestClient
from PIL import Image

from digital_human.api import create_app
from digital_human.backends.lipsync import FakeLipSync
from digital_human.config import Settings
from digital_human.models import JobRecord, JobStatus


def png_bytes(color=(80, 120, 180)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (512, 512), color).save(out, "PNG")
    return out.getvalue()


def test_full_fake_flow_and_idempotency(tmp_path):
    app = create_app(Settings(backend="fake", data_dir=tmp_path))
    with TestClient(app) as client:
        avatar_response = client.post(
            "/v1/avatars", files={"image": ("avatar.png", png_bytes(), "image/png")}
        )
        assert avatar_response.status_code == 201
        avatar_id = avatar_response.json()["avatar_id"]

        payload = {"avatar_id": avatar_id, "text": "欢迎来到我的频道"}
        first = client.post(
            "/v1/renders", json=payload, headers={"Idempotency-Key": "test-1"}
        )
        assert first.status_code == 202
        job_id = first.json()["job_id"]
        second = client.post(
            "/v1/renders", json=payload, headers={"Idempotency-Key": "test-1"}
        )
        assert second.json()["job_id"] == job_id

        for _ in range(100):
            job = client.get(f"/v1/jobs/{job_id}").json()
            if job["status"] in {"succeeded", "failed"}:
                break
            time.sleep(0.05)
        assert job["status"] == "succeeded", job
        video = client.get(f"/v1/jobs/{job_id}/result")
        assert video.status_code == 200
        assert video.headers["content-type"] == "video/mp4"
        assert len(video.content) > 1000


def test_rejects_too_long_text(tmp_path):
    app = create_app(Settings(backend="fake", data_dir=tmp_path))
    with TestClient(app) as client:
        avatar_id = client.post(
            "/v1/avatars", files={"image": ("a.png", png_bytes(), "image/png")}
        ).json()["avatar_id"]
        response = client.post(
            "/v1/renders", json={"avatar_id": avatar_id, "text": "一" * 21}
        )
        assert response.status_code == 422


def test_avatar_prepare_runs_once_per_process(tmp_path):
    class CountingLipSync(FakeLipSync):
        def __init__(self):
            self.prepare_count = 0

        def prepare(self, avatar_key, base_video):
            self.prepare_count += 1

    app = create_app(Settings(backend="fake", data_dir=tmp_path))
    counting = CountingLipSync()
    app.state.service.lipsync = counting
    with TestClient(app) as client:
        avatar_id = client.post(
            "/v1/avatars", files={"image": ("a.png", png_bytes(), "image/png")}
        ).json()["avatar_id"]
        job_ids = []
        for text in ("第一句话", "第二句话"):
            response = client.post(
                "/v1/renders", json={"avatar_id": avatar_id, "text": text}
            )
            job_ids.append(response.json()["job_id"])
        for job_id in job_ids:
            for _ in range(100):
                job = client.get(f"/v1/jobs/{job_id}").json()
                if job["status"] in {"succeeded", "failed"}:
                    break
                time.sleep(0.05)
            assert job["status"] == "succeeded", job
    assert counting.prepare_count == 1


def test_result_endpoint_rejects_paths_outside_job_directory(tmp_path):
    app = create_app(Settings(backend="fake", data_dir=tmp_path / "data"))
    external = tmp_path / "outside.mp4"
    external.write_bytes(b"not a video")
    job = JobRecord(
        job_id="b" * 32,
        status=JobStatus.SUCCEEDED,
        stage="done",
        avatar_id="a" * 64,
        text="你好",
        voice="Vivian",
        language="Chinese",
        request_digest="d" * 64,
        result_path=str(external),
    )
    app.state.store.save_job(job)

    with TestClient(app) as client:
        response = client.get(f"/v1/jobs/{job.job_id}/result")

    assert response.status_code == 500


def test_job_view_hides_internal_failure_detail(tmp_path):
    app = create_app(Settings(backend="fake", data_dir=tmp_path / "data"))
    job = JobRecord(
        job_id="c" * 32,
        status=JobStatus.FAILED,
        stage="failed",
        avatar_id="a" * 64,
        text="你好",
        voice="Vivian",
        language="Chinese",
        request_digest="d" * 64,
        error_code="FileNotFoundError",
        error_message="/Users/private/work/secret.wav does not exist",
    )
    app.state.store.save_job(job)

    with TestClient(app) as client:
        response = client.get(f"/v1/jobs/{job.job_id}")

    assert response.json()["error_code"] == "render_failed"
    assert "/Users/private" not in response.json()["error_message"]
