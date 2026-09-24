from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import sqlite3
import stat
import tempfile
import warnings
from pathlib import Path
from threading import Lock

from PIL import Image, ImageOps

from .ffmpeg import FFmpeg
from .backends.motion import MotionBackend, StaticMotion
from .models import AvatarRecord, JobRecord, JobStatus, utc_now

Image.MAX_IMAGE_PIXELS = 25_000_000
logger = logging.getLogger(__name__)


def _ensure_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        if path.is_symlink() or not path.is_dir():
            raise ValueError(f"data path must be a real directory: {path}")
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            logger.warning(
                "Existing data directory %s is accessible to group/others; "
                "leaving its permissions unchanged",
                path,
            )
    else:
        # Only tighten a directory this process just created. Never chmod an
        # arbitrary operator-supplied or pre-existing shared directory.
        path.chmod(0o700)


def _ensure_database_file(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"database path must not be a symbolic link: {path}")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        if not path.is_file():
            raise ValueError(f"database path must be a regular file: {path}")
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            logger.warning(
                "Existing database %s is accessible to group/others; "
                "leaving its permissions unchanged",
                path,
            )
    else:
        os.close(fd)


class Store:
    PREPROCESSOR_VERSION = "avatar-png-v1"

    def __init__(self, root: Path, media: FFmpeg, idle_seconds: float, fps: int, motion: MotionBackend | None = None) -> None:
        self.root = root
        self.media = media
        self.idle_seconds = idle_seconds
        self.fps = fps
        self.motion = motion or StaticMotion(media)
        self.avatars = root / "avatars"
        self.jobs = root / "jobs"
        for directory in (self.root, self.avatars, self.jobs):
            _ensure_directory(directory)
        self._lock = Lock()
        self._canonicalization_lock = Lock()
        self.db = root / "state.sqlite3"
        _ensure_database_file(self.db)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                idempotency_key TEXT UNIQUE, request_digest TEXT NOT NULL)"""
            )
            rows = conn.execute("SELECT job_id,payload FROM jobs").fetchall()
            for row in rows:
                job = JobRecord.model_validate_json(row["payload"])
                if job.status in {JobStatus.RUNNING, JobStatus.QUEUED}:
                    job.status = JobStatus.FAILED
                    job.stage = "interrupted"
                    job.error_code = "server_restarted"
                    job.error_message = "The service restarted before this job completed."
                    job.updated_at = utc_now()
                    conn.execute(
                        "UPDATE jobs SET payload=? WHERE job_id=?",
                        (job.model_dump_json(), job.job_id),
                    )

    @staticmethod
    def canonical_png(raw: bytes) -> bytes:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as opened:
                    if getattr(opened, "is_animated", False):
                        raise ValueError("animated images are not supported")
                    if opened.width * opened.height > Image.MAX_IMAGE_PIXELS:
                        raise ValueError("avatar image exceeds the pixel limit")
                    if opened.width < 256 or opened.height < 256:
                        raise ValueError("avatar image must be at least 256x256")
                    image = ImageOps.exif_transpose(opened).convert("RGB")
                    image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                    out = io.BytesIO()
                    image.save(out, format="PNG", optimize=True)
                    return out.getvalue()
        except (OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ValueError("invalid or unsafe image") from exc

    def create_avatar(self, raw: bytes, backend_revision: str) -> AvatarRecord:
        # Serialize decoding/resizing so concurrent uploads cannot multiply
        # peak memory use on a 24GB machine.
        with self._canonicalization_lock:
            png = self.canonical_png(raw)
        digest = hashlib.sha256()
        digest.update(png)
        digest.update(self.PREPROCESSOR_VERSION.encode())
        digest.update(backend_revision.encode())
        digest.update(f"fps={self.fps}".encode())
        digest.update(f"idle_seconds={self.idle_seconds}".encode())
        key = digest.hexdigest()
        final_dir = self.avatars / key
        manifest = final_dir / "manifest.json"
        if manifest.exists():
            return AvatarRecord.model_validate_json(manifest.read_text())

        with self._lock:
            if manifest.exists():
                return AvatarRecord.model_validate_json(manifest.read_text())
            tmp = Path(tempfile.mkdtemp(prefix=f".{key[:12]}-", dir=self.avatars))
            try:
                source = tmp / "source.png"
                base_video = tmp / "base.mp4"
                source.write_bytes(png)
                self.motion.build(source, base_video, self.idle_seconds, self.fps)
                record = AvatarRecord(
                    avatar_id=key,
                    cache_key=key,
                    source_path=str(final_dir / "source.png"),
                    base_video_path=str(final_dir / "base.mp4"),
                )
                (tmp / "manifest.json").write_text(record.model_dump_json(indent=2))
                tmp.replace(final_dir)
                return record
            except Exception:
                for child in tmp.glob("*"):
                    child.unlink(missing_ok=True)
                tmp.rmdir()
                raise

    def get_avatar(self, avatar_id: str) -> AvatarRecord | None:
        if not avatar_id.isalnum():
            return None
        manifest = self.avatars / avatar_id / "manifest.json"
        return AvatarRecord.model_validate_json(manifest.read_text()) if manifest.exists() else None

    def save_job(self, job: JobRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO jobs(job_id,payload,idempotency_key,request_digest)
                VALUES(?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET payload=excluded.payload""",
                (job.job_id, job.model_dump_json(), job.idempotency_key, job.request_digest),
            )

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return JobRecord.model_validate_json(row["payload"]) if row else None

    def get_by_idempotency(self, key: str) -> JobRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM jobs WHERE idempotency_key=?", (key,)
            ).fetchone()
        return JobRecord.model_validate_json(row["payload"]) if row else None

    def job_dir(self, job_id: str) -> Path:
        path = self.jobs / job_id
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            if path.is_symlink() or not path.is_dir():
                raise ValueError(f"job path must be a real directory: {path}")
            mode = stat.S_IMODE(path.stat().st_mode)
            if mode & 0o077:
                logger.warning(
                    "Existing job directory %s is accessible to group/others; "
                    "leaving its permissions unchanged",
                    path,
                )
        else:
            path.chmod(0o700)
        return path
