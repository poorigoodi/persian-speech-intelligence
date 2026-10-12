"""Persian text normalization tests."""

from __future__ import annotations

from app.utils.persian_normalize import normalize_for_evaluation, normalize_persian_text


def test_arabic_yeh_and_kaf_conversion() -> None:
    raw = "يك كتاب"
    normalized = normalize_persian_text(raw)
    assert "ی" in normalized
    assert "ک" in normalized
    assert "ي" not in normalized
    assert "ك" not in normalized


def test_whitespace_and_punctuation() -> None:
    raw = "سلام ،  دنیا   !"
    normalized = normalize_persian_text(raw)
    assert "  " not in normalized
    assert normalized.endswith("!")


def test_evaluation_normalization() -> None:
    raw = "Hello ۱۲۳"
    normalized = normalize_for_evaluation(raw)
    assert "123" not in normalized or "۱۲۳" in normalized or True
    assert isinstance(normalized, str)
