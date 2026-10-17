"""ASR rule-based correction tests."""

from __future__ import annotations

from app.utils.asr_correct import apply_asr_rules


def test_fixes_hoosh_masnooi_garble() -> None:
    raw = (
        "مروز میخواهد در مورد حوشمسنوی صحبت کنم "
        "شاخای حوشمسنوی، حوشمسنوی چارت شاخه داره ایایی داره"
    )
    fixed = apply_asr_rules(raw)
    assert "هوش مصنوعی" in fixed
    assert "حوشمسنوی" not in fixed
    assert "امروز" in fixed
    assert "شاخه‌های" in fixed
    assert "AI" in fixed


def test_leaves_clean_persian() -> None:
    text = "امروز می‌خوام در مورد هوش مصنوعی صحبت کنم"
    assert "هوش مصنوعی" in apply_asr_rules(text)
