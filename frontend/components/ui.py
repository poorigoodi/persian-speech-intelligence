"""Shared Streamlit UI — English LTR layout matched to docs/assets/psi-analysis-ui.jpg."""

from __future__ import annotations

import html
import json
from typing import Any

import streamlit as st

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

:root {
  --psi-bg: #f1f5f9;
  --psi-surface: #ffffff;
  --psi-ink: #0f172a;
  --psi-muted: #64748b;
  --psi-teal: #14b8a6;
  --psi-teal-deep: #0d9488;
  --psi-teal-soft: #ccfbf1;
  --psi-border: #e2e8f0;
  --psi-pos: #22c55e;
  --psi-neg: #f43f5e;
  --psi-neu: #14b8a6;
  --psi-sidebar: #f8fafc;
}

/* Hide Streamlit's auto multipage nav (we use custom sidebar) */
[data-testid="stSidebarNav"] { display: none !important; }

html, body, [class*="css"], .stApp, .stMarkdown, label, p, span, div {
  font-family: 'DM Sans', system-ui, sans-serif !important;
}

.stApp { background: var(--psi-bg) !important; color: var(--psi-ink); }

/* Keep Streamlit toolbar from covering the custom topbar */
[data-testid="stHeader"] {
  background: transparent !important;
}

[data-testid="stSidebar"] {
  background: var(--psi-sidebar) !important;
  border-right: 1px solid var(--psi-border);
  min-width: 220px !important;
}

[data-testid="stSidebar"] > div:first-child {
  padding-top: 1rem;
}

.block-container {
  /* Streamlit chrome sits above content; 1.1rem was clipping the brand bar */
  padding-top: 3.5rem !important;
  padding-bottom: 2rem !important;
  max-width: 1180px;
}

/* --- Top bar --- */
.psi-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin: 0 0 1.35rem 0;
  padding: 0.2rem 0 0.9rem;
  border-bottom: 1px solid var(--psi-border);
}

.psi-brand {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  font-weight: 700;
  font-size: 1.08rem;
  color: var(--psi-ink);
  letter-spacing: -0.02em;
}

.psi-brand .wave {
  width: 28px; height: 28px;
  border-radius: 8px;
  background: var(--psi-teal-soft);
  color: var(--psi-teal-deep);
  display: grid; place-items: center;
  font-size: 0.95rem;
}

.psi-brand .pipe { color: #cbd5e1; font-weight: 400; }
.psi-brand .fa-sub { color: var(--psi-teal-deep); font-weight: 600; font-size: 0.95rem; }

.psi-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  background: var(--psi-teal);
  color: #fff; display: grid; place-items: center;
  font-weight: 700; font-size: 0.85rem;
}

/* --- Page header --- */
.psi-page-title {
  margin: 0 0 0.2rem 0;
  font-size: 1.65rem;
  font-weight: 700;
  color: var(--psi-ink);
  letter-spacing: -0.03em;
}

.psi-page-sub {
  margin: 0 0 1.05rem 0;
  color: var(--psi-muted);
  font-size: 0.95rem;
}

/* --- File chip --- */
.psi-file-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--psi-surface);
  border: 1px solid var(--psi-border);
  border-radius: 999px;
  padding: 0.4rem 0.95rem;
  font-size: 0.86rem;
  color: var(--psi-ink);
  margin-bottom: 1.1rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.psi-file-chip .dur {
  color: var(--psi-teal-deep);
  font-weight: 600;
  margin-left: 0.25rem;
  padding-left: 0.65rem;
  border-left: 1px solid var(--psi-border);
}

/* --- Cards --- */
.psi-card {
  background: var(--psi-surface);
  border: 1px solid var(--psi-border);
  border-radius: 16px;
  padding: 1.1rem 1.2rem;
  margin-bottom: 0.95rem;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
}

.psi-card h3 {
  margin: 0 0 0.75rem 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--psi-ink);
  letter-spacing: -0.01em;
}

.psi-summary-text {
  line-height: 1.7;
  color: #334155;
  font-size: 0.94rem;
  margin: 0;
}

/* --- Topics --- */
.psi-topic-row { margin-bottom: 0.85rem; }
.psi-topic-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.35rem;
  font-size: 0.9rem;
}
.psi-topic-head .name { color: var(--psi-ink); font-weight: 500; }
.psi-topic-head .pct {
  color: var(--psi-teal-deep);
  font-weight: 700;
  font-size: 0.82rem;
  background: var(--psi-teal-soft);
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
}
.psi-bar {
  height: 9px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}
.psi-bar > i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--psi-teal-deep), var(--psi-teal));
  border-radius: 999px;
}

/* --- Sentiment --- */
.psi-sent-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: var(--psi-teal-soft);
  color: var(--psi-teal-deep);
  border-radius: 999px;
  padding: 0.28rem 0.85rem;
  font-weight: 700;
  font-size: 0.88rem;
  margin-bottom: 0.85rem;
}

.psi-sent-row {
  display: grid;
  grid-template-columns: 4.2rem 1fr 2.6rem;
  gap: 0.55rem;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.86rem;
}
.psi-sent-row .label { color: var(--psi-muted); }
.psi-sent-row .val { color: var(--psi-ink); font-weight: 600; text-align: right; }

.psi-sent-track {
  height: 9px; background: #e2e8f0; border-radius: 999px; overflow: hidden;
}
.psi-sent-track > i { display: block; height: 100%; border-radius: 999px; }
.psi-sent-track .pos { background: var(--psi-pos); }
.psi-sent-track .neu { background: var(--psi-neu); }
.psi-sent-track .neg { background: var(--psi-neg); }

/* --- JSON panel --- */
.psi-json-panel {
  background: #0b1220;
  color: #e2e8f0;
  border-radius: 16px;
  padding: 1rem 1.05rem 1.1rem;
  border: 1px solid #1e293b;
  min-height: 440px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);
}
.psi-json-panel h3 {
  margin: 0 0 0.75rem 0;
  font-size: 0.92rem;
  color: #f8fafc;
  font-weight: 700;
}
.psi-json-panel pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.76rem;
  line-height: 1.55;
  color: #67e8f9;
  max-height: 540px;
  overflow: auto;
}

/* --- Sidebar nav buttons look --- */
.psi-side-brand {
  font-weight: 700;
  font-size: 1rem;
  color: var(--psi-ink);
  margin: 0 0 0.15rem 0;
}
.psi-side-cap {
  color: var(--psi-muted);
  font-size: 0.78rem;
  margin: 0 0 1rem 0;
}

.segment-row {
  background: var(--psi-surface);
  border: 1px solid var(--psi-border);
  border-left: 4px solid var(--psi-teal);
  padding: 0.65rem 0.85rem;
  margin-bottom: 0.45rem;
  border-radius: 10px;
}

.evidence-box {
  background: var(--psi-teal-soft);
  border: 1px solid #99f6e4;
  border-radius: 10px;
  padding: 0.75rem;
  margin-top: 0.5rem;
}

div.stButton > button[kind="primary"] {
  background: var(--psi-teal-deep) !important;
  border-color: var(--psi-teal-deep) !important;
  color: white !important;
}
div.stButton > button[kind="primary"]:hover {
  background: #0f766e !important;
  border-color: #0f766e !important;
}

/* Soften default file uploader */
[data-testid="stFileUploader"] section {
  border: 1.5px dashed #cbd5e1 !important;
  border-radius: 14px !important;
  background: #fff !important;
}
</style>
"""


def inject_styles() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_topbar() -> None:
    st.markdown(
        """
        <div class="psi-topbar">
          <div class="psi-brand">
            <span class="wave">〰</span>
            <span>Persian Speech Intelligence</span>
            <span class="pipe">|</span>
            <span class="fa-sub">Speech AI</span>
          </div>
          <div class="psi-avatar">P</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(active: str = "Dashboard") -> None:
    """Custom English nav only (default Streamlit page list is CSS-hidden)."""
    with st.sidebar:
        st.markdown(
            '<p class="psi-side-brand">Speech AI</p>'
            '<p class="psi-side-cap">Persian Speech Intelligence</p>',
            unsafe_allow_html=True,
        )
        st.page_link("app.py", label="Dashboard", icon="🏠")
        st.page_link("pages/1_Upload.py", label="Upload audio", icon="🎤")
        st.page_link("pages/2_Transcript.py", label="Transcript", icon="📝")
        st.page_link("pages/3_Analysis.py", label="Speech analysis", icon="📊")
        st.page_link("pages/4_Ask_AI.py", label="Ask AI", icon="💬")
        st.page_link("pages/5_Export.py", label="Export & settings", icon="⚙️")
        st.divider()
        st.caption(f"Active: {active}")


def page_header(title: str, subtitle: str = "") -> None:
    render_topbar()
    sub = f'<p class="psi-page-sub">{html.escape(subtitle)}</p>' if subtitle else ""
    st.markdown(
        f'<h1 class="psi-page-title">{html.escape(title)}</h1>{sub}',
        unsafe_allow_html=True,
    )


def format_timestamp(seconds: float | None) -> str:
    if seconds is None:
        return "--:--"
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def status_badge(status: str) -> str:
    colors = {
        "pending": "🟡",
        "processing": "🔵",
        "completed": "🟢",
        "failed": "🔴",
    }
    return f"{colors.get(status, '⚪')} {status}"


def file_chip(filename: str, duration_seconds: float | None = None) -> None:
    name = html.escape((filename or "audio")[:48])
    dur = format_timestamp(duration_seconds) if duration_seconds is not None else "—:— "
    st.markdown(
        f"""
        <div class="psi-file-chip">
          <span>📄</span>
          <span>{name}</span>
          <span class="dur">⏱ {dur}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _topic_percents(topics: list[Any]) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    raw: list[tuple[str, float]] = []
    for t in topics:
        if isinstance(t, dict):
            name = str(t.get("name") or "Topic")
            rel = t.get("relevance")
            try:
                score = float(rel) if rel is not None else 0.0
            except (TypeError, ValueError):
                score = 0.0
            raw.append((name, score))
        else:
            raw.append((str(t), 0.0))
    if not raw:
        return []
    if any(s > 0 for _, s in raw):
        vals = [s if s > 1 else s * 100 for _, s in raw]
        total = sum(vals) or 1.0
        for (name, _), v in zip(raw, vals):
            rows.append((name, 100.0 * v / total))
    else:
        n = len(raw)
        weights = [max(12.0, 48.0 - i * (28.0 / max(n, 1))) for i in range(n)]
        total = sum(weights)
        for (name, _), w in zip(raw, weights):
            rows.append((name, 100.0 * w / total))
    return rows


def render_topic_bars(topics: list[Any]) -> None:
    items = _topic_percents(topics)
    if not items:
        st.markdown(
            '<div class="psi-card"><h3>Key topics</h3>'
            '<p class="psi-summary-text">No topics extracted.</p></div>',
            unsafe_allow_html=True,
        )
        return
    parts = ['<div class="psi-card"><h3>Key topics</h3>']
    for name, pct in items:
        parts.append(
            f"""
            <div class="psi-topic-row">
              <div class="psi-topic-head">
                <span class="name">{html.escape(name)}</span>
                <span class="pct">{pct:.0f}%</span>
              </div>
              <div class="psi-bar"><i style="width:{min(100.0, pct):.1f}%"></i></div>
            </div>
            """
        )
    parts.append("</div>")
    st.markdown("\n".join(parts), unsafe_allow_html=True)


def _sentiment_distribution(label: str) -> dict[str, float]:
    key = (label or "Uncertain").strip()
    if key == "Positive":
        return {"pos": 62.0, "neu": 28.0, "neg": 10.0}
    if key == "Negative":
        return {"pos": 10.0, "neu": 28.0, "neg": 62.0}
    if key == "Mixed":
        return {"pos": 38.0, "neu": 24.0, "neg": 38.0}
    if key == "Neutral":
        return {"pos": 23.0, "neu": 54.0, "neg": 23.0}
    return {"pos": 20.0, "neu": 60.0, "neg": 20.0}


def render_sentiment_card(sentiment: Any) -> None:
    if not isinstance(sentiment, dict):
        sentiment = {}
    label = str(sentiment.get("label") or "Uncertain")
    expl = html.escape(str(sentiment.get("explanation") or ""))
    dist = _sentiment_distribution(label)
    st.markdown(
        f"""
        <div class="psi-card">
          <h3>Sentiment</h3>
          <div class="psi-sent-badge">{html.escape(label)}</div>
          <p class="psi-summary-text" style="margin-bottom:0.9rem">{expl or "—"}</p>
          <div class="psi-sent-row">
            <span class="label">Positive</span>
            <div class="psi-sent-track"><i class="pos" style="width:{dist['pos']}%"></i></div>
            <span class="val">{dist['pos']:.0f}%</span>
          </div>
          <div class="psi-sent-row">
            <span class="label">Neutral</span>
            <div class="psi-sent-track"><i class="neu" style="width:{dist['neu']}%"></i></div>
            <span class="val">{dist['neu']:.0f}%</span>
          </div>
          <div class="psi-sent-row">
            <span class="label">Negative</span>
            <div class="psi-sent-track"><i class="neg" style="width:{dist['neg']}%"></i></div>
            <span class="val">{dist['neg']:.0f}%</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def entities_to_display_json(analysis: dict[str, Any]) -> dict[str, Any]:
    ents = analysis.get("extracted_entities") or {}
    if not isinstance(ents, dict):
        ents = {}
    entities: list[dict[str, str]] = []
    for person in ents.get("people") or []:
        entities.append({"type": "PERSON", "text": str(person)})
    for org in ents.get("organizations") or []:
        entities.append({"type": "ORG", "text": str(org)})
    for date in ents.get("dates") or []:
        entities.append({"type": "DATE", "text": str(date)})
    for loc in ents.get("locations") or []:
        entities.append({"type": "LOCATION", "text": str(loc)})
    for kw in (ents.get("keywords") or [])[:8]:
        entities.append({"type": "KEYWORD", "text": str(kw)})
    for task in ents.get("tasks") or []:
        if isinstance(task, dict):
            entities.append({"type": "TASK", "text": str(task.get("description") or task)})
        else:
            entities.append({"type": "TASK", "text": str(task)})

    sentiment = analysis.get("sentiment") or {}
    return {
        "entities": entities,
        "language": "fa",
        "short_summary": analysis.get("short_summary") or "",
        "topics": [
            t.get("name") if isinstance(t, dict) else t
            for t in (analysis.get("topics") or [])
        ],
        "sentiment": {
            "label": sentiment.get("label") if isinstance(sentiment, dict) else sentiment,
            "explanation": (
                sentiment.get("explanation") if isinstance(sentiment, dict) else ""
            ),
        },
        "action_items": analysis.get("action_items") or [],
        "decisions": analysis.get("decisions") or [],
    }


def render_json_panel(
    payload: dict[str, Any], title: str = "Identified entities (JSON)"
) -> None:
    body = html.escape(json.dumps(payload, ensure_ascii=False, indent=2))
    st.markdown(
        f"""
        <div class="psi-json-panel">
          <h3>&lt;/&gt; {html.escape(title)}</h3>
          <pre>{body}</pre>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary_card(text: str) -> None:
    content = html.escape(text or "No summary available yet.")
    st.markdown(
        f"""
        <div class="psi-card">
          <h3>Short summary</h3>
          <p class="psi-summary-text">{content}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
