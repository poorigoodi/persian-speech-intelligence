"""Timestamped transcript viewer."""

from __future__ import annotations

import streamlit as st

from components.api_client import APIError, BackendClient
from components.ui import format_timestamp, inject_styles, page_header, render_sidebar

st.set_page_config(
    page_title="Transcript | Persian Speech Intelligence",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_styles()
render_sidebar(active="Transcript")
page_header("Transcript", "Timestamped segments and full-text search.")

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

selected_label = st.selectbox(
    "Select completed file",
    options=list(options.keys()) or ["—"],
)
recording_id = options.get(selected_label) if options else None
manual_id = st.text_input(
    "Or paste recording ID", value=st.session_state.get("last_recording_id", "")
)
recording_id = manual_id.strip() or recording_id

query = st.text_input("Search in transcript")

if recording_id and st.button("Load transcript", type="primary"):
    try:
        data = client.get_transcript(recording_id)
        st.session_state["transcript_data"] = data
    except APIError as exc:
        st.error(exc.message)

data = st.session_state.get("transcript_data")
if data:
    full = data.get("full_text_normalized") or data.get("full_text") or ""
    st.text_area("Full text", full, height=180)
    st.download_button(
        "Download text",
        data=full,
        file_name=f"{recording_id}_transcript.txt",
        mime="text/plain",
    )

    segments = data.get("segments") or []
    if query:
        segments = [
            s
            for s in segments
            if query in (s.get("normalized_text") or "")
            or query in (s.get("original_text") or "")
        ]

    st.subheader(f"Segments ({len(segments)})")
    for seg in segments:
        start = format_timestamp(seg.get("start_time"))
        end = format_timestamp(seg.get("end_time"))
        text = seg.get("normalized_text") or seg.get("original_text") or ""
        st.markdown(
            f'<div class="segment-row"><strong>{start} → {end}</strong><br/>{text}</div>',
            unsafe_allow_html=True,
        )
