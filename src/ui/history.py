"""Markdown history storage (browser local storage) and UI for generated README content."""

from __future__ import annotations

import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st


IST = ZoneInfo("Asia/Kolkata")


def _now_ist() -> datetime:
    return datetime.now(IST)


def _init_history_storage() -> None:
    """Initialize local storage in session state if not already done."""
    if "_readme_history" not in st.session_state:
        st.session_state["_readme_history"] = {}


def _get_next_version(repo_target: str) -> int:
    """Get the next version number for a repository (from browser storage)."""
    _init_history_storage()
    safe_target = re.sub(r"[^A-Za-z0-9_.-]+", "_", repo_target.strip())
    history = st.session_state["_readme_history"]
    
    # Find all versions for this repo
    existing_versions = []
    for key in history.keys():
        if key.startswith(f"{safe_target}_v"):
            match = re.search(r'_v(\d+)$', key)
            if match:
                existing_versions.append(int(match.group(1)))
    
    return max(existing_versions) + 1 if existing_versions else 1


def _history_key(repo_target: str, version: int) -> str:
    """Generate storage key for a README version."""
    safe_target = re.sub(r"[^A-Za-z0-9_.-]+", "_", repo_target.strip())
    return f"{safe_target}_v{version}"


def save_generation_history(repo_target: str, content: str, generated_at: datetime) -> str:
    """Save README to browser local storage and return the storage key."""
    _init_history_storage()
    version = _get_next_version(repo_target)
    key = _history_key(repo_target, version)
    
    history_data = {
        "repo_target": repo_target,
        "version": version,
        "generated_at": generated_at.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
        "content": content,
    }
    
    st.session_state["_readme_history"][key] = history_data
    return key


def list_history_files() -> list[tuple[str, dict]]:
    """Return list of (display_name, history_data) sorted by repo and version."""
    _init_history_storage()
    history = st.session_state["_readme_history"]
    
    if not history:
        return []
    
    # Sort by repo name, then by version (descending)
    items = []
    for key, data in history.items():
        match = re.search(r'^(.+)_v(\d+)$', key)
        if match:
            repo_safe = match.group(1)
            version = int(match.group(2))
            repo_name = re.sub(r'_', '/', repo_safe, count=1)
            display_name = f"{repo_name} (v{version})"
            items.append((display_name, key, data))
    
    # Sort: by repo name first, then by version descending
    items.sort(key=lambda x: (x[0].split(" (v")[0], -int(x[0].split("v")[1].rstrip(")"))), reverse=True)
    
    return items


def render_history_panel() -> None:
    st.markdown("### 📚 History")
    st.caption("Your README versions are saved locally in your browser. Only you can see them.")

    history_items = list_history_files()
    if not history_items:
        st.info("No history yet. Generate a README and it will be saved automatically.")
        return

    # Extract display names
    display_names = [item[0] for item in history_items]
    display_map = {item[0]: (item[1], item[2]) for item in history_items}

    selected_display = st.selectbox(
        "Saved generations (by repository and version)",
        options=display_names,
        key="history_file_select",
    )
    
    key, history_data = display_map.get(selected_display, (None, None))
    if not history_data:
        st.warning("Selected history item is unavailable.")
        return

    repo_target = history_data.get("repo_target", "")
    version = history_data.get("version", 1)
    generated_at = history_data.get("generated_at", "Unknown")
    content = history_data.get("content", "")
    
    # Build markdown content for download
    history_content = (
        f"# README V{version} - {repo_target}\n\n"
        f"- Generated At: {generated_at}\n"
        f"- Repository: {repo_target}\n"
        f"- Version: {version}\n\n"
        f"---\n\n"
        f"{content}\n"
    )
    
    st.download_button(
        label=f"Download {selected_display}.md",
        data=history_content,
        file_name=f"{re.sub(r'[^A-Za-z0-9_.-]+', '_', repo_target)}_v{version}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    
    with st.expander(f"Preview: {selected_display}", expanded=False):
        st.markdown(history_content)

    if st.button("Load Selected History", key="load_selected_history", use_container_width=True):
        st.session_state["generated_content"] = content
        st.session_state["generated_repo_target"] = repo_target
        st.session_state["generated_history_file"] = f"{selected_display}.md"
        st.success(f"✅ Loaded {selected_display} into the Generated Content section.")
    
    # Export/Import section
    st.divider()
    st.markdown("#### 📤 Backup & Restore")
    col_export, col_import = st.columns(2)
    
    with col_export:
        if st.button("Export All History (JSON)", use_container_width=True):
            export_data = json.dumps(st.session_state["_readme_history"], indent=2)
            st.download_button(
                label="Download History Backup",
                data=export_data,
                file_name=f"readme_history_{_now_ist().strftime('%Y%m%d_%H%M%S')}_IST.json",
                mime="application/json",
                use_container_width=True,
                key="export_history_btn",
            )
    
    with col_import:
        uploaded_file = st.file_uploader("Import History (JSON)", type=["json"], key="import_history_uploader")
        if uploaded_file:
            try:
                imported_data = json.loads(uploaded_file.read().decode())
                st.session_state["_readme_history"].update(imported_data)
                st.success("✅ History imported successfully!")
                st.rerun()
            except json.JSONDecodeError:
                st.error("Invalid JSON file. Please upload a valid history backup.")
