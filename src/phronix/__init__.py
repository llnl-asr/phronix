"""phronix — a self-learning, self-healing agentic framework.

The build order is deliberate and is the framework's whole thesis:

1. **Capabilities first.** Anything deterministic becomes an MCP *tool*, not a
   paragraph of prose an agent has to re-derive every run (``mcp_tools/``,
   plus runtime-authored tools under a layer's ``capabilities/``).
2. **Then intelligence.** What cannot be made deterministic becomes a *skill* —
   a markdown document that evolves as sessions teach it something new.
3. **Then agents.** Specialized actors that scope down to the skills and tools
   their task needs, each carrying a standing instruction to self-heal (fix the
   tool/wiring rather than work around it) and self-learn (write the lesson back).

Everything an agent learns is persisted to a *layer* (see :mod:`phronix.layers`)
and travels with the project, so the next person to clone it starts where the
last session finished.
"""
from __future__ import annotations

try:
    from phronix._version import version as __version__
except Exception:  # pragma: no cover - source checkout without setuptools-scm
    __version__ = "0.0.0.dev0"

__all__ = ["__version__"]
