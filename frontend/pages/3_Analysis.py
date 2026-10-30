"""Speech analysis page — layout matched to docs/assets/psi-analysis-ui.jpg."""

from __future__ import annotations

import html
import json

import streamlit as st

from components.api_client import APIError, BackendClient
from components.ui import (
    entities_to_display_json,
    file_chip,
    inject_styles,
    page_header,
    render_json_panel,
    render_sentiment_card,
    render_sidebar,
    render_summary_card,
    render_topic_bars,
)

st.set_page_config(
    page_title="Speech analysis | Persian Speech Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_styles()
render_sidebar(active="Speech analysis")
page_header(
    "Analysis page",
    "Speech analysis results for your uploaded audio.",
)

client = BackendClient()

try:
    recordings = (client.list_recordings(limit=100).get("items") or [])
except Exception:
    recordings = []

completed = [r for r in recordings if r.get("processing_status") == "completed"]
options = {
    f"{r.get('original_filename')} ({str(r.get('id'))[:8]}…)": r for r in completed
}

col_sel, col_btn = st.columns([3, 1])
with col_sel:
    selected_label = st.selectbox(
        "Select completed file",
        options=list(options.keys()) or ["—"],
    )
with col_btn:
    st.write("")
    load = st.button("Load analysis", type="primary", use_container_width=True)

manual_id = st.text_input(
    "Or paste recording ID",
    value=st.session_state.get("last_recording_id", ""),
    placeholder="UUID",
)

recording_meta = options.get(selected_label) if options else None
recording_id = (manual_id.strip() or None) or (
    recording_meta.get("id") if recording_meta else None
)

if load and recording_id:
    try:
        analysis = client.get_analysis(recording_id)
        st.session_state["analysis_data"] = analysis
        st.session_state["analysis_meta"] = recording_meta or {"id": recording_id}
        if recording_meta is None:
            for r in completed:
                if str(r.get("id")) == str(recording_id):
                    st.session_state["analysis_meta"] = r
                    break
    except APIError as exc:
        st.error(exc.message)

analysis = st.session_state.get("analysis_data")
meta = st.session_state.get("analysis_meta") or {}

if not analysis:
    st.info("Select a completed file and click **Load analysis**.")
    st.stop()

filename = meta.get("original_filename") or "audio"
duration = meta.get("duration_seconds")
file_chip(str(filename), float(duration) if duration is not None else None)

left, right = st.columns([1.35, 1.0], gap="large")

with left:
    render_summary_card(str(analysis.get("short_summary") or ""))

    detailed = analysis.get("detailed_summary") or {}
    if isinstance(detailed, dict) and (
        detailed.get("main_discussion") or detailed.get("important_points")
    ):
        points = detailed.get("important_points") or []
        points_html = "".join(
            f"<li>{html.escape(str(p))}</li>" for p in points[:6]
        )
        main = html.escape(str(detailed.get("main_discussion") or ""))
        st.markdown(
            f"""
            <div class="psi-card">
              <h3>Detailed summary</h3>
              <p class="psi-summary-text"><strong>Main discussion:</strong> {main or "—"}</p>
              <ul class="psi-summary-text">{points_html or "<li>—</li>"}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    render_topic_bars(list(analysis.get("topics") or []))
    render_sentiment_card(analysis.get("sentiment") or {})

with right:
    payload = entities_to_display_json(analysis)
    render_json_panel(payload)
    st.download_button(
        "Download JSON",
        data=json.dumps(payload, ensure_ascii=False, indent=2),
        file_name=f"{recording_id or 'analysis'}_entities.json",
        mime="application/json",
        use_container_width=True,
    )

with st.expander("More details (actions, decisions, raw entities)", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Action items**")
        st.code(
            json.dumps(analysis.get("action_items") or [], ensure_ascii=False, indent=2),
            language="json",
        )
    with c2:
        st.write("**Decisions**")
        st.code(
            json.dumps(analysis.get("decisions") or [], ensure_ascii=False, indent=2),
            language="json",
        )
    st.write("**extracted_entities**")
    st.code(
        json.dumps(analysis.get("extracted_entities") or {}, ensure_ascii=False, indent=2),
        language="json",
    )
