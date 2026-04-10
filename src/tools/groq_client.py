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
        except Exception as exc:
            print(f"HTTP request failed: {exc}")
            return None

    try:
        data = response.json()
    except Exception:
        data = None

    if response.is_error:
        message = response.text.strip() or "Groq API request failed."
        if isinstance(data, dict):
            error = data.get("error")
            if isinstance(error, dict):
                message = error.get("message") or message
        print(f"Groq API error: {message}")
        return {"error": {"message": message, "status_code": response.status_code}}

    if isinstance(data, dict) and "error" in data:
        error = data.get("error")
        message = "Groq API error."
        if isinstance(error, dict):
            message = error.get("message") or message
        print(f"Groq API error: {message}")
        return data

    if isinstance(data, dict):
        return data

    print("Groq API returned an unexpected response payload.")
    return {"error": {"message": "Groq API returned an unexpected response payload."}}