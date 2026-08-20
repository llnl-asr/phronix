"""Verifies: the tools the context-economy skill tells agents to call actually exist.

A skill that names a tool creates an obligation on the code. When a tool is
renamed or dropped and the skill is not updated, every agent following that skill
calls something that is not there — and the failure appears as a confused agent
mid-task, far from the documentation that caused it.

This corrector closes the loop by checking the skill's prose against the tools the
server really registers. Deterministic: a static scan of the tool definitions and
a substring search of the skill text, with no environment involved.
"""
from __future__ import annotations

import re
from pathlib import Path

#: Tool names the skill must document, because they are the entry points an agent
#: is told to reach for first. A skill that stops mentioning one of these has
#: quietly dropped the instruction that makes the tool get used at all.
_REQUIRED_MENTIONS = ("graph_query", "graph_ensure")

_TOOL_DEF_RE = re.compile(r"@[A-Za-z_][A-Za-z0-9_.]*\.tool\(\)\s*def\s+(\w+)\s*\(")
_TOOL_REF_RE = re.compile(r"\b((?:graph|skill|memory|context|verify|capability|privacy)_\w+)\s*\(")


def _registered_tools(ctx):
    """Every tool name the built-in services and learned capabilities register."""
    import phronix

    names = set()
    root = Path(phronix.__file__).resolve().parent / "mcp_tools"
    for path in sorted(root.rglob("*.py")):
        names.update(_TOOL_DEF_RE.findall(path.read_text(errors="replace")))
    try:
        from phronix.layers import capability_files

        for path in capability_files().values():
            names.update(_TOOL_DEF_RE.findall(path.read_text(errors="replace")))
    except Exception:
        pass
    return names or None


def _skill_text(ctx):
    from phronix.layers import skill_dirs

    directory = skill_dirs().get("phronix-context-economy")
    if directory is None:
        return None
    skill_md = directory / "SKILL.md"
    return skill_md.read_text(encoding="utf-8", errors="replace") if skill_md.is_file() else None


def _every_referenced_tool_exists(ctx):
    referenced = set(_TOOL_REF_RE.findall(ctx["skill_text"]))
    missing = sorted(referenced - ctx["registered_tools"])
    return (not missing,
            f"skill references tools that are not registered: {missing}" if missing
            else f"all {len(referenced)} referenced tools are registered")


def _required_tools_are_documented(ctx):
    absent = [name for name in _REQUIRED_MENTIONS if name not in ctx["skill_text"]]
    return (not absent,
            f"skill no longer documents: {absent}" if absent
            else f"documents all {len(_REQUIRED_MENTIONS)} required entry points")


def _shows_a_runnable_example(ctx):
    """The skill must carry a fenced example, not only prose about the idea."""
    fences = ctx["skill_text"].count("```") // 2
    return (fences > 0,
            f"{fences} fenced example(s)" if fences else
            "no fenced code block; agents copy the example, not the prose")


SPEC = {
    "kind": "skill",
    "target": "phronix-context-economy",
    "claim": (
        "Every tool the phronix-context-economy skill tells an agent to call is "
        "actually registered by the MCP server, and the skill still documents the "
        "graph entry points with a runnable example."
    ),

    "assumptions": [
        {"name": "skill_is_visible",
         "detail": "the phronix-context-economy skill is in the merged store",
         "check": lambda ctx: _skill_text(ctx) is not None},
        {"name": "tools_are_scannable",
         "detail": "the mcp_tools package is importable and readable",
         "check": lambda ctx: bool(_registered_tools(ctx))},
    ],

    "inputs": [
        {"name": "registered_tools", "required": True,
         "detail": "tool names discovered by static scan of the tool definitions",
         "resolve": _registered_tools},
        {"name": "skill_text", "required": True,
         "detail": "the skill's SKILL.md body",
         "resolve": _skill_text},
    ],

    "constraints": [
        {"name": "no_dangling_tool_references",
         "detail": "the skill names no tool that does not exist",
         "check": _every_referenced_tool_exists},
        {"name": "entry_points_documented",
         "detail": "the graph entry points are still named in the skill",
         "check": _required_tools_are_documented},
    ],

    "invariants": [
        {"name": "skill_unmodified",
         "detail": "verifying the skill does not rewrite it",
         "sample": lambda ctx: len(ctx.get("skill_text") or "")},
    ],

    "outputs": [
        {"name": "runnable_example_present",
         "detail": "the skill carries a fenced example agents can copy",
         "check": _shows_a_runnable_example},
    ],
}
