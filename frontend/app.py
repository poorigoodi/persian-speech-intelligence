"""Persian Speech Intelligence — Dashboard (English UI)."""

from __future__ import annotations

import html

import streamlit as st

from components.api_client import APIError, BackendClient
from components.ui import inject_styles, page_header, render_sidebar, status_badge

st.set_page_config(
    page_title="Dashboard | Persian Speech Intelligence",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()
render_sidebar(active="Dashboard")
page_header(
    "Dashboard",
    "Overview of recordings, processing status, and shortcuts to speech analysis.",
)

client = BackendClient()

try:
    health = client.health()
    st.caption(f"Backend: {health.get('status', 'ok')}")
except Exception as exc:
    st.error(f"Backend unreachable: {exc}")

try:
    stats = client.stats()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total files", stats.get("total_recordings", 0))
    c2.metric("Completed", stats.get("completed", 0))
    c3.metric("Processing", stats.get("processing", 0))
    c4.metric("Queued", stats.get("pending", 0))
    c5.metric("Failed", stats.get("failed", 0))
except APIError as exc:
    st.warning(f"Stats unavailable: {exc.message}")
except Exception as exc:
    st.warning(f"Stats unavailable: {exc}")

st.markdown("### Recent recordings")
try:
    data = client.list_recordings(limit=20)
    items = data.get("items") or []
    if not items:
        st.info("No uploads yet. Start from **Upload audio**.")
    else:
        for item in items:
            name = html.escape(str(item.get("original_filename") or "—"))
            dur = (
                f"{item.get('duration_seconds'):.1f}s"
                if item.get("duration_seconds") is not None
                else "—"
            )
            rid = html.escape(str(item.get("id", ""))[:8])
            st.markdown(
                f"""
                <div class="psi-card" style="margin-bottom:0.55rem;padding:0.8rem 1rem">
                  <div style="display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap">
                    <strong>{name}</strong>
                    <span>{status_badge(item.get('processing_status', ''))}</span>
                  </div>
                  <div style="color:#64748b;font-size:0.85rem;margin-top:0.35rem">
                    Duration: {dur} · ID: {rid}…
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
except APIError as exc:
    st.error(exc.message)
except Exception as exc:
    st.error(str(exc))
