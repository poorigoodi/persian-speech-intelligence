"""Persian-aware text normalization.

Preserves semantic meaning and informal expressions. Does not aggressively rewrite.
"""

from __future__ import annotations

import re
import unicodedata

# Arabic characters commonly appearing in Persian text → Persian equivalents
_ARABIC_TO_PERSIAN = str.maketrans(
    {
        "\u0643": "\u06a9",  # ك → ک
        "\u0649": "\u06cc",  # ى → ی
        "\u064a": "\u06cc",  # ي → ی
        "\u06c1": "\u0647",  # ہ → ه
        "\u0629": "\u0647",  # ة → ه
        "\u0660": "۰",
        "\u0661": "۱",
        "\u0662": "۲",
        "\u0663": "۳",
        "\u0664": "۴",
        "\u0665": "۵",
        "\u0666": "۶",
        "\u0667": "۷",
        "\u0668": "۸",
        "\u0669": "۹",
    }
)

_DIGIT_TO_PERSIAN = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# Zero-width characters to remove (keep ZWNJ as spacing control separately)
_ZW_REMOVE = re.compile(r"[\u200b\u200c\u200d\ufeff]+")
_MULTI_SPACE = re.compile(r"[ \t\f\v]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_PUNCT_SPACE = re.compile(r"\s+([،؛:!؟?.,])")


def normalize_persian_text(text: str, *, convert_digits: bool = False) -> str:
    """Normalize Persian transcript text without changing meaning.

    Args:
        text: Raw transcript text.
        convert_digits: If True, convert ASCII digits to Persian digits.
            Default False to preserve mixed Persian-English technical content.
    """
    if not text:
        return ""

    # Unicode NFC normalization
    normalized = unicodedata.normalize("NFC", text)

    # Character variant mapping
    normalized = normalized.translate(_ARABIC_TO_PERSIAN)

    if convert_digits:
        normalized = normalized.translate(_DIGIT_TO_PERSIAN)

    # Normalize zero-width chars: collapse runs of ZWNJ to a single ZWNJ
    # when between letters; otherwise remove.
    normalized = re.sub(r"\u200c+", "\u200c", normalized)
    normalized = re.sub(r"[\u200b\u200d\ufeff]", "", normalized)

    # Punctuation spacing and whitespace
    normalized = _PUNCT_SPACE.sub(r"\1", normalized)
    normalized = _MULTI_SPACE.sub(" ", normalized)
    normalized = _MULTI_NEWLINE.sub("\n\n", normalized)
    normalized = normalized.strip()

    return normalized


def normalize_for_evaluation(text: str) -> str:
    """Stricter normalization used only for ASR evaluation metrics."""
    normalized = normalize_persian_text(text, convert_digits=True)
    normalized = normalized.replace("\u200c", " ")
    normalized = re.sub(r"[^\w\s\u0600-\u06FF]", " ", normalized, flags=re.UNICODE)
    normalized = _MULTI_SPACE.sub(" ", normalized).strip().lower()
    return normalized
