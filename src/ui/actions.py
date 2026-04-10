"""Action helpers for generation and MCP-based README updates."""

from __future__ import annotations

import asyncio

from src.app_service import generate_readme_upgrade, update_repository_readme


def run_generation(
    repo_target: str,
    max_iterations: int,
    author_linkedin: str | None = None,
    author_email: str | None = None,
    github_token: str | None = None,
) -> tuple[str | None, str | None]:
    return asyncio.run(
        generate_readme_upgrade(
            repo_target=repo_target,
            max_iterations=max_iterations,
            author_linkedin=author_linkedin,
            author_email=author_email,
            github_token=github_token,
        )
    )


def run_readme_update(
    repo_target: str,
    content: str,
    commit_message: str,
    branch: str,
    github_token: str | None = None,
) -> tuple[bool, str]:
    return asyncio.run(
        update_repository_readme(
            repo_target=repo_target,
            readme_content=content,
            commit_message=commit_message,
            branch=branch,
            github_token=github_token,
        )
    )
