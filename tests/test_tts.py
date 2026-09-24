from pathlib import Path

from digital_human.backends.tts import MLXQwenTTS


def test_voice_names_are_case_insensitive(monkeypatch, tmp_path):
    seen = {}

    class Result:
        audio = [0.0, 0.1, -0.1]
        sample_rate = 24_000

    class Model:
        def get_supported_speakers(self):
            return ["vivian", "serena"]

        def generate_custom_voice(self, **kwargs):
            seen.update(kwargs)
            yield Result()

    backend = MLXQwenTTS("unused", "revision")
    monkeypatch.setattr(backend, "_load", lambda: Model())
    backend.synthesize("你好", "Vivian", "Chinese", tmp_path / "voice.wav")
    assert seen["speaker"] == "vivian"
