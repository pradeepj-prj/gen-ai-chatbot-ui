"""SAP AI Documentation Assistant — Streamlit UI."""

import html
import re
from datetime import datetime, timezone

import streamlit as st

from api_client import APIError, ask_question, check_health, fetch_services
from config import (
    CLIENT_SIDE_ENTITIES,
    DEFAULT_SERVICE_COLOR,
    MAX_QUESTION_LENGTH,
    SERVICE_COLORS,
    SERVICE_DISPLAY,
    SUGGESTED_QUESTIONS,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SAP AI Documentation Assistant",
    page_icon=":material/smart_toy:",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .service-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        color: #FFFFFF;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 4px;
    }
    .confidence-high   { color: #188918; font-weight: 600; }
    .confidence-medium { color: #E78C07; font-weight: 600; }
    .confidence-low    { color: #BB0000; font-weight: 600; }
    .answer-text {
        white-space: pre-wrap;
        line-height: 1.6;
        font-size: 0.95rem;
    }
    div[data-testid="stHorizontalBlock"] button {
        white-space: normal;
        text-align: left;
    }

    /* ── Pipeline dashboard ─────────────────────── */
    .pipeline-card {
        background: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 10px;
        padding: 1.1rem 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .pipeline-card-header {
        font-size: 1.05rem;
        font-weight: 700;
        border-left: 4px solid #0070F2;
        padding-left: 0.6rem;
        margin-bottom: 0.75rem;
        color: #1A1A1A;
    }
    .score-badge {
        display: inline-block;
        text-align: center;
        padding: 0.4rem 0.9rem;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 700;
        margin: 0.2rem 0.15rem;
        min-width: 80px;
    }
    .score-safe    { background: #DFF6DD; color: #1E7D1E; }
    .score-caution { background: #FFF4CE; color: #9A6700; }
    .score-danger  { background: #FFE0E0; color: #C41E3A; }
    .filter-status-passed {
        display: inline-block;
        padding: 2px 12px;
        border-radius: 12px;
        background: #DFF6DD;
        color: #1E7D1E;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .filter-status-blocked {
        display: inline-block;
        padding: 2px 12px;
        border-radius: 12px;
        background: #FFE0E0;
        color: #C41E3A;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .model-chip {
        display: inline-block;
        padding: 3px 14px;
        border-radius: 14px;
        background: #E8F0FE;
        color: #0070F2;
        font-weight: 600;
        font-size: 0.88rem;
    }
    .masking-field {
        background: #F8F9FA;
        border-left: 3px solid #0070F2;
        padding: 0.55rem 0.8rem;
        margin: 0.4rem 0;
        border-radius: 0 6px 6px 0;
        font-size: 0.9rem;
    }
    .masking-field-label {
        font-weight: 600;
        color: #555;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    .masked-token {
        display: inline;
        background: #FFF0F0;
        border: 1px solid #E8A0A0;
        border-radius: 4px;
        padding: 1px 7px;
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 0.84rem;
        font-weight: 600;
        color: #C41E3A;
        letter-spacing: 0.2px;
    }
    .entity-badge {
        display: inline-block;
        padding: 1px 8px;
        border-radius: 10px;
        background: #E8F0FE;
        color: #0070F2;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 4px;
    }
    .entity-badge-custom {
        display: inline-block;
        padding: 1px 8px;
        border-radius: 10px;
        background: #FFF4CE;
        color: #9A6700;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 4px;
    }
    .masked-token-custom {
        display: inline;
        background: #FFF4CE;
        border: 1px solid #D4A843;
        border-radius: 4px;
        padding: 1px 7px;
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 0.84rem;
        font-weight: 600;
        color: #9A6700;
        letter-spacing: 0.2px;
    }
    .tool-call-name {
        font-weight: 700;
        color: #0070F2;
        font-size: 0.95rem;
    }
    .tool-call-count {
        display: inline-block;
        padding: 1px 10px;
        border-radius: 10px;
        background: #E8F0FE;
        color: #0070F2;
        font-size: 0.78rem;
        font-weight: 600;
        margin-left: 6px;
    }
    .role-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        color: #FFFFFF;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .role-system    { background: #0070F2; }
    .role-user      { background: #8B5CF6; }
    .role-assistant { background: #188918; }
    .role-tool      { background: #E78C07; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []
if "show_pipeline" not in st.session_state:
    st.session_state.show_pipeline = False


# ---------------------------------------------------------------------------
# Helper functions (all defined before any UI rendering that uses them)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def _cached_services() -> dict[str, str]:
    """Fetch service display-name map from API, falling back to config."""
    try:
        services = fetch_services()
        return {s["key"]: s["display_name"] for s in services}
    except APIError:
        return dict(SERVICE_DISPLAY)


def _service_name(key: str) -> str:
    names = _cached_services()
    return names.get(key, SERVICE_DISPLAY.get(key, key))


def _service_color(key: str) -> str:
    return SERVICE_COLORS.get(key, DEFAULT_SERVICE_COLOR)


def _confidence_label(score: float) -> str:
    pct = f"{score:.0%}"
    if score >= 0.75:
        return f'<span class="confidence-high">{pct}</span>'
    if score >= 0.45:
        return f'<span class="confidence-medium">{pct}</span>'
    return f'<span class="confidence-low">{pct}</span>'


def _score_severity_class(score: float) -> str:
    """Return CSS class based on content-filter score severity."""
    if score < 0.3:
        return "score-safe"
    if score < 0.6:
        return "score-caution"
    return "score-danger"


def _role_css_class(role: str) -> str:
    """Return CSS class for a message role."""
    return f"role-{role}" if role in ("system", "user", "assistant", "tool") else "role-system"


def _export_markdown(history: list[dict]) -> str:
    """Export session history as a Markdown document."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# SAP AI Documentation Assistant — Session Export",
        f"Exported: {now}  ",
        f"Questions: {len(history)}",
        "",
    ]
    for i, entry in enumerate(history, 1):
        lines.append(f"---\n## Q{i}: {entry['question']}\n")
        if entry.get("error"):
            lines.append(f"**Error:** {entry['error']}\n")
            continue
        data = entry["response"]
        if data.get("services"):
            names = ", ".join(_service_name(s) for s in data["services"])
            lines.append(f"**Services:** {names}  ")
        lines.append(f"**Confidence:** {data['confidence']:.0%}  \n")
        lines.append(data["answer"])
        lines.append("")
        if data.get("links"):
            lines.append("**Links:**")
            for lnk in data["links"]:
                lines.append(f"- [{lnk['title']}]({lnk['url']}) — {lnk['description']}")
            lines.append("")
    return "\n".join(lines)


def _handle_question(question: str) -> None:
    """Send *question* to the API and append the result to history."""
    if len(question) > MAX_QUESTION_LENGTH:
        st.warning(f"Question is too long (max {MAX_QUESTION_LENGTH} characters). Please shorten it.")
        return
    with st.spinner("Searching SAP AI documentation..."):
        try:
            response = ask_question(question, st.session_state.show_pipeline)
            st.session_state.history.append(
                {"question": question, "response": response, "error": None}
            )
        except APIError as exc:
            st.session_state.history.append(
                {"question": question, "response": None, "error": str(exc)}
            )


def _render_pipeline(pipeline: dict, index: int) -> None:
    """Render pipeline orchestration details as a visual dashboard."""
    with st.expander("Pipeline details", expanded=False):

        # ── Data Masking ──────────────────────────────────────────
        masking = pipeline.get("data_masking")
        if masking:
            entities_html = ""
            if masking.get("entities_masked"):
                sap_entities = [e for e in masking["entities_masked"] if e not in CLIENT_SIDE_ENTITIES]
                custom_entities = [e for e in masking["entities_masked"] if e in CLIENT_SIDE_ENTITIES]
                parts = []
                if sap_entities:
                    sap_badges = "".join(
                        f'<span class="entity-badge">{html.escape(e)}</span>'
                        for e in sap_entities
                    )
                    parts.append(
                        f'<div style="margin-top:0.5rem">'
                        f'<span class="masking-field-label">Entities masked</span><br>{sap_badges}'
                        f'</div>'
                    )
                if custom_entities:
                    custom_badges = "".join(
                        f'<span class="entity-badge-custom">{html.escape(e)}</span>'
                        for e in custom_entities
                    )
                    parts.append(
                        f'<div style="margin-top:0.5rem">'
                        f'<span class="masking-field-label">Custom filters</span><br>{custom_badges}'
                        f'</div>'
                    )
                entities_html = "".join(parts)
            # Escape first, then highlight MASKED_* tokens
            masked_query_safe = html.escape(masking["masked_query"])
            # Client-side tokens (e.g. MASKED_NRIC) get amber styling
            custom_token_pattern = "|".join(f"MASKED_{e}" for e in CLIENT_SIDE_ENTITIES)
            masked_query_safe = re.sub(
                rf"({custom_token_pattern})",
                r'<span class="masked-token-custom">\1</span>',
                masked_query_safe,
            )
            # Remaining MASKED_* tokens get red SAP DPI styling (skip already-wrapped ones)
            masked_query_safe = re.sub(
                r'(?<!">)(MASKED_\w+)',
                r'<span class="masked-token">\1</span>',
                masked_query_safe,
            )
            st.markdown(
                f'<div class="pipeline-card">'
                f'<div class="pipeline-card-header">Data Masking</div>'
                f'<div class="masking-field">'
                f'<span class="masking-field-label">Original query</span><br>'
                f'{html.escape(masking["original_query"])}'
                f'</div>'
                f'<div class="masking-field">'
                f'<span class="masking-field-label">Masked query</span><br>'
                f'{masked_query_safe}'
                f'</div>'
                f'{entities_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="pipeline-card">'
                '<div class="pipeline-card-header">Data Masking</div>'
                '<em style="color:#888">No PII detected — query sent unmasked.</em>'
                '</div>',
                unsafe_allow_html=True,
            )

        # ── Content Filtering ─────────────────────────────────────
        filtering = pipeline.get("content_filtering")
        if filtering:
            col_in, col_out = st.columns(2)
            categories = ["hate", "self_harm", "sexual", "violence"]
            category_labels = {"hate": "Hate", "self_harm": "Self-harm", "sexual": "Sexual", "violence": "Violence"}
            for label, col, scores in [
                ("Input", col_in, filtering.get("input", {})),
                ("Output", col_out, filtering.get("output", {})),
            ]:
                with col:
                    with st.container(border=True):
                        passed = scores.get("passed", True)
                        status_cls = "filter-status-passed" if passed else "filter-status-blocked"
                        status_text = "Passed" if passed else "Blocked"
                        st.markdown(
                            f'<div class="pipeline-card-header">'
                            f'Content Filtering — {label} '
                            f'<span class="{status_cls}">{status_text}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        badge_html = ""
                        for cat in categories:
                            score = scores.get(cat, 0)
                            sev = _score_severity_class(score)
                            cat_label = html.escape(category_labels[cat])
                            badge_html += (
                                f'<span class="score-badge {sev}">'
                                f'{cat_label}<br>{score:.2f}'
                                f'</span> '
                            )
                        st.markdown(badge_html, unsafe_allow_html=True)

        # ── LLM / Tokens ─────────────────────────────────────────
        llm = pipeline.get("llm")
        if llm:
            with st.container(border=True):
                st.markdown(
                    f'<div class="pipeline-card-header">'
                    f'LLM <span class="model-chip">{html.escape(llm["model"])}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                prompt_tok = llm["prompt_tokens"]
                completion_tok = llm["completion_tokens"]
                total_tok = prompt_tok + completion_tok
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("Prompt", f"{prompt_tok:,}")
                mc2.metric("Completion", f"{completion_tok:,}")
                mc3.metric("Total", f"{total_tok:,}")

        # ── Tool Calls ────────────────────────────────────────────
        tool_calls = pipeline.get("tool_calls")
        if tool_calls:
            for tc_idx, tc in enumerate(tool_calls):
                with st.container(border=True):
                    st.markdown(
                        f'<span class="tool-call-name">{html.escape(tc["tool_name"])}</span>'
                        f'<span class="tool-call-count">{tc["result_count"]} results</span>',
                        unsafe_allow_html=True,
                    )
                    st.json(tc["arguments"], expanded=False)
                    if tc.get("results_preview"):
                        st.caption("Results preview:")
                        for preview in tc["results_preview"]:
                            st.caption(
                                f"  - {html.escape(str(preview.get('id', '')))} "
                                f"— {html.escape(str(preview.get('title', '')))}"
                            )

        # ── Messages to LLM ──────────────────────────────────────
        messages = pipeline.get("messages_to_llm")
        if messages:
            for msg_idx, msg in enumerate(messages):
                with st.container(border=True):
                    role = msg["role"]
                    role_cls = _role_css_class(role)
                    st.markdown(
                        f'<span class="role-badge {role_cls}">{html.escape(role)}</span>',
                        unsafe_allow_html=True,
                    )
                    st.code(msg["content"], language=None)


def _render_answer_card(entry: dict, index: int) -> None:
    """Render a single Q&A card."""
    with st.container(border=True):
        st.markdown(f"**Q:** {html.escape(entry['question'])}")

        # Error case
        if entry.get("error"):
            st.error(entry["error"])
            return

        data = entry["response"]

        # Service badges
        if data.get("services"):
            badges = ""
            for svc in data["services"]:
                color = _service_color(svc)
                name = html.escape(_service_name(svc))
                badges += f'<span class="service-badge" style="background:{color}">{name}</span>'
            st.markdown(badges, unsafe_allow_html=True)

        # Confidence
        st.markdown(
            f"**Confidence:** {_confidence_label(data['confidence'])}",
            unsafe_allow_html=True,
        )

        # Special cases: content filtered / non-SAP
        if not data["is_sap_ai"] and data["confidence"] == 0.0:
            st.warning(data["answer"])
        elif not data["is_sap_ai"]:
            st.info(data["answer"])
        else:
            st.markdown(
                f'<div class="answer-text">{html.escape(data["answer"])}</div>',
                unsafe_allow_html=True,
            )

        # Links
        if data.get("links"):
            st.markdown("**Relevant documentation:**")
            for lnk in data["links"]:
                title = html.escape(lnk["title"])
                desc = html.escape(lnk["description"])
                st.markdown(f"- [{title}]({lnk['url']}) — {desc}")

        # Pipeline details
        if data.get("pipeline"):
            _render_pipeline(data["pipeline"], index)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")

    st.session_state.show_pipeline = st.toggle(
        "Show pipeline details",
        value=st.session_state.show_pipeline,
        help="Include orchestration details (data masking, content filtering, LLM stats, tool calls) in the response.",
        key="pipeline_toggle",
    )

    st.divider()

    if st.button("New Session", use_container_width=True, key="new_session"):
        st.session_state.history = []
        st.rerun()

    if st.session_state.history:
        md_export = _export_markdown(st.session_state.history)
        fname = datetime.now().strftime("sap_ai_assistant_%Y%m%d_%H%M%S.md")
        st.download_button(
            "Download Results",
            data=md_export,
            file_name=fname,
            mime="text/markdown",
            use_container_width=True,
            key="download_btn",
        )

    st.divider()

    # API health
    try:
        health = check_health()
        st.success(f"API: {health.get('status', 'ok')} (v{health.get('version', '?')})")
    except APIError as exc:
        st.error(f"API offline — {exc}")


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("SAP AI Documentation Assistant")
st.caption("Ask questions about SAP AI services — powered by GPT-4o with tool calling")

if not st.session_state.history:
    st.markdown("### Try one of these questions to get started:")
    cols = st.columns(len(SUGGESTED_QUESTIONS))
    for col_idx, q in enumerate(SUGGESTED_QUESTIONS):
        with cols[col_idx]:
            if st.button(q, key=f"suggested_{col_idx}", use_container_width=True):
                _handle_question(q)
                st.rerun()
else:
    for idx, entry in enumerate(st.session_state.history):
        _render_answer_card(entry, idx)

# ---------------------------------------------------------------------------
# Chat input (always rendered at top level)
# ---------------------------------------------------------------------------
user_input = st.chat_input("Ask a question about SAP AI services...")
if user_input:
    _handle_question(user_input.strip())
    st.rerun()
