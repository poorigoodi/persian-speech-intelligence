"""Lightweight Persian ASR post-correction (rules + optional LLM polish)."""

from __future__ import annotations

import re

# Common Whisper failures on Persian (especially tech talk).
# Applied before optional LLM polish; keep conservative.
_RULE_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"حوش\s*مسنو[یی]?|حوش\s*مصنوعی|هوشمسنو[عییی]+|هوش\s*مسنو[یی]?|"
            r"حوش\s*مصنوعی|هوش\s*مسنوعی|هوشمصنوعی"
        ),
        "هوش مصنوعی",
    ),
    (re.compile(r"یادگیری\s*ماشین"), "یادگیری ماشین"),
    (re.compile(r"داده\s*کاوی|داده‌کاوی"), "داده‌کاوی"),
    (re.compile(r"شاخای\s+"), "شاخه‌های "),
    (re.compile(r"شاخه\s*های"), "شاخه‌های"),
    (re.compile(r"\bایایی\b|\bای‌ایی\b|\bای ای\b|\bآی\s*آی\b"), "AI"),
    (re.compile(r"^مروز\b"), "امروز"),
    (re.compile(r"(?<=\s)مروز\b"), "امروز"),
    (re.compile(r"میخواهد(?=\s+در\s+مورد)"), "می‌خوام"),
    (re.compile(r"میخواد"), "می‌خواد"),
    (re.compile(r"میخوام"), "می‌خوام"),
    (re.compile(r"میخواهم"), "می‌خواهم"),
    (re.compile(r"صحبت\s*کنم"), "صحبت کنم"),
]


def apply_asr_rules(text: str) -> str:
    """Apply deterministic Persian ASR cleanup rules."""
    if not text:
        return ""
    out = text
    for pattern, repl in _RULE_REPLACEMENTS:
        out = pattern.sub(repl, out)
    out = re.sub(r"[ \t]+", " ", out).strip()
    return out


ASR_POLISH_SYSTEM = """شما ویرایشگر transcript فارسی هستید.
فقط خطاهای واضح تشخیص گفتار (ASR) را اصلاح کنید.
معنی را عوض نکنید، چیزی اضافه یا حذف نکنید مگر برای اصلاح واج/املای غلط.
عبارات تخصصی مثل «هوش مصنوعی» و «AI» را درست بنویسید.
فقط متن اصلاح‌شده را برگردانید؛ توضیح ندهید."""
