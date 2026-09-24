from __future__ import annotations

import base64
import shutil
from pathlib import Path
from typing import Protocol

import httpx


class LipSyncBackend(Protocol):
    revision: str

    def prepare(self, avatar_key: str, base_video: Path) -> None: ...

    def render(self, avatar_key: str, audio: Path, base_video: Path, output: Path) -> None: ...

    def health(self) -> dict: ...


class FakeLipSync:
    revision = "fake-lipsync-v1"

    def prepare(self, avatar_key: str, base_video: Path) -> None:
        return None

    def render(self, avatar_key: str, audio: Path, base_video: Path, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(base_video, output)

    def health(self) -> dict:
        return {"ok": True, "mode": "fake"}


class CachedLoop:
    """Reuse accepted face motion; FFmpeg loops it to match the TTS duration."""

    revision = "cached-talking-loop-v1"

    def prepare(self, avatar_key: str, base_video: Path) -> None:
        if not base_video.is_file() or base_video.stat().st_size == 0:
            raise RuntimeError(f"Cached talking video is missing or empty: {base_video}")

    def render(self, avatar_key: str, audio: Path, base_video: Path, output: Path) -> None:
        self.prepare(avatar_key, base_video)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(base_video, output)

    def health(self) -> dict:
        return {"ok": True, "mode": "loop", "audio_driven": False,
                "detail": "Reuses cached face motion; mouth movement is not synchronized to speech."}


class MuseTalkHTTP:
    def __init__(
        self,
        base_url: str,
        revision: str,
        mask_upper_boundary_ratio: float = 0.5,
        timeout: float = 300.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.mask_upper_boundary_ratio = mask_upper_boundary_ratio
        self.revision = f"musetalk-mac:{revision}:mask={mask_upper_boundary_ratio:.2f}"
        self.timeout = timeout

    def prepare(self, avatar_key: str, base_video: Path) -> None:
        payload = {
            "avatar_key": avatar_key,
            "video_b64": base64.b64encode(base_video.read_bytes()).decode("ascii"),
            "mask_upper_boundary_ratio": self.mask_upper_boundary_ratio,
        }
        response = httpx.post(f"{self.base_url}/warmup", json=payload, timeout=self.timeout)
        response.raise_for_status()

    def render(self, avatar_key: str, audio: Path, base_video: Path, output: Path) -> None:
        payload = {
            "avatar_key": avatar_key,
            "audio_b64": base64.b64encode(audio.read_bytes()).decode("ascii"),
        }
        response = httpx.post(
            f"{self.base_url}/lipsync_stream", json=payload, timeout=self.timeout
        )
        if response.status_code == 404:
            self.prepare(avatar_key, base_video)
            response = httpx.post(
                f"{self.base_url}/lipsync_stream", json=payload, timeout=self.timeout
            )
        response.raise_for_status()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(response.content)

    def health(self) -> dict:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=3)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
