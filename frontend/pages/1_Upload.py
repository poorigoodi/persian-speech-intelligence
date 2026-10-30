"""Audio upload and processing progress."""

from __future__ import annotations

import html
import time

import streamlit as st

from components.api_client import APIError, BackendClient
from components.ui import inject_styles, page_header, render_sidebar, status_badge

st.set_page_config(
    page_title="Upload | Persian Speech Intelligence",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_styles()
render_sidebar(active="Upload audio")
page_header(
    "Upload audio",
    "Supported formats: WAV, MP3, M4A, FLAC, OGG. Stay on this page until the file finishes selecting.",
)

client = BackendClient()

uploaded = st.file_uploader(
    "Choose a Persian audio file",
    type=["wav", "mp3", "m4a", "flac", "ogg"],
    key="audio_uploader",
    help="Wait until the file name appears below before clicking Start processing.",
)

if uploaded is not None:
    file_bytes = uploaded.getvalue()
    st.markdown(
        f"""
        <div class="psi-card">
          <h3>Selected file</h3>
          <p class="psi-summary-text">
            <strong>Name:</strong> {html.escape(uploaded.name)}<br/>
            <strong>Size:</strong> {len(file_bytes) / (1024 * 1024):.2f} MB
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.audio(file_bytes)

    if st.button("Start processing", type="primary", key="start_processing"):
        try:
            with st.spinner("Sending file to API…"):
                result = client.upload(
                    uploaded.name,
                    file_bytes,
                    uploaded.type,
                )
            rid = str(result.get("recording_id") or "")
            st.session_state["last_recording_id"] = rid
            st.session_state["last_upload_name"] = uploaded.name
            st.success("File queued for processing.")
            st.json(result)
            st.rerun()
        except APIError as exc:
            st.error(f"Upload failed: {exc.message}")
        except Exception as exc:
            st.error(f"Upload failed: {exc}")

st.markdown("### Processing status")
st.caption(
    "Recording ID is kept after you leave this page. "
    "If the file picker still says Uploading…, wait or re-select the file — "
    "do not switch sidebar pages mid-select."
)

default_id = str(st.session_state.get("last_recording_id") or "")
recording_id = st.text_input("Recording ID", value=default_id)

cols = st.columns([1, 1, 2])
refresh = cols[0].button("Refresh status", key="refresh_status")
auto = cols[1].checkbox("Auto-refresh", value=False, key="auto_refresh_status")

if recording_id and (refresh or auto):
    try:
        status = client.get_status(recording_id)
        st.write(status_badge(status.get("status", "")))
        st.progress(int(status.get("progress") or 0) / 100.0)
        st.write(f"Current step: {status.get('current_step') or '—'}")
        if status.get("error_message"):
            st.error(status["error_message"])
        state = (status.get("status") or "").lower()
        if state in {"pending", "processing"} and auto:
            time.sleep(1.5)
            st.rerun()
        elif state == "completed":
            st.success("Processing completed. Open Transcript / Speech analysis.")
        elif state == "failed":
            st.error("Processing failed. Check the error above or retry upload.")
    except APIError as exc:
        st.error(exc.message)
    except Exception as exc:
        st.error(str(exc))
