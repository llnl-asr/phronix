"""Which project a capability belongs to.

Capabilities live with the project whose subject they are, and the projects form a chain: phronix (the framework and
everything general: workloads, software, systems, tools, process) <- dftracer-agents (performance engineering with
dftracer) <- moirai-agents (data provenance) and rabbit-agent (using Rabbits). A project loads its own capabilities
over those of everything upstream of it, and what it learns about a capability upstream goes back upstream (see
:mod:`phronix.engine.upstream`), so each capability keeps one home.

Ownership of a capability, most specific first:

1. its ``tool.py`` imports a project's package (``rabbit_agent``, ``moirai_agents``, ``dftracer_agents``): that project,
   the most downstream one when it imports several (a capability can only live where its imports resolve);
2. its name has a project's prefix (``dftracer_``, ``prov_``, ``ropt_``, ...) or is one of its names;
3. otherwise phronix, the root of the chain.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Scope:
    project: str                          # "dftracer-agents"
    package: str                          # its import name, "dftracer_agents"
    cap_dir: Path                         # where its capabilities live in its installed package
    prefixes: Tuple[str, ...] = ()        # capability names it owns by prefix
    names: Tuple[str, ...] = ()           # and by name
    root: bool = False                    # owns whatever no other scope claims (phronix)
    nested: bool = False                  # files capabilities under <topic>/<name> (phronix) rather than <name>


# The phronix scope: its bundled layer, capabilities under <topic>/<name>.
def phronix_scope() -> Scope:
    import phronix
    return Scope(project="phronix", package="phronix",
                 cap_dir=Path(phronix.__file__).resolve().parent / ".phronix" / "capabilities", root=True, nested=True)


# Where an unowned capability is filed inside phronix (by name prefix), so the bundled layer stays browsable.
TOPICS = (("workload_", "workloads"), ("software_", "software"), ("system_", "systems"), ("tools_", "tooling"),
          ("phronix_", "framework"))


def topic_for(name: str, meta: Optional[dict] = None) -> str:
    t = (meta or {}).get("topic")
    if t:
        return t
    for prefix, topic in TOPICS:
        if name.startswith(prefix):
            return topic
    return "framework"


def imported_packages(code: str) -> List[str]:
    """Top-level packages ``code`` imports (absolute imports only)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out += [a.name.split(".")[0] for a in n.names]
        elif isinstance(n, ast.ImportFrom) and not n.level and n.module:
            out.append(n.module.split(".")[0])
    return list(dict.fromkeys(out))


def owner(name: str, code: str, chain: Sequence[Scope]) -> Scope:
    """The scope a capability belongs to. ``chain`` is upstream first, this project last."""
    imported = set(imported_packages(code or ""))
    by_import = [s for s in chain if s.package in imported and not s.root]
    if by_import:
        return by_import[-1]
    for s in reversed(chain):
        if name in s.names or any(name.startswith(p) for p in s.prefixes):
            return s
    roots = [s for s in chain if s.root]
    return roots[0] if roots else chain[-1]


def find_bundles(root: Path) -> Iterable[Path]:
    """Every capability bundle (a directory holding capability.json) under ``root``, at any depth, not looking inside
    a bundle (its versions/ and docs/ are not capabilities)."""
    import os
    if not root.is_dir():
        return []
    out = []
    for top, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not d.startswith("."))
        if "capability.json" in files and Path(top) != root:
            out.append(Path(top))
            dirs[:] = []
    return out
