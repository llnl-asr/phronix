"""phronix's capability engine: capability bundles and the predictor -> validator -> corrector discipline.

A capability is a directory (``capstore``): ``tool.py`` (the MCP tools), ``capability.json`` (name, version, history,
``pvc``: which tools predict and which validate), ``SKILL.md`` (rules, corner cases, the corrector, self-heal,
self-learn, what works), ``LESSONS.md``, ``WORKED.md``, ``agent.json``, ``checks.json`` (run sandboxed on every change)
and ``versions/``. Around it: lessons (``learning``), the knowledge graph (``knowledge``), consolidation
(``consolidate``), the verdict and the corrector's budget (``verdict``), edits that take effect without a restart
(``selfrefresh``), which project owns a capability (``scopes``) and contributing back to it (``upstream``).

A project configures it once (``configure``) with its package, environment prefix, its scope and the scopes upstream
of it, then uses these modules as its own.
"""
from .config import S as settings
from .config import configure, scoped_change, shared_change

__all__ = ["configure", "settings", "shared_change", "scoped_change"]
