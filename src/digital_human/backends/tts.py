from __future__ import annotations

import math
import wave
from pathlib import Path
from threading import Lock
from typing import Protocol


class TTSBackend(Protocol):
    revision: str

    def synthesize(self, text: str, voice: str, language: str, output: Path) -> None: ...


class FakeToneTTS:
    revision = "fake-tone-v1"

    def synthesize(self, text: str, voice: str, language: str, output: Path) -> None:
        sample_rate = 24_000
        duration = max(0.55, min(5.0, 0.16 * len(text) + 0.25))
        frames = int(sample_rate * duration)
        output.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            data = bytearray()
            for i in range(frames):
                fade = min(1.0, i / 480, (frames - i) / 480)
                value = int(5500 * fade * math.sin(2 * math.pi * 220 * i / sample_rate))
                data.extend(value.to_bytes(2, "little", signed=True))
            wav.writeframes(bytes(data))


class MLXQwenTTS:
    def __init__(self, model_id: str, model_revision: str) -> None:
        self.model_id = model_id
        self.model_revision = model_revision
        self.revision = f"mlx-audio-0.5.4:{model_id}@{model_revision}"
        self._model = None
        self._lock = Lock()

    def _load(self):
        if self._model is None:
            try:
                from mlx_audio.tts.utils import load_model
            except ImportError as exc:
                raise RuntimeError(
                    "MLX-Audio is not installed. Run: uv sync --frozen --extra tts"
                ) from exc
            self._model = load_model(self.model_id, revision=self.model_revision)
        return self._model

    def synthesize(self, text: str, voice: str, language: str, output: Path) -> None:
        import numpy as np
        import soundfile as sf

        with self._lock:
            model = self._load()
            supported = model.get_supported_speakers()
            speaker_map = {item.casefold(): item for item in supported or []}
            resolved_voice = speaker_map.get(voice.casefold(), voice)
            if supported and resolved_voice not in supported:
                raise ValueError(f"voice {voice!r} is not supported; choose one of {supported}")
            results = list(
                model.generate_custom_voice(
                    text=text, speaker=resolved_voice, language=language
                )
            )
            if not results:
                raise RuntimeError("Qwen3-TTS returned no audio")
            chunks = [np.asarray(item.audio).reshape(-1) for item in results]
            audio = np.concatenate(chunks)
            peak = float(np.max(np.abs(audio))) if audio.size else 0.0
            if peak > 1.0:
                audio = audio / peak
            sample_rate = int(
                getattr(results[0], "sample_rate", getattr(model, "sample_rate", 24_000))
            )
            output.parent.mkdir(parents=True, exist_ok=True)
            sf.write(output, audio, sample_rate, subtype="PCM_16")
