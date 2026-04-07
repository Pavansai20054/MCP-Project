"""Application services shared by CLI and UI entrypoints."""

from __future__ import annotations

import httpx

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from src.config.env import config
from src.orchestrator import run_readme_upgrade
from src.tools.mcp_bridge import build_server_params, to_groq_tools


async def generate_readme_upgrade(repo_target: str, max_iterations: int) -> str | None:
    """Generate upgraded README content for a target repository."""
    server_params = build_server_params()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_res = await session.list_tools()
            groq_tools = to_groq_tools(tools_res.tools)

            return await run_readme_upgrade(
                session=session,
                repo_target=repo_target,
                groq_tools=groq_tools,
                max_iterations=max_iterations,
            )


def missing_env_vars() -> list[str]:
    """Return list of required environment variables that are not set."""
    missing: list[str] = []
    if not config.GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not config.GITHUB_TOKEN:
        missing.append("GITHUB_PERSONAL_ACCESS_TOKEN")
    return missing


def list_public_repositories(username: str) -> tuple[list[str], str | None]:
    """Return all public repository names for a GitHub username."""
    repos: list[str] = []
    page = 1
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "readme-upgrade-studio",
    }
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"

    with httpx.Client(timeout=20.0, headers=headers) as client:
        while True:
            url = f"https://api.github.com/users/{username}/repos"
            response = client.get(url, params={"type": "public", "per_page": 100, "page": page})

            if response.status_code == 404:
                return [], "GitHub username not found."
            if response.status_code >= 400:
                return [], f"GitHub API error ({response.status_code})."

            data = response.json()
            if not isinstance(data, list):
                return [], "Unexpected response from GitHub API."
            if not data:
                break

            repos.extend([repo.get("name", "") for repo in data if repo.get("name")])
            if len(data) < 100:
                break
            page += 1

    repos = sorted(set(repos), key=str.lower)
    if not repos:
        return [], "No public repositories found for this user."
    return repos, None