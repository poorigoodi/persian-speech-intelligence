"""Shared Streamlit UI helpers with Persian RTL support."""

from __future__ import annotations

import streamlit as st

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700&display=swap');

html, body, [class*="css"] {
  font-family: 'Vazirmatn', Tahoma, sans-serif;
}

.rtl {
  direction: rtl;
  text-align: right;
}

.psi-hero {
  background: linear-gradient(135deg, #0f3d3e 0%, #1a5f61 45%, #c4a35a 100%);
  color: #f7f3e8;
  padding: 1.4rem 1.6rem;
  border-radius: 16px;
  margin-bottom: 1.2rem;
}

.psi-hero h1 {
  margin: 0;
  font-size: 1.7rem;
  font-weight: 700;
}

.psi-hero p {
  margin: 0.4rem 0 0 0;
  opacity: 0.92;
}

.metric-card {
  background: #f7f3e8;
  border: 1px solid #d9c9a3;
  border-radius: 12px;
  padding: 0.9rem 1rem;
}

.segment-row {
  background: #faf8f3;
  border-right: 4px solid #1a5f61;
  padding: 0.6rem 0.8rem;
  margin-bottom: 0.45rem;
  border-radius: 8px;
}

.evidence-box {
  background: #eef6f6;
  border: 1px solid #b7d4d5;
  border-radius: 10px;
  padding: 0.75rem;
  margin-top: 0.5rem;
}
</style>
"""


def inject_styles() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="psi-hero rtl">
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_timestamp(seconds: float | None) -> str:
    if seconds is None:
        return "--:--"
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def status_badge(status: str) -> str:
    colors = {
        "pending": "🟡",
        "processing": "🔵",
        "completed": "🟢",
        "failed": "🔴",
    }
    return f"{colors.get(status, '⚪')} {status}"
