"""Helpers to work with MCP tool sessions."""

from __future__ import annotations

import json
import os
from typing import Any

from mcp import StdioServerParameters

from src.config.env import config


MAX_TOOL_CONTENT_CHARS = 12000


def _normalize_tool_result_content(raw_content: Any) -> str:
    """Convert MCP tool content objects into plain text for model consumption."""
    if raw_content is None:
        return ""

    if isinstance(raw_content, str):
        return raw_content

    if isinstance(raw_content, list):
        parts: list[str] = []
        for item in raw_content:
            text_value = getattr(item, "text", None)
            if isinstance(text_value, str):
                parts.append(text_value)
                continue

            if isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                    continue
                if isinstance(item.get("content"), str):
                    parts.append(item["content"])
                    continue

            parts.append(str(item))

        return "\n".join(part for part in parts if part)

    text_attr = getattr(raw_content, "text", None)
    if isinstance(text_attr, str):
        return text_attr

    return str(raw_content)


def _clip_tool_content(content: str) -> str:
    if len(content) <= MAX_TOOL_CONTENT_CHARS:
        return content
    clipped = content[:MAX_TOOL_CONTENT_CHARS]
    return (
        f"{clipped}\n\n[truncated: original output was {len(content)} characters; "
        "request narrower paths or fewer files for full detail]"
    )


def build_server_params(github_token: str | None = None) -> StdioServerParameters:
    """Build stdio server parameters for the GitHub MCP server."""
    token = (github_token or config.GITHUB_TOKEN or "").strip()
    return StdioServerParameters(
        command=config.MCP_COMMAND,
        args=config.MCP_ARGS,
        env={
            **os.environ,
            "GITHUB_PERSONAL_ACCESS_TOKEN": token,
            "GITHUB_TOKEN": token,
            "GH_TOKEN": token,
        },
    )


def to_groq_tools(mcp_tools: list[Any]) -> list[dict[str, Any]]:
    """Convert MCP tool schemas into Groq-compatible function tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        }
        for tool in mcp_tools
    ]


async def execute_tool_calls(session: Any, tool_calls: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Execute all tool calls requested by the model and return tool messages."""
    tool_messages: list[dict[str, str]] = []

    for tool_call in tool_calls:
        fn_name = tool_call["function"]["name"]
        fn_args = json.loads(tool_call["function"]["arguments"])

        try:
            tool_result = await session.call_tool(fn_name, fn_args)
            content = _normalize_tool_result_content(getattr(tool_result, "content", None))
        except Exception as exc:
            content = f"Tool execution failed: {exc}"

        content = _clip_tool_content(content)

        tool_messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": fn_name,
                "content": content,
            }
        )

    return tool_messages