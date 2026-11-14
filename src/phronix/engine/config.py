"""Which project the engine serves in this process, and where its capabilities come from and go to.

One process serves one project (phronix itself, dftracer-agents, moirai-agents, rabbit-agent, ...). The project calls
:func:`configure` once, before it uses the engine, with its package's capabilities directory, its environment prefix,
its own :class:`~phronix.engine.scopes.Scope` and the scopes upstream of it (phronix first):

    from phronix.engine import configure
    from phronix.engine.scopes import Scope, phronix_scope
    configure(project="dftracer-agents", env_prefix="DFTRACER_AGENTS", package_dir=PKG,
              scope=Scope("dftracer-agents", "dftracer_agents", PKG / ".agents" / "capabilities", prefixes=("dftracer_",)),
              upstream=[phronix_scope()])

It then loads its own capabilities over those of everything upstream, and every change it makes to a capability is
written where that capability belongs: its own package for its own, the contribution worktree of the owning upstream
for the rest (:mod:`phronix.engine.upstream`), committed there after the change.

Environment, with <P> the prefix: <P>_BUNDLED_CAPABILITIES, <P>_PROJECT_CAPABILITIES, <P>_USER_CAPABILITIES (layers,
for tests), <P>_LEARNING_DIR (lessons and proposals), <P>_PIPELINES_DIR, <P>_USER (who approves), <P>_HOME (state).
"""
from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Callable, List, Optional

from .scopes import Scope


class Settings:
    project = "phronix"
    env_prefix = "PHRONIX"
    package_dir: Optional[Path] = None        # the project's package: <package_dir>/.agents/capabilities is its store
    project_root: Optional[Path] = None       # its checkout (vendor/ lives here)
    state_dir: Optional[Callable[..., Path]] = None
    module_prefix = "phronix"                 # names of the modules capabilities are loaded as
    context_tag = "capability-context"        # the tag knowledge.context wraps its hits in
    bootstrap = ""                            # "module" or "module:function" that configures the engine (run in check sandboxes)
    agent: Optional[Callable[[], Optional[str]]] = None   # the merge agent's executable (Claude Code), when the project knows it
    scope: Optional[Scope] = None             # this project's scope
    upstream: List[Scope] = []                # the scopes it builds on, phronix first
    configured = False


S = Settings()


def configure(project: str, env_prefix: str, package_dir, state_dir: Optional[Callable[..., Path]] = None,
              module_prefix: str = "", context_tag: str = "", standing: str = "", shared_agent_tools: Optional[List[str]] = None,
              trace_rule: str = "", trace_reader: Optional[str] = None, bootstrap: str = "",
              scope: Optional[Scope] = None, upstream: Optional[List[Scope]] = None, project_root=None,
              store: Optional[Path] = None, agent: Optional[Callable[[], Optional[str]]] = None) -> Settings:
    """Set the project this process serves. ``standing`` / ``shared_agent_tools`` / ``trace_rule`` / ``trace_reader``
    replace the engine's defaults (capstore.STANDING, SHARED_AGENT_TOOLS, TV_RULE, TRACE_READER) for this project.
    ``bootstrap`` names what configures the engine for this project ("module" or "module:function"); a check sandbox
    imports it first. ``store`` is the project's own capabilities directory (default <package_dir>/.agents/capabilities)."""
    from . import capstore
    S.project, S.env_prefix = project, env_prefix.rstrip("_")
    S.package_dir = Path(package_dir).resolve()
    S.state_dir = state_dir
    S.module_prefix = module_prefix or project.split("-")[0].replace("-", "_")
    S.context_tag = context_tag or f"{S.module_prefix}-context"
    S.bootstrap = bootstrap
    own = Path(store).resolve() if store else S.package_dir / ".agents" / "capabilities"
    S.scope = scope or Scope(project=project, package=S.package_dir.name, cap_dir=own)
    S.upstream = list(upstream or [])
    S.agent = agent
    S.project_root = Path(project_root).resolve() if project_root else _checkout(S.package_dir)
    S.configured = True
    capstore.PKG = S.package_dir
    capstore.BUNDLED = own
    if standing:
        capstore.STANDING = standing
    if shared_agent_tools is not None:
        capstore.SHARED_AGENT_TOOLS = list(shared_agent_tools)
    if trace_rule:
        capstore.TV_RULE = trace_rule
    if trace_reader is not None:
        capstore.TRACE_READER = trace_reader
    capstore._State.fingerprint = ""
    return S


def _checkout(package_dir: Path) -> Path:
    for p in [package_dir, *package_dir.parents]:
        if (p / ".git").exists() or (p / "pyproject.toml").exists():
            return p
    return package_dir.parent


def chain() -> List[Scope]:
    """Upstream first, this project last."""
    return [*S.upstream, *([S.scope] if S.scope else [])]


def agent_bin() -> Optional[str]:
    """The agent that merges a conflicted rebase (Claude Code): the project's own finder, <P>_CLAUDE_BIN, or claude on
    PATH or in ~/.local/bin."""
    import shutil
    if S.agent is not None:
        try:
            found = S.agent()
        except Exception:
            found = None
        if found:
            return found
    for cand in (env("CLAUDE_BIN"), shutil.which("claude"), str(Path.home() / ".local" / "bin" / "claude")):
        if cand and Path(cand).is_file() and os.access(cand, os.X_OK):
            return cand
    return None


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    """<prefix>_<name> from the environment."""
    return os.environ.get(f"{S.env_prefix}_{name}", default)


def env_name(name: str) -> str:
    return f"{S.env_prefix}_{name}"


def state_dir(*parts: str) -> Path:
    """The project's state directory (lessons, proposals): its own state_dir, else <P>_HOME, else ~/.<project>."""
    if S.state_dir is not None:
        return Path(S.state_dir(*parts))
    base = env("HOME") or str(Path.home() / f".{S.project}")
    return Path(base).expanduser().joinpath(*parts)


def shared_change(what: str, describe=None):
    """Decorate an operation that changes capabilities or lessons. What it wrote for a capability another project owns
    went into that project's contribution worktree (capstore.write_dir); afterwards it is committed there, on this
    project's contribution branch, with a message naming what was done. Nothing is pushed: see upstream.update."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            out = fn(*args, **kwargs)
            if S.upstream:
                msg = f"{what} {args[0] if args else ''}".strip()
                if describe is not None:
                    try:
                        msg = describe(out, args, kwargs)
                    except Exception:           # the commit message is best effort
                        pass
                try:
                    from .upstream import commit_pending
                    committed = commit_pending(f"{S.project}: {msg}")
                    if committed and isinstance(out, dict):
                        out = {**out, "contributed": committed}
                except Exception as e:          # never lose the change itself over the commit
                    if isinstance(out, dict):
                        out = {**out, "contribution_error": f"{type(e).__name__}: {e}"}
            return out
        return wrapper
    return deco


scoped_change = shared_change
