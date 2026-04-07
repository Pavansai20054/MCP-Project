"""Professional Streamlit UI for README upgrade generation."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime

import streamlit as st

from src.app_service import generate_readme_upgrade, list_public_repositories, missing_env_vars
from src.config.env import config
from src.tools.rate_limiter import FileRateLimiter


NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
RATE_LIMIT_PER_HOUR = 2
RATE_LIMIT_WINDOW_SECONDS = 3600

_LIMITER = FileRateLimiter(".runtime/rate_limits.json")


def _is_valid_name(value: str) -> bool:
    return bool(NAME_PATTERN.match(value.strip()))


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 10% 15%, rgba(26, 96, 255, 0.18) 0%, rgba(26, 96, 255, 0) 30%),
                radial-gradient(circle at 85% 20%, rgba(0, 194, 168, 0.18) 0%, rgba(0, 194, 168, 0) 35%);
        }
        .app-hero {
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 14px;
            padding: 1.2rem 1.2rem 0.8rem 1.2rem;
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.68) 0%, rgba(30, 41, 59, 0.58) 100%);
            box-shadow: 0 10px 30px rgba(2, 6, 23, 0.35);
            margin-bottom: 1rem;
            backdrop-filter: blur(8px);
        }
        .status-card {
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 12px;
            padding: 0.8rem 1rem;
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.6) 0%, rgba(30, 41, 59, 0.5) 100%);
            backdrop-filter: blur(8px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    st.markdown(
        """
        <div class="app-hero">
            <h2 style="margin-bottom:0.3rem;color:#f8fafc;">README Upgrade Studio</h2>
            <p style="margin-top:0.2rem;color:#cbd5e1;">
                Audit a GitHub repository and generate a stronger, production-grade README using MCP + Groq.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar() -> int:
    st.sidebar.header("Generation Settings")
    st.sidebar.caption(f"Model: {config.GROQ_MODEL}")
    max_iterations = st.sidebar.slider(
        "Max iterations",
        min_value=3,
        max_value=20,
        value=10,
        help="Higher values can improve depth but take longer.",
    )
    st.sidebar.markdown("---")
    st.sidebar.write("Tip: Start with 8-10, then increase if output is incomplete.")
    return max_iterations


def _run_generation(repo_target: str, max_iterations: int) -> str | None:
    return asyncio.run(generate_readme_upgrade(repo_target=repo_target, max_iterations=max_iterations))


@st.cache_data(ttl=300, show_spinner=False)
def _get_repositories_for_user(username: str) -> tuple[list[str], str | None]:
    return list_public_repositories(username)


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
        session_key = f"session-{datetime.now().timestamp()}"
        st.session_state["_session_rl_key"] = session_key
    return session_key


def main() -> None:
    st.set_page_config(
        page_title="README Upgrade Studio",
        page_icon="R",
        layout="wide",
    )
    _inject_styles()
    _render_header()

    missing = missing_env_vars()
    if missing:
        st.error("Missing required environment variables")
        for name in missing:
            st.write(f"- {name}")
        st.stop()

    max_iterations = _render_sidebar()

    col_left, col_right = st.columns([2, 1], gap="large")
    with col_left:
        form_col1, form_col2 = st.columns(2)
        with form_col1:
            username = st.text_input(
                "GitHub Username",
                placeholder="owner",
                help="Example: octocat",
            )

        repos: list[str] = []
        repo_error: str | None = None
        if username.strip() and _is_valid_name(username):
            with st.spinner("Fetching public repositories..."):
                repos, repo_error = _get_repositories_for_user(username.strip())

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
        generate_clicked = st.button("Generate README V2", type="primary", use_container_width=True)

    with col_right:
        st.markdown('<div class="status-card">', unsafe_allow_html=True)
        st.write("Session")
        st.caption(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.caption("Output can be downloaded as markdown once generated.")
        st.markdown("</div>", unsafe_allow_html=True)

    if generate_clicked:
        if not username.strip() or not repository:
            st.warning("Please enter both GitHub username and repository name.")
            st.stop()

        if not _is_valid_name(username) or not _is_valid_name(repository):
            st.warning(
                "Only letters, numbers, dot (.), underscore (_) and hyphen (-) are allowed in username/repository."
            )
            st.stop()

        user_key = _get_user_identifier()
        rate_result = _LIMITER.consume(
            key=user_key,
            limit=RATE_LIMIT_PER_HOUR,
            window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        )
        if not rate_result.allowed:
            wait_minutes = max(1, (rate_result.retry_after_seconds + 59) // 60)
            st.error(
                f"Rate limit reached: only {RATE_LIMIT_PER_HOUR} generations per hour are allowed. "
                f"Please try again in about {wait_minutes} minute(s)."
            )
            st.stop()

        st.info(f"Generation started. Remaining quota this hour: {rate_result.remaining}")

        with st.spinner("Generating improved README. This may take a minute..."):
            content = _run_generation(repo_target=repo_target, max_iterations=max_iterations)

        if not content:
            st.error("No content was generated. Try increasing max iterations or narrowing repository scope.")
            st.stop()

        st.success("README generated successfully.")
        st.subheader("Generated Content")
        st.markdown(content)
        st.download_button(
            label="Download README_V2.md",
            data=content,
            file_name="README_V2.md",
            mime="text/markdown",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()