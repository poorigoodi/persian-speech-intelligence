"""Export and deletion page."""

from __future__ import annotations

import streamlit as st

from components.api_client import APIError, BackendClient
from components.ui import inject_styles, page_header

st.set_page_config(page_title="خروجی", layout="wide")
inject_styles()
page_header("خروجی و مدیریت داده", "دانلود گزارش تحلیل و حذف ایمن فایل‌ها")

client = BackendClient()

try:
    recordings = (client.list_recordings(limit=100).get("items") or [])
except Exception:
    recordings = []

options = {
    f"{r.get('original_filename')} [{r.get('processing_status')}] ({str(r.get('id'))[:8]}…)": r.get(
        "id"
    )
    for r in recordings
}
selected_label = st.selectbox("انتخاب فایل", options=list(options.keys()) or ["—"])
recording_id = options.get(selected_label) if options else None
manual_id = st.text_input("یا شناسه", value=st.session_state.get("last_recording_id", ""))
recording_id = manual_id.strip() or recording_id

fmt = st.selectbox("قالب خروجی", ["json", "txt", "markdown"])

if recording_id and st.button("دانلود خروجی", type="primary"):
    try:
        content = client.export(recording_id, fmt)
        ext = {"json": "json", "txt": "txt", "markdown": "md"}[fmt]
        mime = {
            "json": "application/json",
            "txt": "text/plain",
            "markdown": "text/markdown",
        }[fmt]
        st.download_button(
            "ذخیره فایل",
            data=content,
            file_name=f"{recording_id}.{ext}",
            mime=mime,
        )
        st.code(content[:4000], language="json" if fmt == "json" else None)
    except APIError as exc:
        st.error(exc.message)

st.divider()
st.subheader("حذف فایل و داده‌های مرتبط")
st.warning(
    "حذف، فایل صوتی، رونوشت، تحلیل و ایندکس برداری را پاک می‌کند و برگشت‌ناپذیر است."
)
confirm = st.checkbox("حذف را تأیید می‌کنم")
if recording_id and confirm and st.button("حذف دائمی", type="secondary"):
    try:
        result = client.delete(recording_id)
        st.success(result.get("message", "Deleted."))
        st.session_state.pop("last_recording_id", None)
        st.session_state.pop("transcript_data", None)
        st.session_state.pop("analysis_data", None)
    except APIError as exc:
        st.error(exc.message)
