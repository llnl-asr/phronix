"""Capability tools: how the framework builds new deterministic tools for itself.

The first tier of the build order, exposed to agents. When a session works out a
procedure whose steps are always the same, the right home for it is code, not
prose — and these tools are how an agent writes that code without leaving the
session.
"""
from __future__ import annotations

import json
from typing import Any


def register(mcp: Any) -> None:
    @mcp.tool()
    def capability_list() -> str:
        """List the deterministic tools this project has built for itself.

        Capabilities are MCP tools authored at runtime and committed with the
        layer they live in. Check here before writing a new one — and before doing
        a repetitive task by hand, since the tool for it may already exist.

        Returns JSON: {status, count, capabilities: [{name, description, layer, file}]}.
        """
        from phronix.capabilities import listing

        capabilities = listing()
        return json.dumps({
            "status": "ok",
            "count": len(capabilities),
            "capabilities": capabilities,
            "usage": "capability_new(name=..., description=..., source=...) to add one.",
        }, indent=2)

    @mcp.tool()
    def capability_new(
        name: str,
        description: str,
        source: str = "",
        layer: str = "",
        overwrite: bool = False,
        topic: str = "",
    ) -> str:
        """Turn a deterministic procedure into a permanent MCP tool.

        **Reach for this whenever you notice yourself following fixed steps.** A
        deterministic task written down as prose in a skill will be re-interpreted
        every run, and re-interpretation is where drift comes from. The same task
        as code runs identically every time, for every agent, in every harness.

        Write a capability when the procedure has one correct answer given its
        inputs — a transformation, a check, a lookup, a parse. Write a skill
        instead when it needs judgment.

        The module must define ``register(mcp)`` and register its tools inside it::

            def register(mcp):
                @mcp.tool()
                def count_todos(path: str) -> str:
                    \"\"\"Count TODO markers under *path*.\"\"\"
                    ...

        Give every tool a real docstring: it is the only description the model
        sees, and a vague one produces a tool nobody calls correctly.

        Args:
            name: snake_case module name.
            description: one line explaining what the capability is for.
            source: the full module text. Omit to get a working scaffold you can
                fill in afterwards.
            layer: force a target layer ("project", "user", "bundled"). Defaults
                to the layer whose audience should inherit it.
            overwrite: replace an existing capability of the same name.
            topic: the task key, when this tool KNOWS that task — it names its
                repository, its files, or the shape of its fix. Filed under that
                task rather than beside the method tools, which is what lets a
                later from-scratch run inherit how to run tests without also
                inheriting this task's answer. Leave empty for a genuine method
                tool: one that would work unchanged on a repository you have
                never seen.

        The module is compiled and checked for ``register`` BEFORE it is saved, so
        a broken capability is rejected now rather than failing at the next server
        start with nobody around who knows what it was for.

        Returns JSON: {status, file, layer, scaffolded, next}. The tool is not
        callable until the MCP server restarts — a running server holds tool
        closures captured at registration time.
        """
        from phronix.capabilities import new

        try:
            return json.dumps(
                new(name, description, source=source or None,
                    layer=layer or None, overwrite=overwrite, topic=topic),
                indent=2,
            )
        except Exception as exc:
            return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
