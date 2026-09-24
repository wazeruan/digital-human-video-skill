from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RenderRequest(BaseModel):
    avatar_id: str = Field(min_length=8, max_length=128)
    text: str = Field(min_length=1, max_length=256)
    voice: str | None = Field(default=None, max_length=80)
    language: str = Field(default="Chinese", max_length=40)


class JobRecord(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    stage: str = "queued"
    avatar_id: str
    text: str
    voice: str
    language: str
    request_digest: str
    idempotency_key: str | None = None
    result_path: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class AvatarRecord(BaseModel):
    avatar_id: str
    cache_key: str
    status: str = "ready"
    source_path: str
    base_video_path: str
    created_at: str = Field(default_factory=utc_now)
