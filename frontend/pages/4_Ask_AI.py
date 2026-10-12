"""Grounded Persian Q&A chat interface."""

from __future__ import annotations

import streamlit as st

from components.api_client import APIError, BackendClient
from components.ui import format_timestamp, inject_styles, page_header

st.set_page_config(page_title="پرسش از AI", layout="wide")
inject_styles()
page_header(
    "پرسش از هوش مصنوعی",
    "پاسخ‌ها فقط بر اساس شواهد رونوشت همان فایل تولید می‌شوند.",
)

client = BackendClient()

try:
    recordings = (client.list_recordings(limit=100).get("items") or [])
except Exception:
    recordings = []

options = {
    f"{r.get('original_filename')} ({str(r.get('id'))[:8]}…)": r.get("id")
    for r in recordings
    if r.get("processing_status") == "completed"
}
selected_label = st.selectbox("انتخاب فایل", options=list(options.keys()) or ["—"])
recording_id = options.get(selected_label) if options else None
manual_id = st.text_input("یا شناسه", value=st.session_state.get("last_recording_id", ""))
recording_id = manual_id.strip() or recording_id

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

question = st.text_input(
    "سؤال خود را به فارسی بپرسید",
    placeholder="جلسه درباره چه موضوعی بود؟",
)

if st.button("ارسال سؤال", type="primary") and recording_id and question.strip():
    try:
        with st.spinner("در حال بازیابی شواهد و تولید پاسخ..."):
            answer = client.chat(recording_id, question.strip())
        st.session_state.chat_history.append(answer)
    except APIError as exc:
        st.error(exc.message)

for item in reversed(st.session_state.chat_history):
    st.markdown('<div class="rtl">', unsafe_allow_html=True)
    st.markdown(f"**سؤال:** {item.get('question')}")
    st.markdown(f"**پاسخ:** {item.get('answer')}")
    grounded = "مستند" if item.get("grounded") else "امتناع / بدون شواهد کافی"
    st.caption(f"وضعیت: {grounded}")
    evidence = item.get("evidence") or []
    if evidence:
        st.markdown("**شواهد:**")
        for ev in evidence:
            st.markdown(
                f'<div class="evidence-box rtl">'
                f"{format_timestamp(ev.get('start_time'))} → "
                f"{format_timestamp(ev.get('end_time'))}<br/>{ev.get('text')}</div>",
                unsafe_allow_html=True,
            )
    st.divider()
    st.markdown("</div>", unsafe_allow_html=True)
