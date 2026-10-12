"""Persian Speech Intelligence — Streamlit entrypoint / Dashboard."""

from __future__ import annotations

import streamlit as st

from components.api_client import APIError, BackendClient
from components.ui import inject_styles, page_header, status_badge

st.set_page_config(
    page_title="Persian Speech Intelligence",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()
page_header(
    "Persian Speech Intelligence",
    "پلتفرم تحلیل هوشمند گفتار فارسی — رونویسی، خلاصه‌سازی، استخراج اطلاعات و پرسش‌وپاسخ",
)

client = BackendClient()

with st.sidebar:
    st.markdown("### ناوبری")
    st.page_link("app.py", label="داشبورد", icon="📊")
    st.page_link("pages/1_Upload.py", label="آپلود صوت", icon="⬆️")
    st.page_link("pages/2_Transcript.py", label="رونوشت", icon="📝")
    st.page_link("pages/3_Analysis.py", label="تحلیل هوش مصنوعی", icon="🧠")
    st.page_link("pages/4_Ask_AI.py", label="پرسش از هوش مصنوعی", icon="💬")
    st.page_link("pages/5_Export.py", label="خروجی و حذف", icon="📦")
    st.divider()
    try:
        health = client.health()
        st.success(f"Backend: {health.get('status', 'ok')}")
    except Exception as exc:
        st.error(f"Backend unreachable: {exc}")

st.markdown('<div class="rtl">', unsafe_allow_html=True)
st.subheader("نمای کلی")

try:
    stats = client.stats()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("کل فایل‌ها", stats.get("total_recordings", 0))
    c2.metric("تکمیل‌شده", stats.get("completed", 0))
    c3.metric("در حال پردازش", stats.get("processing", 0))
    c4.metric("در صف", stats.get("pending", 0))
    c5.metric("ناموفق", stats.get("failed", 0))
except APIError as exc:
    st.warning(f"آمار در دسترس نیست: {exc.message}")
except Exception as exc:
    st.warning(f"آمار در دسترس نیست: {exc}")

st.subheader("آخرین فایل‌های صوتی")
try:
    data = client.list_recordings(limit=20)
    items = data.get("items") or []
    if not items:
        st.info("هنوز فایلی آپلود نشده است. از صفحه آپلود شروع کنید.")
    else:
        for item in items:
            cols = st.columns([3, 2, 2, 2])
            cols[0].write(item.get("original_filename"))
            cols[1].write(status_badge(item.get("processing_status", "")))
            duration = item.get("duration_seconds")
            cols[2].write(f"{duration:.1f}s" if duration is not None else "—")
            cols[3].write(str(item.get("id", ""))[:8] + "…")
except APIError as exc:
    st.error(exc.message)
except Exception as exc:
    st.error(str(exc))

st.markdown("</div>", unsafe_allow_html=True)
