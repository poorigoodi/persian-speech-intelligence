"""Export and deletion page."""

from __future__ import annotations

import streamlit as st

from components.api_client import APIError, BackendClient
from components.ui import inject_styles, page_header, render_sidebar

st.set_page_config(
    page_title="Export & settings | Persian Speech Intelligence",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_styles()
render_sidebar(active="Export & settings")
page_header(
    "Export & settings",
    "Download analysis reports and safely delete recordings.",
)

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
selected_label = st.selectbox("Select file", options=list(options.keys()) or ["—"])
recording_id = options.get(selected_label) if options else None
manual_id = st.text_input("Or paste recording ID", value=st.session_state.get("last_recording_id", ""))
recording_id = manual_id.strip() or recording_id

fmt = st.selectbox("Export format", ["json", "txt", "markdown"])

if recording_id and st.button("Prepare download", type="primary"):
    try:
        content = client.export(recording_id, fmt)
        ext = {"json": "json", "txt": "txt", "markdown": "md"}[fmt]
        mime = {
            "json": "application/json",
            "txt": "text/plain",
            "markdown": "text/markdown",
        }[fmt]
        st.download_button(
            "Save file",
            data=content,
            file_name=f"{recording_id}.{ext}",
            mime=mime,
        )
        st.code(content[:4000], language="json" if fmt == "json" else None)
    except APIError as exc:
        st.error(exc.message)

st.divider()
st.subheader("Delete recording")
st.warning(
    "This permanently removes the audio file, transcript, analysis, and vector index."
)
confirm = st.checkbox("I confirm deletion")
if recording_id and confirm and st.button("Delete permanently", type="secondary"):
    try:
        result = client.delete(recording_id)
        st.success(result.get("message", "Deleted."))
        st.session_state.pop("last_recording_id", None)
        st.session_state.pop("transcript_data", None)
        st.session_state.pop("analysis_data", None)
        st.session_state.pop("analysis_meta", None)
    except APIError as exc:
        st.error(exc.message)
