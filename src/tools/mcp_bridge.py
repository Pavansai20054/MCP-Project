"""Helpers to work with MCP tool sessions."""

from __future__ import annotations

import json
import os
from typing import Any

from mcp import StdioServerParameters

from src.config.env import config


MAX_TOOL_CONTENT_CHARS = 4000


def _clip_tool_content(content: str) -> str:
    if len(content) <= MAX_TOOL_CONTENT_CHARS:
        return content
    clipped = content[:MAX_TOOL_CONTENT_CHARS]
    return (
        f"{clipped}\n\n[truncated: original output was {len(content)} characters; "
        "request narrower paths or fewer files for full detail]"
    )


def build_server_params() -> StdioServerParameters:
    """Build stdio server parameters for the GitHub MCP server."""
    return StdioServerParameters(
        command=config.MCP_COMMAND,
        args=config.MCP_ARGS,
        env={**os.environ, "GITHUB_PERSONAL_ACCESS_TOKEN": config.GITHUB_TOKEN},
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
        print(f"Running tool: {fn_name}({fn_args})")

        try:
            tool_result = await session.call_tool(fn_name, fn_args)
            content = str(tool_result.content)
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