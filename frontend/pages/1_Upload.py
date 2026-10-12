"""Audio upload and processing progress page."""

from __future__ import annotations

import time

import streamlit as st

from components.api_client import APIError, BackendClient
from components.ui import inject_styles, page_header, status_badge

st.set_page_config(page_title="آپلود صوت", layout="wide")
inject_styles()
page_header("آپلود فایل صوتی", "فایل‌های WAV، MP3، M4A، FLAC و OGG پشتیبانی می‌شوند.")

client = BackendClient()

uploaded = st.file_uploader(
    "انتخاب فایل صوتی فارسی",
    type=["wav", "mp3", "m4a", "flac", "ogg"],
)

if uploaded is not None:
    st.write(f"**نام فایل:** {uploaded.name}")
    st.write(f"**حجم:** {uploaded.size / (1024 * 1024):.2f} MB")
    st.audio(uploaded.getvalue())

    if st.button("شروع پردازش", type="primary"):
        try:
            with st.spinner("در حال آپلود..."):
                result = client.upload(
                    uploaded.name,
                    uploaded.getvalue(),
                    uploaded.type,
                )
            st.success("فایل در صف پردازش قرار گرفت.")
            st.session_state["last_recording_id"] = result["recording_id"]
            st.json(result)
        except APIError as exc:
            st.error(exc.message)

recording_id = st.text_input(
    "شناسه ضبط برای پیگیری وضعیت",
    value=st.session_state.get("last_recording_id", ""),
)

if recording_id and st.button("بروزرسانی وضعیت"):
    try:
        status = client.get_status(recording_id)
        st.write(status_badge(status.get("status", "")))
        st.progress(int(status.get("progress") or 0) / 100.0)
        st.write(f"مرحله فعلی: {status.get('current_step') or '—'}")
        if status.get("error_message"):
            st.error(status["error_message"])
        if status.get("status") == "processing":
            time.sleep(0.2)
            st.info("پردازش در جریان است. دوباره بروزرسانی کنید.")
    except APIError as exc:
        st.error(exc.message)
