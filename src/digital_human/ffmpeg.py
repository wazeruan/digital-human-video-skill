from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class MediaCommandError(RuntimeError):
    pass


class FFmpeg:
    def __init__(self, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe") -> None:
        self.ffmpeg = shutil.which(ffmpeg) or ffmpeg
        self.ffprobe = shutil.which(ffprobe) or ffprobe

    def available(self) -> bool:
        return bool(shutil.which(self.ffmpeg) and shutil.which(self.ffprobe))

    def _run(self, args: list[str], timeout: float = 120) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                args,
                check=True,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            stderr = getattr(exc, "stderr", "") or ""
            raise MediaCommandError(stderr[-2000:] or str(exc)) from exc

    def still_video(self, image: Path, output: Path, seconds: float, fps: int) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        tmp = output.with_suffix(".tmp.mp4")
        self._run(
            [
                self.ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-loop",
                "1",
                "-i",
                str(image),
                "-t",
                str(seconds),
                "-vf",
                f"scale='min(1024,iw)':-2,fps={fps}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(tmp),
            ]
        )
        tmp.replace(output)

    def mux(self, video: Path, audio: Path, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        tmp = output.with_suffix(".tmp.mp4")
        self._run(
            [
                self.ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(video),
                "-i",
                str(audio),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(tmp),
            ]
        )
        tmp.replace(output)

    def probe(self, path: Path) -> dict:
        result = self._run(
            [
                self.ffprobe,
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            timeout=20,
        )
        return json.loads(result.stdout)
