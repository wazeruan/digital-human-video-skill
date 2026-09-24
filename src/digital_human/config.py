from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="DIGITAL_HUMAN_", extra="ignore"
    )

    backend: Literal["fake", "local"] = "fake"
    render_mode: Literal["musetalk", "loop"] = "musetalk"
    motion_backend: Literal["static", "liveportrait"] = "static"
    liveportrait_dir: Path = Path("vendor/LivePortrait")
    liveportrait_python: str = "vendor/LivePortrait/.venv/bin/python"
    liveportrait_driving: Path = Path("data/motion/licensed-driver.mp4")
    liveportrait_revision: str = "9b294b3d0536135442ea73cb01e6cb3ca7029dd3"
    liveportrait_driving_multiplier: float = Field(default=1.0, gt=0, le=2.0)
    data_dir: Path = Path("data")
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    musetalk_url: str = "http://127.0.0.1:8001"
    musetalk_revision: str = "7fd019315127d7f31e2e7f9853547ddceabbeb6e"
    musetalk_mask_upper_boundary_ratio: float = Field(default=0.5, ge=0.35, le=0.65)
    qwen_model: str = "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit"
    qwen_revision: str = "049ef77fe8816b536193c0c25f9a214d17921282"
    default_voice: str = "Vivian"
    openai_image_model: str = "gpt-image-2.5-flare"
    max_text_graphemes: int = 20
    max_upload_bytes: int = 12 * 1024 * 1024
    queue_size: int = 8
    idle_seconds: float = 0.04
    fps: int = Field(default=25, ge=20, le=30)
    public_base_url: str = ""

    @model_validator(mode="after")
    def validate_loop_motion(self) -> Settings:
        if self.render_mode == "loop" and self.motion_backend != "liveportrait":
            raise ValueError("render_mode=loop requires motion_backend=liveportrait")
        return self

    @property
    def resolved_data_dir(self) -> Path:
        return self.data_dir.expanduser().resolve()
