"""FastMCP middleware that injects relevant memory into tool traffic.

Prompt hooks cover the user's raw prompt, but only for the harnesses that have a
hook mechanism. Every harness, without exception, talks to this MCP server — so
tool traffic is the one channel where injection works uniformly, and this
middleware is where that happens.

It appends the context block to a tool's *result* rather than mutating its
arguments: arguments are a contract the tool validates, and a memory digest
smuggled into one would at best be ignored and at worst break the call.

Everything here is best-effort. A failure in retrieval must never turn a
successful tool call into a failed one, so every hook is wrapped and any
exception falls through to the untouched result.
"""
from __future__ import annotations

from typing import Any, Optional

from phronix.context_pack import build_pack, tool_query


def _session_id(context: Any) -> str:
    """Best-effort session identity from whatever the middleware context exposes.

    FastMCP's context shape varies by version and transport, so this probes
    several attributes and falls back to a constant. A wrong-but-stable id only
    costs dedup accuracy across concurrent sessions; raising here would cost the
    tool call.
    """
    for attr in ("session_id", "client_id", "request_id"):
        value = getattr(context, attr, None)
        if isinstance(value, str) and value:
            return value
    session = getattr(context, "session", None)
    for attr in ("session_id", "id"):
        value = getattr(session, attr, None)
        if isinstance(value, str) and value:
            return value
    return "mcp"


def _as_text(result: Any) -> Optional[str]:
    """Extract appendable text from a tool result, or ``None`` if there is none."""
    if isinstance(result, str):
        return result
    content = getattr(result, "content", None)
    if isinstance(content, list) and content:
        text = getattr(content[0], "text", None)
        if isinstance(text, str):
            return text
    return None


def _append(result: Any, block: str) -> Any:
    """Return *result* with *block* appended, preserving its original shape."""
    if isinstance(result, str):
        return result + "\n\n" + block
    content = getattr(result, "content", None)
    if isinstance(content, list) and content and hasattr(content[0], "text"):
        try:
            content[0].text = f"{content[0].text}\n\n{block}"
        except Exception:
            return result
    return result


def install(server: Any) -> Any:
    """Attach the injection middleware to a FastMCP *server*, if it supports one.

    Returns the server either way. A FastMCP build without a middleware API is a
    degraded experience (no tool-channel injection), not a broken one, so this
    reports rather than raises.
    """
    try:
        from fastmcp.server.middleware import Middleware, MiddlewareContext
    except Exception:
        return server

    class PhronixContextMiddleware(Middleware):
        """Append newly-relevant memory to each tool result."""

        async def on_call_tool(self, context: "MiddlewareContext", call_next):
            result = await call_next(context)
            try:
                message = getattr(context, "message", None)
                name = getattr(message, "name", "") or ""
                arguments = getattr(message, "arguments", None) or {}
                if not name or _as_text(result) is None:
                    return result
                block = build_pack(
                    tool_query(name, arguments),
                    session_id=_session_id(context),
                    kind="tool",
                )
                return _append(result, block) if block else result
            except Exception:
                return result

    try:
        server.add_middleware(PhronixContextMiddleware())
    except Exception:
        pass
    return server
