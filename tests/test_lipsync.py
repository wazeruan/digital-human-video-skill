from pathlib import Path

from digital_human.backends.lipsync import MuseTalkHTTP


def test_musetalk_warmup_includes_mask_ratio(monkeypatch, tmp_path):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

    def fake_post(url, *, json, timeout):
        captured.update(url=url, payload=json, timeout=timeout)
        return Response()

    monkeypatch.setattr("digital_human.backends.lipsync.httpx.post", fake_post)
    base = tmp_path / "base.mp4"
    base.write_bytes(b"video")
    backend = MuseTalkHTTP("http://localhost:8001", "rev", 0.44)
    backend.prepare("avatar-1", base)

    assert captured["url"] == "http://localhost:8001/warmup"
    assert captured["payload"]["mask_upper_boundary_ratio"] == 0.44
    assert backend.revision.endswith("mask=0.44")
