"""AI analysis dashboard."""

from __future__ import annotations

import json

import streamlit as st

from components.api_client import APIError, BackendClient
from components.ui import inject_styles, page_header

st.set_page_config(page_title="تحلیل", layout="wide")
inject_styles()
page_header("تحلیل هوش مصنوعی", "خلاصه، موضوعات، احساسات متنی، موجودیت‌ها و اقدامات")

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

if recording_id and st.button("بارگذاری تحلیل", type="primary"):
    try:
        analysis = client.get_analysis(recording_id)
        st.session_state["analysis_data"] = analysis
    except APIError as exc:
        st.error(exc.message)

analysis = st.session_state.get("analysis_data")
if analysis:
    st.markdown('<div class="rtl">', unsafe_allow_html=True)
    st.subheader("خلاصه کوتاه")
    st.write(analysis.get("short_summary") or "—")

    st.subheader("خلاصه تفصیلی")
    detailed = analysis.get("detailed_summary") or {}
    if isinstance(detailed, dict):
        st.write(f"**بحث اصلی:** {detailed.get('main_discussion') or '—'}")
        st.write("**نکات مهم:**")
        for point in detailed.get("important_points") or []:
            st.write(f"- {point}")
        st.write("**تصمیم‌ها:**")
        for item in detailed.get("decisions") or []:
            st.write(f"- {item}")
        st.write("**اقدامات:**")
        for item in detailed.get("action_items") or []:
            st.write(f"- {item}")
        st.write("**سؤالات باز:**")
        for item in detailed.get("open_questions") or []:
            st.write(f"- {item}")
        st.write("**نتیجه‌گیری:**")
        for item in detailed.get("final_conclusions") or []:
            st.write(f"- {item}")
    else:
        st.write(detailed)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("موضوعات")
        for topic in analysis.get("topics") or []:
            if isinstance(topic, dict):
                st.write(f"**{topic.get('name')}** — {topic.get('description')}")
            else:
                st.write(topic)
    with col2:
        st.subheader("احساسات زبانی متن")
        sentiment = analysis.get("sentiment") or {}
        if isinstance(sentiment, dict):
            st.write(f"**برچسب:** {sentiment.get('label')}")
            st.write(sentiment.get("explanation") or "")
            st.caption(sentiment.get("disclaimer") or "")
        else:
            st.write(sentiment)

    st.subheader("موجودیت‌های استخراج‌شده")
    st.code(
        json.dumps(analysis.get("extracted_entities") or {}, ensure_ascii=False, indent=2),
        language="json",
    )

    st.subheader("اقدامات و تصمیم‌ها")
    st.write("**اقدامات:**")
    st.code(
        json.dumps(analysis.get("action_items") or [], ensure_ascii=False, indent=2),
        language="json",
    )
    st.write("**تصمیم‌ها:**")
    st.code(
        json.dumps(analysis.get("decisions") or [], ensure_ascii=False, indent=2),
        language="json",
    )
    st.markdown("</div>", unsafe_allow_html=True)
