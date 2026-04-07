"""Groq API client helpers."""

from __future__ import annotations

from typing import Any

import httpx

from src.config.env import config


async def call_groq(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Call Groq chat-completions with MCP tool definitions."""
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.GROQ_MODEL,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                config.GROQ_BASE_URL,
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            data = response.json()
            if "error" in data:
                print(f"Groq API error: {data['error'].get('message')}")
                return None
            return data
        except Exception as exc:
            print(f"HTTP request failed: {exc}")
            return None