"""Core orchestration loop for README upgrade flow."""

from __future__ import annotations

from typing import Any

from src.prompts.readme_upgrade import build_system_prompt, build_user_prompt
from src.tools.groq_client import call_groq
from src.tools.mcp_bridge import execute_tool_calls


def build_messages(repo_target: str) -> list[dict[str, str]]:
    """Construct initial system and user messages."""
    return [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": build_user_prompt(repo_target)},
    ]


async def run_readme_upgrade(
    session: Any,
    repo_target: str,
    groq_tools: list[dict[str, Any]],
    max_iterations: int = 10,
) -> str | None:
    """Run the agentic loop and return final generated content."""
    messages: list[dict[str, Any]] = build_messages(repo_target)

    for _ in range(max_iterations):
        response = await call_groq(messages, groq_tools)
        if not response or "choices" not in response:
            print("Stopped due to API error.")
            return None

        message = response["choices"][0]["message"]
        messages.append(message)

        if message.get("tool_calls"):
            tool_messages = await execute_tool_calls(session, message["tool_calls"])
            messages.extend(tool_messages)
            continue

        if message.get("content"):
            return message["content"]

        return None

    print("Reached max iteration limit.")
    return None