from __future__ import annotations

import unicodedata

import regex


class TextTooLong(ValueError):
    def __init__(self, count: int, maximum: int) -> None:
        self.count = count
        self.maximum = maximum
        super().__init__(f"text has {count} graphemes; maximum is {maximum}")


def normalize_short_text(text: str, maximum: int = 20) -> tuple[str, int]:
    normalized = unicodedata.normalize("NFC", text).strip()
    if not normalized:
        raise ValueError("text must not be blank")
    clusters = regex.findall(r"\X", normalized)
    if len(clusters) > maximum:
        raise TextTooLong(len(clusters), maximum)
    return normalized, len(clusters)
