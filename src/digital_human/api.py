from __future__ import annotations

import base64
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .backends.lipsync import CachedLoop, FakeLipSync, MuseTalkHTTP
from .backends.motion import LivePortraitMotion, StaticMotion, liveportrait_available
from .backends.tts import FakeToneTTS, MLXQwenTTS
from .config import Settings
from .ffmpeg import FFmpeg
from .models import JobStatus, RenderRequest
from .service import IdempotencyConflict, QueueFull, RenderService
from .store import Store
from .text import TextTooLong

logger = logging.getLogger(__name__)


class AvatarPrompt(BaseModel):
    prompt: str = Field(min_length=10, max_length=4000)


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings()
    media = FFmpeg(cfg.ffmpeg, cfg.ffprobe)
    if cfg.motion_backend == "liveportrait":
        motion = LivePortraitMotion(
            media,
            cfg.liveportrait_dir,
            cfg.liveportrait_python,
            cfg.liveportrait_driving,
            cfg.liveportrait_revision,
            cfg.liveportrait_driving_multiplier,
        )
    else:
        motion = StaticMotion(media)
    store = Store(cfg.resolved_data_dir, media, cfg.idle_seconds, cfg.fps, motion)
    if cfg.backend == "local":
        tts = MLXQwenTTS(cfg.qwen_model, cfg.qwen_revision)
    else:
        tts = FakeToneTTS()
    if cfg.render_mode == "loop":
        lipsync = CachedLoop()
    elif cfg.backend == "local":
        lipsync = MuseTalkHTTP(
            cfg.musetalk_url,
            cfg.musetalk_revision,
            cfg.musetalk_mask_upper_boundary_ratio,
        )
    else:
        lipsync = FakeLipSync()
    service = RenderService(
        store=store,
        tts=tts,
        lipsync=lipsync,
        media=media,
        default_voice=cfg.default_voice,
        max_text=cfg.max_text_graphemes,
        queue_size=cfg.queue_size,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await service.start()
        yield
        await service.stop()

    app = FastAPI(
        title="Local Digital Human MVP",
        version="0.1.0",
        lifespan=lifespan,
        description="Short Chinese TTS with cached face motion or MuseTalk for Apple Silicon.",
    )
    app.state.settings = cfg
    app.state.store = store
    app.state.service = service

    def job_view(job):
        data = job.model_dump(mode="json", exclude={"result_path", "request_digest"})
        if job.status == JobStatus.FAILED and job.error_code not in {
            "queue_full",
            "server_restarted",
        }:
            # Keep upstream errors and local paths in the local server log/DB,
            # not in a response that may be copied to another client.
            data["error_code"] = "render_failed"
            data["error_message"] = "Render failed; inspect the local server log."
        data["status_url"] = f"/v1/jobs/{job.job_id}"
        data["result_url"] = (
            f"/v1/jobs/{job.job_id}/result"
            if job.status == JobStatus.SUCCEEDED
            else None
        )
        return data

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "ffmpeg": media.available(), "backend": cfg.backend,
                "render_mode": cfg.render_mode}

    @app.get("/readyz")
    def readyz():
        worker_ok = bool(service.worker_task and not service.worker_task.done())
        lipsync_health = lipsync.health()
        motion_ok = cfg.motion_backend == "static" or liveportrait_available(
            cfg.liveportrait_dir, cfg.liveportrait_python, cfg.liveportrait_driving
        )
        ready = media.available() and worker_ok and motion_ok and bool(lipsync_health.get("ok"))
        return {
            "ready": ready,
            "worker": worker_ok,
            "ffmpeg": media.available(),
            "lipsync": lipsync_health,
            "motion": {"backend": cfg.motion_backend, "available": motion_ok},
        }

    @app.post("/v1/avatars", status_code=status.HTTP_201_CREATED)
    async def create_avatar(image: UploadFile = File(...)):
        raw = await image.read(cfg.max_upload_bytes + 1)
        if len(raw) > cfg.max_upload_bytes:
            raise HTTPException(status_code=413, detail="avatar image is too large")
        try:
            avatar = await __import__("asyncio").to_thread(
                store.create_avatar, raw, f"{lipsync.revision}|{motion.revision}"
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return avatar.model_dump(mode="json", exclude={"source_path", "base_video_path"})

    @app.post("/v1/avatars/generate", status_code=status.HTTP_201_CREATED)
    async def generate_avatar(body: AvatarPrompt):
        try:
            from openai import OpenAI

            result = await __import__("asyncio").to_thread(
                OpenAI().images.generate,
                model=cfg.openai_image_model,
                prompt=body.prompt,
                size="1024x1024",
                quality="medium",
            )
            encoded = result.data[0].b64_json
            if not encoded:
                raise RuntimeError("OpenAI returned no image bytes")
            avatar = await __import__("asyncio").to_thread(
                store.create_avatar, base64.b64decode(encoded), f"{lipsync.revision}|{motion.revision}"
            )
            return avatar.model_dump(
                mode="json", exclude={"source_path", "base_video_path"}
            )
        except Exception as exc:
            logger.exception("OpenAI avatar generation failed")
            raise HTTPException(
                status_code=502,
                detail={"code": "image_generation_failed"},
            ) from exc

    @app.get("/v1/avatars/{avatar_id}")
    def get_avatar(avatar_id: str):
        avatar = store.get_avatar(avatar_id)
        if not avatar:
            raise HTTPException(status_code=404, detail="avatar not found")
        return avatar.model_dump(mode="json", exclude={"source_path", "base_video_path"})

    @app.post("/v1/renders", status_code=status.HTTP_202_ACCEPTED)
    async def create_render(
        body: RenderRequest,
        idempotency_key: str | None = Header(default=None, max_length=200),
    ):
        try:
            job = await service.create_job(body, idempotency_key)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except TextTooLong as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "text_too_long", "count": exc.count, "max": exc.maximum},
            ) from exc
        except ValueError as exc:
            code = 409 if isinstance(exc, IdempotencyConflict) else 422
            raise HTTPException(status_code=code, detail=str(exc)) from exc
        except QueueFull as exc:
            raise HTTPException(status_code=503, detail=str(exc), headers={"Retry-After": "5"})
        return job_view(job)

    @app.get("/v1/jobs/{job_id}")
    def get_job(job_id: str):
        job = store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")
        return job_view(job)

    @app.get("/v1/jobs/{job_id}/result")
    def get_result(job_id: str):
        job = store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")
        if job.status != JobStatus.SUCCEEDED or not job.result_path:
            raise HTTPException(status_code=409, detail=f"job is {job.status}")
        expected_dir = (store.jobs / job.job_id).resolve()
        try:
            path = Path(job.result_path).resolve(strict=True)
        except (OSError, RuntimeError):
            raise HTTPException(status_code=410, detail="result file is missing")
        if (
            not path.is_file()
            or path.suffix.lower() != ".mp4"
            or not path.is_relative_to(expected_dir)
        ):
            logger.error("Rejected result path outside the job directory for %s", job_id)
            raise HTTPException(status_code=500, detail="result file is invalid")
        return FileResponse(path, media_type="video/mp4", filename=f"{job_id}.mp4")

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("digital_human.api:app", host="127.0.0.1", port=8000, workers=1)
