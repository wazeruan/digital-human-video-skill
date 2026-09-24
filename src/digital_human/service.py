from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sqlite3
import uuid
from pathlib import Path

from .backends.lipsync import LipSyncBackend
from .backends.tts import TTSBackend
from .ffmpeg import FFmpeg
from .models import JobRecord, JobStatus, RenderRequest, utc_now
from .store import Store
from .text import normalize_short_text

logger = logging.getLogger(__name__)


class IdempotencyConflict(ValueError):
    pass


class QueueFull(RuntimeError):
    pass


class RenderService:
    def __init__(
        self,
        store: Store,
        tts: TTSBackend,
        lipsync: LipSyncBackend,
        media: FFmpeg,
        default_voice: str,
        max_text: int,
        queue_size: int,
    ) -> None:
        self.store = store
        self.tts = tts
        self.lipsync = lipsync
        self.media = media
        self.default_voice = default_voice
        self.max_text = max_text
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=queue_size)
        self.worker_task: asyncio.Task | None = None
        self._prepared_avatars: set[str] = set()

    async def start(self) -> None:
        self.worker_task = asyncio.create_task(self._worker(), name="render-worker")

    async def stop(self) -> None:
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

    async def create_job(
        self, request: RenderRequest, idempotency_key: str | None
    ) -> JobRecord:
        text, _ = normalize_short_text(request.text, self.max_text)
        if self.store.get_avatar(request.avatar_id) is None:
            raise KeyError("avatar not found")
        voice = request.voice or self.default_voice
        canonical = json.dumps(
            {
                "avatar_id": request.avatar_id,
                "text": text,
                "voice": voice,
                "language": request.language,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        if idempotency_key:
            previous = self.store.get_by_idempotency(idempotency_key)
            if previous:
                if previous.request_digest != digest:
                    raise IdempotencyConflict(
                        "the Idempotency-Key was already used for a different request"
                    )
                return previous
        job = JobRecord(
            job_id=uuid.uuid4().hex,
            avatar_id=request.avatar_id,
            text=text,
            voice=voice,
            language=request.language,
            request_digest=digest,
            idempotency_key=idempotency_key,
        )
        try:
            self.store.save_job(job)
        except sqlite3.IntegrityError:
            previous = self.store.get_by_idempotency(idempotency_key or "")
            if previous and previous.request_digest == digest:
                return previous
            raise IdempotencyConflict("idempotency conflict")
        try:
            self.queue.put_nowait(job.job_id)
        except asyncio.QueueFull as exc:
            job.status = JobStatus.FAILED
            job.error_code = "queue_full"
            job.error_message = "Render queue is full; retry later."
            self.store.save_job(job)
            raise QueueFull(job.error_message) from exc
        return job

    async def _worker(self) -> None:
        while True:
            job_id = await self.queue.get()
            try:
                await asyncio.to_thread(self._run_job, job_id)
            finally:
                self.queue.task_done()

    def _run_job(self, job_id: str) -> None:
        job = self.store.get_job(job_id)
        if not job:
            return
        avatar = self.store.get_avatar(job.avatar_id)
        if not avatar:
            return
        work = self.store.job_dir(job.job_id)
        audio = work / "speech.wav"
        raw_video = work / "lipsync.mp4"
        final = work / "final.mp4"
        try:
            job.status = JobStatus.RUNNING
            job.stage = "tts"
            job.updated_at = utc_now()
            self.store.save_job(job)
            self.tts.synthesize(job.text, job.voice, job.language, audio)
            self.media.probe(audio)

            job.stage = "lipsync"
            job.updated_at = utc_now()
            self.store.save_job(job)
            if avatar.cache_key not in self._prepared_avatars:
                self.lipsync.prepare(avatar.cache_key, Path(avatar.base_video_path))
                self._prepared_avatars.add(avatar.cache_key)
            self.lipsync.render(
                avatar.cache_key, audio, Path(avatar.base_video_path), raw_video
            )

            job.stage = "compose"
            job.updated_at = utc_now()
            self.store.save_job(job)
            self.media.mux(raw_video, audio, final)
            self.media.probe(final)

            job.status = JobStatus.SUCCEEDED
            job.stage = "done"
            job.result_path = str(final)
        except Exception as exc:
            logger.exception("Render job %s failed", job_id)
            job.status = JobStatus.FAILED
            job.stage = "failed"
            job.error_code = type(exc).__name__
            job.error_message = str(exc)[:1000]
        finally:
            job.updated_at = utc_now()
            self.store.save_job(job)
