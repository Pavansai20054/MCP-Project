"""Core orchestration loop for README upgrade flow."""

from __future__ import annotations

from typing import Any

from src.prompts.readme_upgrade import build_system_prompt, build_user_prompt
from src.tools.groq_client import call_groq
from src.tools.mcp_bridge import execute_tool_calls


def build_messages(
    repo_target: str,
    repo_snapshot: str | None = None,
    author_linkedin: str | None = None,
    author_email: str | None = None,
) -> list[dict[str, str]]:
    """Construct initial system and user messages."""
    return [
        {"role": "system", "content": build_system_prompt()},
        {
            "role": "user",
            "content": build_user_prompt(
                repo_target,
                repo_snapshot,
                author_linkedin,
                author_email,
            ),
        },
    ]


async def run_readme_upgrade(
    session: Any,
    repo_target: str,
    groq_tools: list[dict[str, Any]],
    max_iterations: int = 10,
    repo_snapshot: str | None = None,
    author_linkedin: str | None = None,
    author_email: str | None = None,
) -> tuple[str | None, str | None]:
    """Run the agentic loop and return final generated content plus any error."""
    messages: list[dict[str, Any]] = build_messages(
        repo_target,
        repo_snapshot,
        author_linkedin,
        author_email,
    )

    for _ in range(max_iterations):
        response = await call_groq(messages, groq_tools)
        if not response:
            error_message = (
                "Groq request failed before a response was produced. "
                "Check the API key, model access, and network connectivity."
            )
            print(error_message)
            return None, error_message

        if "error" in response:
            error = response.get("error", {})
            error_message = error.get("message") if isinstance(error, dict) else str(error)
            if error_message and "failed_generation" in error_message:
                error_message = (
                    "Groq could not complete a valid function call. "
                    "The prompt or tool schema may be too restrictive."
                )
            print(error_message or "Stopped due to API error.")
            return None, error_message or "Stopped due to API error."

        if "choices" not in response:
            error_message = "Groq returned an unexpected response shape."
            print(error_message)
            return None, error_message

        message = response["choices"][0]["message"]
        messages.append(message)

        if message.get("tool_calls"):
            tool_messages = await execute_tool_calls(session, message["tool_calls"])
            messages.extend(tool_messages)
            continue

        if message.get("content"):
            return message["content"], None

        return None, "Groq returned an empty assistant message."

    error_message = "Reached max iteration limit before the model produced a final README."
    print(error_message)
    return None, error_message