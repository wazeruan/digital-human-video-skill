import pytest

from digital_human.text import TextTooLong, normalize_short_text


def test_counts_graphemes_not_codepoints():
    text, count = normalize_short_text(" 你好e\u0301 ", 3)
    assert text == "你好é"
    assert count == 3


def test_rejects_more_than_twenty():
    with pytest.raises(TextTooLong) as exc:
        normalize_short_text("一" * 21, 20)
    assert exc.value.count == 21
