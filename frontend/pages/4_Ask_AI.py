"""Grounded Q&A chat interface."""

from __future__ import annotations

import html

import streamlit as st

from components.api_client import APIError, BackendClient
from components.ui import format_timestamp, inject_styles, page_header, render_sidebar

st.set_page_config(
    page_title="Ask AI | Persian Speech Intelligence",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_styles()
render_sidebar(active="Ask AI")
page_header(
    "Ask AI",
    "Answers are grounded only in evidence from the selected recording transcript.",
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
selected_label = st.selectbox("Select completed file", options=list(options.keys()) or ["—"])
recording_id = options.get(selected_label) if options else None
manual_id = st.text_input("Or paste recording ID", value=st.session_state.get("last_recording_id", ""))
recording_id = manual_id.strip() or recording_id

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

question = st.text_input(
    "Ask a question",
    placeholder="What was the main topic of this recording?",
)

if st.button("Send question", type="primary") and recording_id and question.strip():
    try:
        with st.spinner("Retrieving evidence and generating answer..."):
            answer = client.chat(recording_id, question.strip())
        st.session_state.chat_history.append(answer)
    except APIError as exc:
        st.error(exc.message)

for item in reversed(st.session_state.chat_history):
    st.markdown(
        f"""
        <div class="psi-card">
          <p class="psi-summary-text"><strong>Question:</strong> {html.escape(str(item.get('question') or ''))}</p>
          <p class="psi-summary-text"><strong>Answer:</strong> {html.escape(str(item.get('answer') or ''))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    grounded = "Grounded" if item.get("grounded") else "Refused / insufficient evidence"
    st.caption(f"Status: {grounded}")
    evidence = item.get("evidence") or []
    if evidence:
        st.markdown("**Evidence**")
        for ev in evidence:
            st.markdown(
                f'<div class="evidence-box">'
                f"{format_timestamp(ev.get('start_time'))} → "
                f"{format_timestamp(ev.get('end_time'))}<br/>"
                f"{html.escape(str(ev.get('text') or ''))}</div>",
                unsafe_allow_html=True,
            )
    st.divider()
