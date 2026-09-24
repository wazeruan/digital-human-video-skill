from __future__ import annotations

import shutil
import hashlib
import subprocess
from pathlib import Path
from typing import Protocol

from ..ffmpeg import FFmpeg


class MotionBackend(Protocol):
    revision: str

    def build(self, source: Path, output: Path, seconds: float, fps: int) -> None: ...


class StaticMotion:
    revision = "static-v1"

    def __init__(self, media: FFmpeg) -> None:
        self.media = media

    def build(self, source: Path, output: Path, seconds: float, fps: int) -> None:
        self.media.still_video(source, output, seconds, fps)


class LivePortraitMotion:
    """Run the official LivePortrait CLI in its isolated Python environment.

    LivePortrait produces a silent, full-face animation from a source image and
    a short driving clip.  The generated clip is intentionally cached as the
    avatar base video; it can be reused directly or processed by MuseTalk later.
    """

    def __init__(
        self,
        media: FFmpeg,
        repo: Path,
        python: str,
        driving: Path,
        revision: str,
        driving_multiplier: float = 1.0,
    ) -> None:
        self.media = media
        self.repo = repo.expanduser().resolve()
        python_path = Path(python).expanduser()
        # Do not call Path.resolve() here: uv's venv/bin/python is a symlink,
        # and resolving it would bypass the isolated LivePortrait environment.
        self.python = str(python_path.absolute()) if not python_path.is_absolute() else str(python_path)
        self.driving = driving.expanduser().resolve()
        self.model_revision = revision
        self.driving_multiplier = driving_multiplier

    @property
    def revision(self) -> str:
        # Read at avatar creation, so replacing a driver in place invalidates
        # the cache without requiring the API process to restart.
        digest = hashlib.sha256()
        if self.driving.is_file():
            with self.driving.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            driver_hash = digest.hexdigest()
        else:
            driver_hash = "missing"
        return (f"liveportrait:{self.model_revision}:driver={driver_hash}"
                f":multiplier={self.driving_multiplier!r}:v2")

    def build(self, source: Path, output: Path, seconds: float, fps: int) -> None:
        if not (self.repo / "inference.py").exists():
            raise RuntimeError(f"LivePortrait repo is missing: {self.repo}")
        if not self.driving.exists():
            raise RuntimeError(f"LivePortrait driving video is missing: {self.driving}")
        run_dir = output.parent / "liveportrait-run"
        run_dir.mkdir(parents=True, exist_ok=True)
        for old in run_dir.glob("*.mp4"):
            old.unlink(missing_ok=True)
        # Configure a .pkl explicitly to reuse motion analysis. Silently using
        # a sibling template can reuse stale motion after replacing a video.
        driving = self.driving
        command = [
            self.python,
            "inference.py",
            "-s",
            str(source),
            "-d",
            str(driving),
            "-o",
            str(run_dir),
            "--driving_multiplier",
            str(self.driving_multiplier),
        ]
        env = {"PYTORCH_ENABLE_MPS_FALLBACK": "1"}
        import os

        merged_env = os.environ.copy()
        merged_env.update(env)
        try:
            subprocess.run(
                command,
                cwd=self.repo,
                env=merged_env,
                check=True,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=900,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            raise RuntimeError(f"LivePortrait failed: {detail[-2000:]}") from exc
        candidates = sorted(run_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise RuntimeError("LivePortrait produced no mp4 output")
        generated = next((p for p in candidates if "_concat" not in p.stem), candidates[0])
        # Normalize size/fps and keep enough motion for one-line utterances.
        # Preserve the complete cycle: cutting a prepared loop at two seconds
        # would remove its eased end and introduce a jump at every repetition.
        generated_info = self.media.probe(generated)
        generated_seconds = float(generated_info.get("format", {}).get("duration", 0))
        if generated_seconds <= 0:
            raise RuntimeError("LivePortrait output has no positive duration")
        target_seconds = generated_seconds
        output.parent.mkdir(parents=True, exist_ok=True)
        tmp = output.with_suffix(".tmp.mp4")
        self.media._run(
            [
                self.media.ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(generated),
                "-t",
                str(target_seconds),
                "-vf",
                f"scale='min(1024,iw)':-2,fps={fps}",
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(tmp),
            ],
            timeout=180,
        )
        tmp.replace(output)


def liveportrait_available(repo: Path, python: str, driving: Path) -> bool:
    return bool(shutil.which(python) or Path(python).exists()) and (repo / "inference.py").exists() and driving.exists()
