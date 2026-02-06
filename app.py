"""SAP AI Documentation Assistant — Streamlit UI."""

import html
from datetime import datetime, timezone

import streamlit as st

from api_client import APIError, ask_question, check_health, fetch_services
from config import (
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
    """Render pipeline orchestration details inside an expander."""
    with st.expander("Pipeline details", expanded=False):
        # Data masking
        masking = pipeline.get("data_masking")
        st.subheader("Data Masking", divider="blue")
        if masking:
            st.markdown(f"**Original query:** {html.escape(masking['original_query'])}")
            st.markdown(f"**Masked query:** {html.escape(masking['masked_query'])}")
            if masking.get("entities_masked"):
                st.markdown(f"**Entities masked:** {', '.join(masking['entities_masked'])}")
        else:
            st.caption("No PII detected — query sent unmasked.")

        # Content filtering
        filtering = pipeline.get("content_filtering")
        if filtering:
            st.subheader("Content Filtering", divider="blue")
            col_in, col_out = st.columns(2)
            for label, col, scores in [
                ("Input", col_in, filtering.get("input", {})),
                ("Output", col_out, filtering.get("output", {})),
            ]:
                with col:
                    passed = scores.get("passed", True)
                    status = "Passed" if passed else "Blocked"
                    st.markdown(f"**{label}:** {status}")
                    st.caption(
                        f"hate={scores.get('hate', 0)}  "
                        f"self_harm={scores.get('self_harm', 0)}  "
                        f"sexual={scores.get('sexual', 0)}  "
                        f"violence={scores.get('violence', 0)}"
                    )

        # LLM details
        llm = pipeline.get("llm")
        if llm:
            st.subheader("LLM", divider="blue")
            st.markdown(f"**Model:** `{html.escape(llm['model'])}`")
            st.markdown(
                f"**Tokens:** {llm['prompt_tokens']} prompt + "
                f"{llm['completion_tokens']} completion = "
                f"{llm['prompt_tokens'] + llm['completion_tokens']} total"
            )

        # Tool calls
        tool_calls = pipeline.get("tool_calls")
        if tool_calls:
            st.subheader("Tool Calls", divider="blue")
            for tc in tool_calls:
                st.markdown(f"**`{html.escape(tc['tool_name'])}`** — {tc['result_count']} results")
                st.json(tc["arguments"])
                if tc.get("results_preview"):
                    st.caption("Results preview:")
                    for preview in tc["results_preview"]:
                        st.caption(
                            f"  - {html.escape(str(preview.get('id', '')))} "
                            f"— {html.escape(str(preview.get('title', '')))}"
                        )

        # Messages to LLM
        messages = pipeline.get("messages_to_llm")
        if messages:
            st.subheader("Messages to LLM", divider="blue")
            for msg in messages:
                role = html.escape(msg["role"])
                content = html.escape(msg["content"])
                st.markdown(f"**{role}**")
                st.code(content, language=None)


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
