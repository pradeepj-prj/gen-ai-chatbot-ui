"""Knowledge Base Management — browse, add, edit, and delete documentation entries."""

import html
from collections import defaultdict

import streamlit as st

from api_client import (
    APIError,
    create_kb_entry,
    delete_kb_entry,
    fetch_kb_entries,
    fetch_services,
    update_kb_entry,
)
from config import DEFAULT_SERVICE_COLOR, SERVICE_COLORS, SERVICE_DISPLAY

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Knowledge Base — SAP AI Docs",
    page_icon=":material/menu_book:",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Minimal CSS — reuse service-badge from app.py, add tag pills
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
    .tag-pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 10px;
        background: #F0F2F5;
        color: #555;
        font-size: 0.75rem;
        font-weight: 500;
        margin-right: 4px;
        margin-bottom: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def _cached_entries(service: str | None = None) -> list[dict]:
    return fetch_kb_entries(service)


@st.cache_data(ttl=300)
def _cached_services() -> list[dict]:
    return fetch_services()


def _service_display_name(key: str, services_map: dict[str, str]) -> str:
    return services_map.get(key, SERVICE_DISPLAY.get(key, key))


def _service_color(key: str) -> str:
    return SERVICE_COLORS.get(key, DEFAULT_SERVICE_COLOR)


def _clear_and_rerun():
    """Clear entry cache and rerun so the page reflects mutations."""
    st.cache_data.clear()
    st.rerun()


# ---------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------
@st.dialog("Add New Entry")
def _add_entry_dialog(services_map: dict[str, str]):
    service_keys = list(services_map.keys())
    service_labels = [services_map[k] for k in service_keys]

    svc_label = st.selectbox("Service", service_labels)
    svc_key = service_keys[service_labels.index(svc_label)]
    title = st.text_input("Title")
    url = st.text_input("URL")
    description = st.text_area("Description")
    tags_raw = st.text_input("Tags (comma-separated)")

    if st.button("Create", type="primary", use_container_width=True):
        if not title.strip():
            st.error("Title is required.")
            return
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        entry = {
            "service_key": svc_key,
            "title": title.strip(),
            "url": url.strip(),
            "description": description.strip(),
            "tags": tags,
        }
        try:
            create_kb_entry(entry)
            st.success("Entry created!")
            _clear_and_rerun()
        except APIError as exc:
            st.error(str(exc))


@st.dialog("Edit Entry")
def _edit_entry_dialog(entry: dict, services_map: dict[str, str]):
    title = st.text_input("Title", value=entry.get("title", ""))
    url = st.text_input("URL", value=entry.get("url", ""))
    description = st.text_area("Description", value=entry.get("description", ""))
    tags_raw = st.text_input(
        "Tags (comma-separated)",
        value=", ".join(entry.get("tags", [])),
    )

    if st.button("Save Changes", type="primary", use_container_width=True):
        if not title.strip():
            st.error("Title is required.")
            return
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        updates = {}
        if title.strip() != entry.get("title", ""):
            updates["title"] = title.strip()
        if url.strip() != entry.get("url", ""):
            updates["url"] = url.strip()
        if description.strip() != entry.get("description", ""):
            updates["description"] = description.strip()
        if tags != entry.get("tags", []):
            updates["tags"] = tags

        if not updates:
            st.info("No changes detected.")
            return
        try:
            update_kb_entry(entry["id"], updates)
            st.success("Entry updated!")
            _clear_and_rerun()
        except APIError as exc:
            st.error(str(exc))


@st.dialog("Confirm Delete")
def _delete_entry_dialog(entry: dict):
    st.warning(
        f"Are you sure you want to delete **{html.escape(entry.get('title', ''))}**? "
        "This action cannot be undone."
    )
    col_cancel, col_confirm = st.columns(2)
    with col_cancel:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with col_confirm:
        if st.button("Delete", type="primary", use_container_width=True):
            try:
                delete_kb_entry(entry["id"])
                st.success("Entry deleted!")
                _clear_and_rerun()
            except APIError as exc:
                st.error(str(exc))


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
try:
    services = _cached_services()
    services_map: dict[str, str] = {s["key"]: s["display_name"] for s in services}
except APIError as exc:
    st.error(f"Failed to load services: {exc}")
    services = []
    services_map = dict(SERVICE_DISPLAY)

# ---------------------------------------------------------------------------
# Sidebar — filter & stats
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Filters")

    filter_options = ["All Services"] + [
        _service_display_name(s["key"], services_map) for s in services
    ]
    selected_label = st.selectbox("Filter by service", filter_options, key="kb_service_filter")

    selected_service: str | None = None
    if selected_label != "All Services":
        # Reverse-lookup the key
        for s in services:
            if s["display_name"] == selected_label:
                selected_service = s["key"]
                break

    st.divider()

# Fetch entries (filtered or all)
try:
    entries = _cached_entries(selected_service)
except APIError as exc:
    st.error(f"Failed to load entries: {exc}")
    entries = []

# Sidebar stats
with st.sidebar:
    st.markdown("**Stats**")
    st.markdown(f"- {len(services)} services")
    st.markdown(f"- {len(entries)} entries" + (" (filtered)" if selected_service else ""))

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("Knowledge Base Management")
st.caption("Browse and manage documentation entries across SAP AI services")

# Add new entry button
if st.button("+ Add New Entry", type="primary"):
    _add_entry_dialog(services_map)

# Group entries by service
grouped: dict[str, list[dict]] = defaultdict(list)
for entry in entries:
    grouped[entry.get("service_key", "unknown")].append(entry)

if not entries:
    st.info("No entries found." + (" Try selecting a different service." if selected_service else ""))
else:
    for svc_key in sorted(grouped, key=lambda k: _service_display_name(k, services_map)):
        svc_entries = grouped[svc_key]
        display_name = _service_display_name(svc_key, services_map)
        color = _service_color(svc_key)

        st.subheader(f"{display_name} ({len(svc_entries)} entries)")

        for entry in svc_entries:
            with st.container(border=True):
                # Title row
                st.markdown(f"**{html.escape(entry.get('title', 'Untitled'))}**")

                # Description
                desc = entry.get("description", "")
                if desc:
                    st.caption(html.escape(desc))

                # URL
                url = entry.get("url", "")
                if url:
                    st.markdown(f"[{html.escape(url)}]({url})")

                # Tags
                tags = entry.get("tags", [])
                if tags:
                    tag_html = "".join(
                        f'<span class="tag-pill">{html.escape(t)}</span>' for t in tags
                    )
                    st.markdown(tag_html, unsafe_allow_html=True)

                # Action buttons
                col_edit, col_delete, col_spacer = st.columns([1, 1, 4])
                with col_edit:
                    if st.button("Edit", key=f"edit_{entry['id']}"):
                        _edit_entry_dialog(entry, services_map)
                with col_delete:
                    if st.button("Delete", key=f"del_{entry['id']}"):
                        _delete_entry_dialog(entry)
