"""The layered knowledge store — where phronix reads from and writes to.

A self-learning framework distributed as a wheel has a problem the framework it
grew out of never had to solve. When everything you learn is written back into
``site-packages/phronix/.agents/``, that works beautifully for a contributor who
cloned the repo and ran ``pip install -e .`` — and silently destroys knowledge
for everyone else, because ``site-packages`` is not a git worktree and is
replaced wholesale on the next ``pip install -U``.

So the store is three layers, lowest precedence first:

=========  ==========================  ==========  =========================================
layer      root                        writable    who it travels to
=========  ==========================  ==========  =========================================
bundled    ``<pkg>/.agents``           only in a   everyone who installs phronix
                                       source
                                       checkout
user       ``~/.phronix``              yes         you, across all your projects
project    ``<project>/.phronix``      yes         everyone who clones YOUR project
=========  ==========================  ==========  =========================================

Later layers win on a name collision, so a project can override a bundled skill
by shadowing its name, and ``phronix diff`` can show what a project changed.

**Where a new lesson goes** (:func:`resolve_write_layer`) follows from who
should inherit it:

* Developing phronix itself (the bundled layer is inside a git worktree) →
  ``bundled``, so the lesson ships to every installer. This reproduces the
  contributor ergonomics of a single in-package store.
* Working in some other git project → ``project``, so the lesson is committed
  alongside the code it is about and reaches every teammate who clones it.
* Neither → ``user``, so it is at least not lost.

Promotion between layers is deliberate, never automatic: ``phronix contribute``
(see :mod:`phronix.contribute`) is what moves a project-local lesson up into the
bundled layer via a pull request, with a privacy scan in front of it.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

#: Precedence order, lowest first. Later layers shadow earlier ones by name.
LAYER_NAMES = ("bundled", "user", "project")

#: The content directories every layer may contain. A layer need not have all
#: of them; missing ones simply contribute nothing.
#:
#: ``verifiers`` is paired with the other three by design: every skill lesson,
#: capability and agent change is supposed to have a verifier that can check the
#: claim it makes. See :mod:`phronix.verification`.
CONTENT_DIRS = ("skills", "agents", "memory", "capabilities", "verifiers",
                "research")

#: Markers that identify the root of "the project I am working in". ``.phronix``
#: comes first so an explicitly-initialised project wins over an enclosing repo.
_PROJECT_MARKERS = (".phronix", ".git", "pyproject.toml", "package.json", "Cargo.toml", "go.mod")


@dataclass(frozen=True)
class Layer:
    """One tier of the knowledge store.

    Attributes:
        name: one of :data:`LAYER_NAMES`.
        root: the directory holding ``skills/``, ``agents/``, ``memory/``,
            ``capabilities/`` and this layer's ``privacy_patterns.yaml``.
        writable: whether new learning may be persisted here.
        shared: whether writing here reaches other people via version control.
            ``user`` is writable but not shared — that difference is why it is
            never the default write target when a project is available.
    """

    name: str
    root: Path
    writable: bool
    shared: bool

    def dir(self, kind: str) -> Path:
        """Path to one of :data:`CONTENT_DIRS` within this layer (may not exist)."""
        if kind not in CONTENT_DIRS:
            raise ValueError(f"unknown content dir {kind!r}; expected one of {CONTENT_DIRS}")
        return self.root / kind

    def ensure(self) -> "Layer":
        """Create this layer's directory skeleton. No-op for a read-only layer."""
        if not self.writable:
            return self
        for kind in CONTENT_DIRS:
            (self.root / kind).mkdir(parents=True, exist_ok=True)
        return self

    def exists(self) -> bool:
        return self.root.is_dir()


# ---------------------------------------------------------------------------
# Locating each layer
# ---------------------------------------------------------------------------

def bundled_root() -> Path:
    """``<package>/.agents`` — the knowledge that ships inside the wheel."""
    return Path(__file__).resolve().parent / ".agents"


def user_root() -> Path:
    """``~/.phronix``, or ``$PHRONIX_HOME`` when set."""
    override = os.environ.get("PHRONIX_HOME")
    return Path(override).expanduser().resolve() if override else Path.home() / ".phronix"


def project_root(start: Optional[Path] = None) -> Optional[Path]:
    """Find the working project's root by walking up from *start* (default cwd).

    Returns ``None`` when nothing looks like a project, which is the signal that
    the ``project`` layer does not apply — a user running phronix from their home
    directory has no repo for a lesson to travel with.
    """
    override = os.environ.get("PHRONIX_PROJECT_ROOT")
    if override:
        candidate = Path(override).expanduser().resolve()
        return candidate if candidate.is_dir() else None

    here = Path(start).resolve() if start else Path.cwd().resolve()
    for parent in (here, *here.parents):
        if any((parent / marker).exists() for marker in _PROJECT_MARKERS):
            return parent
    return None


def project_store(start: Optional[Path] = None) -> Optional[Path]:
    """``<project>/.phronix`` — the git-tracked, team-shared layer."""
    root = project_root(start)
    return (root / ".phronix") if root else None


def _in_git_worktree(path: Path) -> bool:
    """True when *path* lives inside a git worktree.

    This is how we tell "phronix was cloned and installed editable" (writes to
    the bundled layer are tracked, reviewable and shippable) from "phronix was
    pip-installed into site-packages" (writes there are invisible to git and
    evaporate on upgrade). Falls back to a cheap upward scan for ``.git`` when
    the git binary is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip() == "true"
    except (OSError, subprocess.SubprocessError):
        pass
    return any((parent / ".git").exists() for parent in (path, *path.parents))


def _writable(path: Path) -> bool:
    """Whether we could actually create files under *path*.

    Checks the nearest existing ancestor, because the layer directory itself
    usually does not exist yet on a first run.
    """
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return os.access(probe, os.W_OK)


def bundled_layer() -> Layer:
    root = bundled_root()
    developing = _in_git_worktree(root) and _writable(root)
    return Layer(name="bundled", root=root, writable=developing, shared=True)


def user_layer() -> Layer:
    root = user_root()
    return Layer(name="user", root=root, writable=_writable(root), shared=False)


def project_layer(start: Optional[Path] = None) -> Optional[Layer]:
    store = project_store(start)
    if store is None:
        return None
    return Layer(name="project", root=store, writable=_writable(store), shared=True)


def layers(start: Optional[Path] = None, include_missing: bool = False) -> List[Layer]:
    """Every applicable layer in precedence order (lowest first).

    By default a layer with no directory on disk is omitted, so callers merging
    content do not have to test for existence. Pass *include_missing* when you
    are reporting on the store (``phronix status``) rather than reading it.
    """
    found = [bundled_layer(), user_layer()]
    project = project_layer(start)
    if project is not None:
        found.append(project)
    if include_missing:
        return found
    return [layer for layer in found if layer.exists()]


def get_layer(name: str, start: Optional[Path] = None) -> Layer:
    """Look up a single layer by name. Raises ``ValueError`` if not applicable."""
    for layer in layers(start, include_missing=True):
        if layer.name == name:
            return layer
    raise ValueError(
        f"layer {name!r} is not available here "
        f"(known: {', '.join(l.name for l in layers(start, include_missing=True))})"
    )


# ---------------------------------------------------------------------------
# Choosing where to write
# ---------------------------------------------------------------------------

def _is_phronix_checkout(project: Optional[Layer]) -> bool:
    """True when the working project is the phronix source tree itself.

    Compared by containment rather than equality: the bundled root is
    ``<checkout>/src/phronix/.agents``, several levels below the project root.
    """
    if project is None:
        return False
    try:
        bundled_root().resolve().relative_to(project.root.parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def resolve_write_layer(explicit: Optional[str] = None, start: Optional[Path] = None) -> Layer:
    """Decide which layer a new lesson should be persisted to.

    Order of decision: an explicit argument, then ``$PHRONIX_WRITE_LAYER``, then
    the inheritance rule described in this module's docstring. A layer named
    explicitly but not writable is an error rather than a silent downgrade — an
    agent told to write to the bundled layer and quietly redirected to ``user``
    would report success for a lesson nobody else will ever see.
    """
    requested = explicit or os.environ.get("PHRONIX_WRITE_LAYER")
    if requested:
        layer = get_layer(requested, start)
        if not layer.writable:
            raise PermissionError(
                f"layer {layer.name!r} at {layer.root} is not writable. "
                "The bundled layer is only writable from a source checkout "
                "(clone phronix and `pip install -e .`); otherwise write to the "
                "'project' or 'user' layer."
            )
        return layer.ensure()

    project = project_layer(start)

    # The bundled layer is the default target ONLY when the project being worked
    # in IS the phronix checkout — i.e. you are developing phronix itself.
    #
    # "Bundled is writable" is not sufficient on its own. An editable install
    # (`pip install -e .` from a clone) leaves the bundled layer inside a git
    # worktree permanently, so a lesson learned while working on some OTHER
    # repository would be written into phronix's own tree — shipped to every
    # installer, and invisible in the repository it was actually about.
    bundled = bundled_layer()
    if bundled.writable and _is_phronix_checkout(project):
        return bundled.ensure()

    if project is not None and project.writable:
        return project.ensure()

    user = user_layer()
    if user.writable:
        return user.ensure()

    raise PermissionError("no writable phronix layer found (tried bundled, project, user)")


# ---------------------------------------------------------------------------
# Merged views over all layers
# ---------------------------------------------------------------------------

def merged_dirs(kind: str, start: Optional[Path] = None) -> Dict[str, Path]:
    """Merge the sub-DIRECTORIES of ``<layer>/<kind>/`` by name, later layers winning.

    Used for skills, where one skill is a directory containing ``SKILL.md`` and
    optional sibling reference files.
    """
    out: Dict[str, Path] = {}
    for layer in layers(start):
        base = layer.dir(kind)
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                out[child.name] = child
    return out


def merged_files(kind: str, pattern: str = "*", start: Optional[Path] = None) -> Dict[str, Path]:
    """Merge the FILES in ``<layer>/<kind>/`` matching *pattern*, later layers winning.

    Keyed on the filename, so a project's ``phronix-router.yaml`` shadows the
    bundled one entirely rather than merging field-by-field. Wholesale override
    is the right semantic here: a half-overridden agent prompt is far harder to
    reason about than a replaced one, and ``phronix diff`` can show what changed.
    """
    out: Dict[str, Path] = {}
    for layer in layers(start):
        base = layer.dir(kind)
        if not base.is_dir():
            continue
        for path in sorted(base.glob(pattern)):
            if path.is_file() and not path.name.startswith("."):
                out[path.name] = path
    return out


def skill_dirs(start: Optional[Path] = None) -> Dict[str, Path]:
    """All skills visible here: ``{skill_name: directory}``."""
    return merged_dirs("skills", start)


def agent_templates(start: Optional[Path] = None) -> Dict[str, Path]:
    """All agent YAML templates visible here, excluding the shared-section library."""
    found = merged_files("agents", "*.yaml", start)
    found.pop("common-sections.yaml", None)
    return found


def common_sections_files(start: Optional[Path] = None) -> List[Path]:
    """Every layer's ``common-sections.yaml``, lowest precedence first.

    Returned as a LIST rather than merged here because shared sections are the
    one thing that genuinely merges key-by-key: a project adding one standing
    rule must not have to restate the bundled library to keep it.
    """
    out: List[Path] = []
    for layer in layers(start):
        path = layer.dir("agents") / "common-sections.yaml"
        if path.is_file():
            out.append(path)
    return out


def memory_files(start: Optional[Path] = None) -> Dict[str, Path]:
    """All memory documents visible here, keyed by filename. ``MEMORY.md`` excluded."""
    found = merged_files("memory", "*.md", start)
    found.pop("MEMORY.md", None)
    return found


def capability_files(start: Optional[Path] = None) -> Dict[str, Path]:
    """Runtime-authored MCP tool modules, keyed by filename.

    These are the capabilities the framework *built for itself*: a session that
    turned a repeated manual procedure into deterministic code drops a module
    here and the MCP server loads it on the next start (see
    :func:`phronix.capabilities.load_all`).
    """
    return merged_files("capabilities", "*.py", start)


def verifier_files(start: Optional[Path] = None) -> Dict[str, Path]:
    """Verifier modules, keyed by filename.

    A verifier is the executable check paired with a piece of learning: it takes
    the claim a skill lesson, capability or agent change makes and answers whether
    that claim still holds. See :mod:`phronix.verification`.
    """
    return merged_files("verifiers", "*.py", start)


def which_layer(path: Path, start: Optional[Path] = None) -> Optional[str]:
    """Name the layer that *path* belongs to, or ``None`` if it is outside the store."""
    resolved = Path(path).resolve()
    best: Optional[str] = None
    best_len = -1
    for layer in layers(start, include_missing=True):
        root = layer.root.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        # Layers can nest (a project inside the phronix checkout); the deepest
        # containing root is the real owner.
        if len(str(root)) > best_len:
            best, best_len = layer.name, len(str(root))
    return best


def describe(start: Optional[Path] = None) -> List[Dict[str, object]]:
    """A status summary of every layer, for the CLI and the ``phronix_status`` tool."""
    out: List[Dict[str, object]] = []
    for layer in layers(start, include_missing=True):
        counts = {}
        for kind in CONTENT_DIRS:
            base = layer.dir(kind)
            if not base.is_dir():
                counts[kind] = 0
            elif kind == "skills":
                counts[kind] = sum(1 for p in base.iterdir() if p.is_dir())
            elif kind == "memory":
                counts[kind] = sum(1 for p in base.glob("*.md") if p.name != "MEMORY.md")
            elif kind in ("capabilities", "verifiers"):
                counts[kind] = len(list(base.glob("*.py")))
            else:
                counts[kind] = len([p for p in base.glob("*.yaml")
                                    if p.name != "common-sections.yaml"])
        out.append({
            "layer": layer.name,
            "root": str(layer.root),
            "exists": layer.exists(),
            "writable": layer.writable,
            "shared": layer.shared,
            "counts": counts,
        })
    return out


#: Directories and suffixes the content sweep skips. Compiled bytecode embeds the
#: absolute path it was built from, so scanning it reports a "leak" in a generated
#: binary nobody can edit and that is not committed — noise that buries the real
#: findings.
_SWEEP_SKIP_DIRS = {"__pycache__", ".git", ".mypy_cache", ".pytest_cache"}
_SWEEP_SKIP_SUFFIXES = {".pyc", ".pyo", ".so", ".png", ".jpg", ".jpeg", ".gif",
                        ".pdf", ".zip", ".gz", ".tar", ".whl"}


def iter_all_content(start: Optional[Path] = None) -> Iterable[Path]:
    """Every reviewable content file across every layer — used by the privacy sweep.

    Restricted to text that a person could actually edit and commit. The sweep
    exists so a human can act on what it reports; a finding inside a ``.pyc`` is
    not actionable.
    """
    def _wanted(path: Path, base: Path) -> bool:
        if path.suffix in _SWEEP_SKIP_SUFFIXES:
            return False
        try:
            parts = path.relative_to(base).parts
        except ValueError:
            return False
        return not any(part in _SWEEP_SKIP_DIRS for part in parts)

    for layer in layers(start):
        for kind in CONTENT_DIRS:
            base = layer.dir(kind)
            if base.is_dir():
                yield from (p for p in base.rglob("*")
                            if p.is_file() and _wanted(p, base))
        patterns = layer.root / "privacy_patterns.yaml"
        if patterns.is_file():
            yield patterns
