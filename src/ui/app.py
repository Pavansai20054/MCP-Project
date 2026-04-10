"""Professional Streamlit UI for README upgrade generation."""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from src.app_service import list_public_repositories, missing_env_vars
from src.config.env import config
from src.tools.rate_limiter import FileRateLimiter
from src.ui.actions import run_generation, run_readme_update
from src.ui.history import render_history_panel, save_generation_history
from src.ui.panels import (
    inject_styles,
    render_header,
    render_help_panel,
    render_session_panel,
)


NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
RATE_LIMIT_PER_HOUR = 2
RATE_LIMIT_WINDOW_SECONDS = 3600
DEFAULT_MAX_ITERATIONS = 10
IST = ZoneInfo("Asia/Kolkata")

_LIMITER = FileRateLimiter(".runtime/rate_limits.json")


def _now_ist() -> datetime:
    return datetime.now(IST)


def _to_ist(value: datetime) -> datetime:
    if value.tzinfo is None:
        # Backward compatibility for old naive values already in session state.
        # Treat them as UTC and convert to IST.
        return value.replace(tzinfo=ZoneInfo("UTC")).astimezone(IST)
    return value.astimezone(IST)


def _is_valid_name(value: str) -> bool:
    return bool(NAME_PATTERN.match(value.strip()))


def _is_admin_user(username: str) -> bool:
    return username.strip().lower() in set(config.ADMIN_GITHUB_USERS)


@st.cache_data(ttl=300, show_spinner=False)
def _get_repositories_for_user(username: str, github_token: str | None = None) -> tuple[list[str], str | None]:
    return list_public_repositories(username, github_token=github_token)


def _get_user_identifier() -> str:
    """Build a stable key for rate limiting this Streamlit user session."""
    ip_addr = ""
    headers = None

    if hasattr(st, "context"):
        headers = getattr(st.context, "headers", None)

    if headers:
        ip_addr = (
            headers.get("x-forwarded-for")
            or headers.get("x-real-ip")
            or headers.get("remote_addr")
            or ""
        )

    if ip_addr:
        return f"ip:{ip_addr.split(',')[0].strip()}"

    session_key = st.session_state.get("_session_rl_key")
    if not session_key:
        session_key = f"session-{_now_ist().timestamp()}"
        st.session_state["_session_rl_key"] = session_key
    return session_key


def _get_session_started_at() -> datetime:
    started_at = st.session_state.get("_session_started_at")
    if isinstance(started_at, datetime):
        normalized = _to_ist(started_at)
        st.session_state["_session_started_at"] = normalized
        return normalized

    started_at = _now_ist()
    st.session_state["_session_started_at"] = started_at
    return started_at


def main() -> None:
    st.set_page_config(
        page_title="README Upgrade Studio",
        page_icon="R",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_styles()
    render_header()

    missing = missing_env_vars()
    if missing:
        st.error("Missing required environment variables")
        for name in missing:
            st.write(f"- {name}")
        st.stop()

    if "recent_username" not in st.session_state:
        st.session_state["recent_username"] = ""
    if "input_username" not in st.session_state:
        st.session_state["input_username"] = st.session_state["recent_username"]
    if "input_github_token" not in st.session_state:
        st.session_state["input_github_token"] = ""

    max_iterations = DEFAULT_MAX_ITERATIONS
    render_help_panel()
    st.markdown("<div style='height: 0.4rem;'></div>", unsafe_allow_html=True)

    if "show_history_panel" not in st.session_state:
        st.session_state["show_history_panel"] = False

    toggle_label = "Hide History" if st.session_state["show_history_panel"] else "Show History"
    if st.button(toggle_label, key="toggle_history_panel", use_container_width=False):
        st.session_state["show_history_panel"] = not st.session_state["show_history_panel"]

    if st.session_state["show_history_panel"]:
        render_history_panel()

    st.subheader("🔐 GitHub Personal Access Token (Required)")
    st.text_input(
        "Enter your GitHub token",
        type="password",
        placeholder="ghp_xxx...",
        help="Create at https://github.com/settings/tokens with Contents: Read and write permission.",
        key="input_github_token",
    )
    effective_github_token = (st.session_state.get("input_github_token") or "").strip() or (config.GITHUB_TOKEN or "").strip()
    if not effective_github_token:
        st.caption("Token is required for repo analysis and README update.")

    col_left, col_right = st.columns([2, 1], gap="large")
    with col_left:
        form_col1, form_col2 = st.columns(2)
        with form_col1:
            username = st.text_input(
                "GitHub Username",
                placeholder="owner",
                help="Example: octocat",
                key="input_username",
            )
            if username.strip():
                st.session_state["recent_username"] = username.strip()

        repos: list[str] = []
        repo_error: str | None = None
        if username.strip() and _is_valid_name(username):
            with st.spinner("Fetching public repositories..."):
                repos, repo_error = _get_repositories_for_user(username.strip(), github_token=effective_github_token)

        with form_col2:
            if username.strip() and not _is_valid_name(username):
                repository = st.selectbox(
                    "Repository Name",
                    options=[""],
                    format_func=lambda _: "Enter a valid GitHub username first",
                )
            elif not username.strip():
                repository = st.selectbox(
                    "Repository Name",
                    options=[""],
                    format_func=lambda _: "Enter GitHub username first",
                )
            elif repos:
                repository = st.selectbox(
                    "Repository Name",
                    options=repos,
                    index=None,
                    placeholder="Select a public repository",
                    help="Public repositories for the entered username.",
                )
            else:
                repository = st.selectbox(
                    "Repository Name",
                    options=[""],
                    format_func=lambda _: "No repositories available",
                )

        if repo_error:
            st.warning(repo_error)

        selected_repository = repository or ""
        repo_target = f"{username.strip()}/{selected_repository.strip()}"
        st.caption(f"Target: {repo_target if username or repository else 'owner/repo'}")

        st.divider()
        st.subheader("📝 Author Info (Optional)")
        author_col1, author_col2 = st.columns(2)
        with author_col1:
            author_linkedin = st.text_input(
                "LinkedIn Profile URL",
                placeholder="https://linkedin.com/in/yourprofile",
                help="Your LinkedIn profile URL for the README author section.",
                key="input_author_linkedin",
            )
        with author_col2:
            author_email = st.text_input(
                "Email Address",
                placeholder="your.email@gmail.com",
                help="Your email address for the README author section.",
                key="input_author_email",
            )

        generate_clicked = st.button("Generate README", type="primary", use_container_width=True)

    with col_right:
        render_session_panel(started_at=_get_session_started_at())

    if generate_clicked:
        if not username.strip() or not repository:
            st.warning("Please enter both GitHub username and repository name.")
            st.stop()

        if not effective_github_token:
            st.warning("Please provide a GitHub Personal Access Token to generate and update README.")
            st.stop()

        if not _is_valid_name(username) or not _is_valid_name(repository):
            st.warning(
                "Only letters, numbers, dot (.), underscore (_) and hyphen (-) are allowed in username/repository."
            )
            st.stop()

        if not _is_admin_user(username):
            user_key = _get_user_identifier()
            rate_result = _LIMITER.consume(
                key=user_key,
                limit=RATE_LIMIT_PER_HOUR,
                window_seconds=RATE_LIMIT_WINDOW_SECONDS,
            )
            if not rate_result.allowed:
                wait_minutes = max(1, (rate_result.retry_after_seconds + 59) // 60)
                st.error(f"You have reached the generation limit. Please try again in about {wait_minutes} minute(s).")
                st.stop()
            st.info("Generation started.")
        else:
            st.info("Generation started.")

        with st.spinner("Generating improved README. This may take a minute..."):
            content, error_message = run_generation(
                repo_target=repo_target,
                max_iterations=max_iterations,
                author_linkedin=author_linkedin.strip() if author_linkedin else None,
                author_email=author_email.strip() if author_email else None,
                github_token=effective_github_token,
            )

        if not content:
            if error_message:
                st.error(error_message)
            else:
                st.error("No content was generated. Try increasing max iterations or narrowing repository scope.")
            st.stop()

        st.success("README generated successfully.")
        generated_at = _now_ist()
        st.session_state["generated_content"] = content
        st.session_state["generated_repo_target"] = repo_target
        st.session_state["generated_at"] = generated_at.strftime("%Y-%m-%d %H:%M:%S IST")
        history_key = save_generation_history(repo_target=repo_target, content=content, generated_at=generated_at)
        st.session_state["generated_history_file"] = history_key

    generated_content = st.session_state.get("generated_content")
    generated_repo_target = st.session_state.get("generated_repo_target")

    if generated_content and generated_repo_target:
        if "is_editing_generated" not in st.session_state:
            st.session_state["is_editing_generated"] = False
        if "generated_draft_content" not in st.session_state:
            st.session_state["generated_draft_content"] = generated_content

        # Keep draft synced with fresh generation when not actively editing.
        if not st.session_state["is_editing_generated"]:
            st.session_state["generated_draft_content"] = generated_content

        st.subheader("Generated Content")

        action_col1, action_col2, action_col3 = st.columns([1, 1, 3])
        with action_col1:
            if st.button("Edit README", key="edit_generated_readme", use_container_width=True):
                st.session_state["is_editing_generated"] = True
                st.session_state["generated_draft_content"] = st.session_state.get("generated_content", "")
        with action_col2:
            if st.button("Cancel Edit", key="cancel_generated_edit", use_container_width=True):
                st.session_state["is_editing_generated"] = False
                st.session_state["generated_draft_content"] = st.session_state.get("generated_content", "")

        if st.session_state["is_editing_generated"]:
            st.text_area(
                "Edit README Markdown",
                key="generated_draft_content",
                height=420,
                help="Changes are temporary until you click Save Changes.",
            )
            if st.button("Save Changes", key="save_generated_edit", use_container_width=True):
                st.session_state["generated_content"] = st.session_state.get("generated_draft_content", "")
                st.session_state["is_editing_generated"] = False
                st.success("Changes saved locally. You can now preview, download, or update GitHub.")

        preview_mode = st.radio(
            "Preview mode",
            options=["Rendered", "Raw Markdown"],
            horizontal=True,
            key="generated_preview_mode",
        )
        if preview_mode == "Raw Markdown":
            st.code(st.session_state.get("generated_content", ""), language="markdown")
        else:
            st.markdown(st.session_state.get("generated_content", ""))
        st.caption(f"Repository: {generated_repo_target}")
        if st.session_state.get("generated_history_file"):
            st.caption(f"Saved in history: {st.session_state['generated_history_file']}")

        commit_message = st.text_input(
            "Commit message for README update",
            value="docs: update README via README Upgrade Studio",
            help="This commit message will be used when updating README.md via MCP.",
        )
        branch_name = st.text_input(
            "Branch name",
            value="main",
            help="Target branch for the README update.",
        )

        update_clicked = st.button("Update README.md in GitHub Repository", use_container_width=True)
        if update_clicked:
            if not effective_github_token:
                st.error("GitHub token is required to update README in repository.")
                st.stop()
            with st.spinner("Updating README.md through MCP..."):
                ok, update_message = run_readme_update(
                    repo_target=generated_repo_target,
                    content=st.session_state.get("generated_content", ""),
                    commit_message=commit_message.strip() or "docs: update README",
                    branch=branch_name.strip() or "main",
                    github_token=effective_github_token,
                )
            if ok:
                st.success(update_message)
            else:
                st.error(update_message)

        st.download_button(
            label="Download README.md",
            data=st.session_state.get("generated_content", ""),
            file_name="README.md",
            mime="text/markdown",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()