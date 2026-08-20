"""Graph context: locate code and knowledge instead of reading it.

The dominant token cost in an agentic session is *input* — the source and
documents an agent reads to orient itself. ``graphify`` builds a tree-sitter
graph over code (C/C++/Fortran/Python/…) **plus markdown headings**, so an agent
can ask "where is X" and get ``file:line`` back for a couple of hundred tokens
instead of tens of thousands.

Two graphs, two lifetimes:

**knowledge**
    The layered store itself — every skill, agent template and memory phronix can
    see, plus phronix's own source. Answers "which skill covers this", "what does
    the self-healing rule actually say", "what breaks if I change this helper".
    This is what makes ``graph_query(mode="docs")`` a cheaper ``skill_load``.

**project**
    The tree the user is actually working in. Answers the same questions about
    their code without reading their repo into context.

Deployment constraints this module works around — all of them observed, none
guessable from the docs:

1. ``graphify`` writes to ``<scanned_path>/graphify-out`` and has no ``--out``
   flag. Scanning an installed package would drop build artifacts inside
   ``site-packages``, which ``pip uninstall`` never removes. So the knowledge
   graph is built over a **staged copy** in a cache directory.
2. ``graphify`` does **not** follow symlinked directories — and the layered store
   is presented to harnesses through symlinks. The stage must contain real files.
3. A markdown-only tree yields no graph at all; markdown headings are only
   extracted when code files are present in the same tree. The stage therefore
   carries both, which is convenient here since the store and the source belong
   together anyway.
4. ``graphify`` honours ``.gitignore``, and a cache under an ignored directory
   scans to zero nodes. A ``.graphifyignore`` with negations at the scan root
   re-includes it (last-match-wins, same semantics as gitignore).
5. Skills and memory are self-updating: the graph rots *during* a session.
   Freshness is keyed on a content hash of the staged inputs plus a dirty flag
   any writer can set — see :func:`mark_dirty`, called by ``memory.write`` and
   ``skills.write_lesson``.

A rebuild costs a few seconds, needs no LLM and no API key, so the freshness
check that looks expensive is in fact free.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

#: Files worth graphing. Everything else is noise or unparseable.
SRC_SUFFIXES = (
    ".py", ".md", ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".hh",
    ".f90", ".F90", ".rs", ".go", ".js", ".ts", ".tsx", ".java",
)

#: Never staged: build artifacts, caches, and graphify's own output.
SKIP_DIRS = {
    "__pycache__", ".git", "graphify-out", "build", "dist", ".venv", "venv",
    "site-packages", ".pytest_cache", "node_modules", ".mypy_cache", ".tox",
    ".phronix-cache", "target",
}

#: Negations that re-include the graph cache. ``graphify`` merges ``.gitignore``
#: and ``.graphifyignore`` per directory, last match wins.
_GRAPHIFYIGNORE_MARK = "# phronix: re-include the knowledge-graph stage"
_GRAPHIFYIGNORE_BODY = f"""{_GRAPHIFYIGNORE_MARK}
# graphify honours .gitignore. The stage lives in a cache directory that is
# routinely ignored, and would otherwise scan to "No code files found".
!stage/
!stage/**
"""

_LOC_RE = re.compile(r"L(\d+)")
_PATH_RE = re.compile(r"(?<![\w/])((?:[\w.-]+/)*[\w.-]+\.[A-Za-z0-9]{1,4})(?![\w/])")

#: Query words that carry no retrieval signal. Deliberately includes the
#: interrogatives, because agents ask these tools questions in natural language
#: and every one of those words would otherwise match somewhere in every section.
_STOPWORDS = frozenset("""
and are but for from has have how not the that this was were what when where why
with you your can will its about into than then they there their use using does
did done should would could must need needs any all one two get got make made
""".split())


class GraphUnavailable(RuntimeError):
    """``graphify`` is not installed, or produced no graph."""


# ---------------------------------------------------------------------------
# Cache locations
# ---------------------------------------------------------------------------

def cache_root() -> Path:
    """Writable cache for staged copies and graph output.

    Never inside the package: a wheel install's ``site-packages`` may be
    read-only, and artifacts written there survive ``pip uninstall`` forever.
    """
    override = os.environ.get("PHRONIX_CACHE")
    if override:
        root = Path(override).expanduser()
    else:
        base = os.environ.get("XDG_CACHE_HOME")
        root = (Path(base).expanduser() if base else Path.home() / ".cache") / "phronix"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _graph_dir(name: str) -> Path:
    path = cache_root() / "graph" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_path(name: str) -> Path:
    return _graph_dir(name) / "state.json"


def _dirty_path(name: str) -> Path:
    return _graph_dir(name) / "dirty"


def mark_dirty(reason: str = "", name: str = "knowledge") -> None:
    """Flag a graph stale. Call after writing a skill, memory or capability.

    Cheap and idempotent; the next ``ensure``/``query`` rebuilds. Content hashing
    already catches edits made through the filesystem, so this exists purely so
    an in-process writer does not have to wait for the next hash sweep to make
    the thing it just wrote findable.
    """
    try:
        _dirty_path(name).write_text(f"{time.time()}\n{reason}\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Staging and freshness
# ---------------------------------------------------------------------------

def _iter_sources(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in SRC_SUFFIXES:
            continue
        try:
            parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in SKIP_DIRS for part in parts):
            continue
        yield path


def _content_hash(roots: List[Path]) -> str:
    """Hash the path and content of every graphable file across *roots*.

    Content, not mtime: a ``git checkout`` or a reinstall rewrites mtimes without
    changing anything, and a spurious rebuild on every checkout would make the
    freshness check worse than useless.
    """
    digest = hashlib.sha256()
    for root in roots:
        if not root.is_dir():
            continue
        digest.update(f"\x00root:{root.name}\x00".encode())
        for path in sorted(_iter_sources(root)):
            digest.update(str(path.relative_to(root)).encode())
            try:
                digest.update(path.read_bytes())
            except OSError:
                continue
    return digest.hexdigest()


def _stage(roots: Dict[str, Path], stage: Path) -> int:
    """Copy graphable files into *stage* as REAL files (symlinks are not followed).

    Each root lands under its own subdirectory so that two layers holding a
    same-named skill do not overwrite each other in the stage — which would make
    the graph describe a file that no longer exists in the merged view.
    """
    if stage.exists():
        shutil.rmtree(stage)
    count = 0
    for prefix, root in roots.items():
        if not root.is_dir():
            continue
        for path in _iter_sources(root):
            dest = stage / prefix / path.relative_to(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(path, dest)
                count += 1
            except OSError:
                continue
    return count


def _ensure_graphifyignore(scan_root: Path) -> None:
    path = scan_root / ".graphifyignore"
    try:
        if path.is_file() and _GRAPHIFYIGNORE_MARK in path.read_text():
            return
        path.write_text(_GRAPHIFYIGNORE_BODY)
    except OSError:
        pass


def _graphify(*args: str, timeout: int = 900) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["graphify", *args], capture_output=True,
                              text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise GraphUnavailable(
            "the `graphify` CLI is not on PATH. It ships with phronix's "
            "`graphifyy` dependency — reinstall with `pip install -U phronix`."
        ) from exc


def _node_count(graph_json: Path) -> int:
    try:
        return len(json.loads(graph_json.read_text()).get("nodes", []))
    except Exception:
        return 0


def _knowledge_roots() -> Dict[str, Path]:
    """What the knowledge graph indexes: every layer's store, plus phronix itself."""
    from phronix.layers import CONTENT_DIRS, layers

    roots: Dict[str, Path] = {"phronix": Path(__file__).resolve().parent}
    for layer in layers():
        for kind in CONTENT_DIRS:
            directory = layer.dir(kind)
            if directory.is_dir():
                roots[f"{layer.name}-{kind}"] = directory
    return roots


def ensure_knowledge_graph(force: bool = False) -> Dict[str, Any]:
    """Rebuild the knowledge graph iff its inputs changed, or it was marked dirty."""
    name = "knowledge"
    root = _graph_dir(name)
    stage = root / "stage"
    graph_json = stage / "graphify-out" / "graph.json"

    roots = _knowledge_roots()
    digest = _content_hash(list(roots.values()))

    state: Dict[str, Any] = {}
    if _state_path(name).exists():
        try:
            state = json.loads(_state_path(name).read_text())
        except Exception:
            state = {}

    dirty = _dirty_path(name).exists()
    if not force and not dirty and state.get("hash") == digest and graph_json.exists():
        return {"rebuilt": False, "reason": "up to date", "graph": str(graph_json),
                "nodes": state.get("nodes", 0), "roots": {k: str(v) for k, v in roots.items()}}

    staged = _stage(roots, stage)
    _ensure_graphifyignore(root)
    if staged == 0:
        return {"rebuilt": False, "error": "nothing graphable found in the knowledge store",
                "roots": {k: str(v) for k, v in roots.items()}}

    result = _graphify("update", str(stage), "--no-cluster")
    if not graph_json.exists():
        return {"rebuilt": False, "error": "graphify produced no graph",
                "staged_files": staged, "stderr": (result.stderr or result.stdout)[-400:]}

    nodes = _node_count(graph_json)
    _state_path(name).write_text(json.dumps({
        "hash": digest, "nodes": nodes, "staged_files": staged,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }, indent=2) + "\n")
    try:
        _dirty_path(name).unlink(missing_ok=True)
    except OSError:
        pass
    return {"rebuilt": True,
            "reason": "forced" if force else ("dirty flag" if dirty else "inputs changed"),
            "graph": str(graph_json), "nodes": nodes, "staged_files": staged}


def ensure_project_graph(root: Optional[Path] = None, force: bool = False) -> Dict[str, Any]:
    """Build the working project's graph.

    Staged into the cache rather than scanned in place, for the same reason as
    the knowledge graph: dropping a ``graphify-out/`` directory into someone
    else's repo is a side effect they did not ask for.
    """
    from phronix.layers import project_root

    source = Path(root).resolve() if root else project_root()
    if source is None:
        return {"rebuilt": False, "error": "no project root detected; pass an explicit path"}

    name = "project-" + hashlib.sha256(str(source).encode()).hexdigest()[:12]
    cache = _graph_dir(name)
    stage = cache / "stage"
    graph_json = stage / "graphify-out" / "graph.json"

    digest = _content_hash([source])
    state: Dict[str, Any] = {}
    if _state_path(name).exists():
        try:
            state = json.loads(_state_path(name).read_text())
        except Exception:
            state = {}

    dirty = _dirty_path(name).exists()
    if not force and not dirty and state.get("hash") == digest and graph_json.exists():
        return {"rebuilt": False, "reason": "up to date", "graph": str(graph_json),
                "nodes": state.get("nodes", 0), "source": str(source)}

    staged = _stage({".": source}, stage)
    _ensure_graphifyignore(cache)
    if staged == 0:
        return {"rebuilt": False, "error": f"no graphable files under {source}"}

    result = _graphify("update", str(stage), "--no-cluster")
    if not graph_json.exists():
        return {"rebuilt": False, "error": "graphify produced no graph",
                "staged_files": staged, "stderr": (result.stderr or result.stdout)[-400:]}

    nodes = _node_count(graph_json)
    _state_path(name).write_text(json.dumps({
        "hash": digest, "nodes": nodes, "staged_files": staged, "source": str(source),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }, indent=2) + "\n")
    try:
        _dirty_path(name).unlink(missing_ok=True)
    except OSError:
        pass
    return {"rebuilt": True, "graph": str(graph_json), "nodes": nodes,
            "staged_files": staged, "source": str(source)}


def ensure(scope: str = "knowledge", root: Optional[Path] = None,
           force: bool = False) -> Dict[str, Any]:
    """Freshen the graph for *scope* (``knowledge`` or ``project``)."""
    if scope == "project":
        return ensure_project_graph(root, force)
    if scope == "knowledge":
        return ensure_knowledge_graph(force)
    return {"rebuilt": False, "error": f"unknown scope {scope!r} (knowledge|project)"}


# ---------------------------------------------------------------------------
# Reading the graph
# ---------------------------------------------------------------------------

def load_nodes(graph: str) -> List[Dict[str, Any]]:
    with open(graph, encoding="utf-8") as handle:
        return json.load(handle).get("nodes", [])


def _stage_root(graph: str) -> Path:
    """The directory the graph's ``source_file`` paths are relative to."""
    return Path(graph).parents[1]


def _real_path(stage_root: Path, rel: str, scope: str) -> str:
    """Map a stage-relative path back to a real, openable file.

    The graph is built over a copy, so every ``source_file`` is stage-relative.
    Handing an agent ``bundled-skills/foo/SKILL.md`` sends it to a path that does
    not exist. Reverse the staging prefix; if that fails, return the stage path
    rather than inventing one — a wrong-but-plausible path costs more than an
    ugly-but-true one.
    """
    if scope == "project":
        from phronix.layers import project_root

        base = project_root()
        if base is not None:
            candidate = base / rel
            if candidate.exists():
                return str(candidate)
        return str(stage_root / rel)

    parts = Path(rel).parts
    if parts:
        roots = _knowledge_roots()
        origin = roots.get(parts[0])
        if origin is not None:
            candidate = origin.joinpath(*parts[1:])
            if candidate.exists():
                return str(candidate)
    return str(stage_root / rel)


def _rewrite_paths(output: str, stage_root: Path, scope: str) -> str:
    """Rewrite stage-relative paths in graphify's own output back to real ones."""
    def substitute(match: "re.Match") -> str:
        return _real_path(stage_root, match.group(1), scope)

    return _PATH_RE.sub(substitute, output)


def _node_line(node: Dict[str, Any]) -> int:
    match = _LOC_RE.search(str(node.get("source_location") or ""))
    return int(match.group(1)) if match else 1


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _header_end(lines: List[str], start: int) -> int:
    """0-indexed line closing the definition header that begins at 1-indexed *start*.

    A multi-line signature ends at the ``:`` closing it at bracket depth 0 — not
    at the first dedent, because ``) -> bool:`` sits at the same indent as its own
    ``def``. Scans at most 40 lines; a header longer than that is not a header.
    """
    depth = 0
    for i in range(start - 1, min(start + 39, len(lines))):
        for char in lines[i]:
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
        if depth <= 0 and lines[i].rstrip().endswith(":"):
            return i
    return start - 1


def _code_end(lines: List[str], start: int) -> int:
    """End of the definition beginning at 1-indexed *start*, found by dedent.

    The next graph node in the file is NOT a usable end: graphify emits nodes for
    nested definitions too, so a method containing an inner function would
    truncate to its own signature. Scan past the header, then take the first
    non-blank line indented no deeper than the definition itself.
    """
    base = _indent(lines[start - 1])
    for i in range(_header_end(lines, start) + 1, len(lines)):
        line = lines[i]
        if line.strip() and _indent(line) <= base:
            return i
    return -1


def _doc_end(nodes: List[Dict[str, Any]], node: Dict[str, Any]) -> int:
    """End of a markdown section: the line before the next heading in the same file.

    graphify emits one node per heading with a start line and no end, so the next
    heading is exactly where this section stops.
    """
    source, start = node.get("source_file"), _node_line(node)
    later = [_node_line(n) for n in nodes
             if n.get("source_file") == source and _node_line(n) > start]
    return min(later) - 1 if later else -1


def read_span(stage_root: Path, node: Dict[str, Any], nodes: List[Dict[str, Any]],
              max_lines: int = 200) -> Tuple[str, int, int, bool]:
    """Extract the text *node* owns, choosing the end rule by node type."""
    path = stage_root / node["source_file"]
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = _node_line(node)
    if start > len(lines):
        raise OSError(f"node starts at L{start} but the file has {len(lines)} lines "
                      "— stale graph; rebuild with force=True")

    if node.get("label") == Path(node["source_file"]).name:
        end = -1  # the node IS the file (graphify emits one per file at L1)
    elif node.get("file_type") == "document":
        end = _doc_end(nodes, node)
    else:
        end = _code_end(lines, start)

    stop = len(lines) if end < 0 else min(end, len(lines))
    body = lines[start - 1:stop]
    truncated = len(body) > max_lines
    return "\n".join(body[:max_lines]), start, stop, truncated


def _score(node: Dict[str, Any], terms: List[str]) -> int:
    hay = f"{node.get('label', '')} {node.get('source_file', '')}".lower()
    return sum(1 for term in terms if term in hay)


def query(
    question: str = "",
    mode: str = "query",
    symbol: str = "",
    budget: int = 1200,
    depth: int = 2,
    scope: str = "knowledge",
    root: Optional[Path] = None,
    context: Optional[List[str]] = None,
    limit: int = 12,
) -> Dict[str, Any]:
    """Locate code and documents without reading them. Freshens the graph first.

    Modes:

    ``query``
        BFS for *question*; returns ``NODE <sym> [src=file loc=Lnn]``. Open only
        the files it names. Budget-capped.
    ``docs``
        Search only markdown nodes — skills, agent templates, memory. Use this
        instead of ``skill_load`` on a whole skill. A plain BFS ``query`` leaks
        into the code subgraph and buries headings under generic helpers, so
        document search is a separate, ranked path rather than a filter on the
        BFS results.
    ``explain``
        Definition, callers and callees of *symbol*.
    ``affected``
        Reverse traversal: everything impacted by changing *symbol*. Run this
        before editing any shared function and state the blast radius.
    """
    ensured = ensure(scope, root, force=False)
    if ensured.get("error"):
        return {"status": "error", **ensured}
    graph = ensured["graph"]
    stage_root = _stage_root(graph)
    mode = mode.strip().lower()

    if mode == "docs":
        if not question:
            return {"status": "error", "error": "mode='docs' needs a question"}
        terms = [t for t in re.split(r"\W+", question.lower()) if len(t) > 2]
        if not terms:
            return {"status": "error", "error": "mode='docs' needs a term longer than 2 chars"}
        docs = [n for n in load_nodes(graph) if n.get("file_type") == "document"]
        ranked = sorted(((_score(n, terms), n) for n in docs), key=lambda p: -p[0])
        hits = [(s, n) for s, n in ranked if s > 0][:limit]
        if not hits:
            return {"status": "no_match", "error": f"no document node matches {question!r}",
                    "graph": graph}
        lines = [
            f"NODE {n['label']} [id={n['id']} "
            f"src={_real_path(stage_root, n['source_file'], scope)} "
            f"loc={n.get('source_location')} score={s}]"
            for s, n in hits
        ]
        lines.append("\nFetch any of these with graph_get_node(node=<id>).")
        return {"status": "ok", "output": "\n".join(lines), "graph": graph,
                "rebuilt": ensured.get("rebuilt", False)}

    if mode == "query":
        if not question:
            return {"status": "error", "error": "mode='query' needs a question"}
        args = ["query", question, "--budget", str(budget), "--graph", graph]
        for entry in context or []:
            args += ["--context", entry]
    elif mode == "explain":
        if not symbol:
            return {"status": "error", "error": "mode='explain' needs a symbol"}
        args = ["explain", symbol, "--graph", graph]
    elif mode == "affected":
        if not symbol:
            return {"status": "error", "error": "mode='affected' needs a symbol"}
        args = ["affected", symbol, "--depth", str(depth), "--graph", graph]
    else:
        return {"status": "error", "error": f"unknown mode {mode!r} (query|docs|explain|affected)"}

    try:
        result = _graphify(*args, timeout=180)
    except GraphUnavailable as exc:
        return {"status": "error", "error": str(exc)}
    except subprocess.TimeoutExpired:
        return {"status": "error",
                "error": "graphify timed out; narrow the question or lower the budget"}

    output = (result.stdout or "").strip()
    if not output:
        return {"status": "no_match",
                "error": f"no result (graphify said: {(result.stderr or '').strip()[-200:]})",
                "graph": graph}
    return {"status": "ok", "output": _rewrite_paths(output, stage_root, scope),
            "graph": graph, "rebuilt": ensured.get("rebuilt", False)}


#: Which staged sub-tree each retrieval store corresponds to. The knowledge graph
#: stages every layer's content under ``<layer>-<kind>/``, so the first path
#: component is exactly the filter needed to search one store and not the others.
_STORE_SUFFIX = {
    "skills": "-skills",
    "memory": "-memory",
    "lessons": "-skills",   # LESSONS.md lives inside the skill directory
    "agents": "-agents",
    "capabilities": "-capabilities",
    "verifiers": "-verifiers",
}

#: Stores that additionally require a specific filename. A skill directory holds
#: both ``SKILL.md`` (how to do it) and ``LESSONS.md`` (what went wrong), and the
#: two are retrieved by different tools answering different questions — so the
#: staging prefix alone is not enough to tell them apart.
_STORE_FILENAME = {
    "skills": "SKILL.md",
    "lessons": "LESSONS.md",
}


def _in_store(node: Dict[str, Any], store: str) -> bool:
    if store in ("", "all"):
        return True
    suffix = _STORE_SUFFIX.get(store)
    if suffix is None:
        return True
    source = str(node.get("source_file", ""))
    parts = Path(source).parts
    if not parts or not parts[0].endswith(suffix):
        return False
    filename = _STORE_FILENAME.get(store)
    return filename is None or Path(source).name == filename


def find_docs(
    question: str,
    store: str = "all",
    limit: int = 8,
    max_lines: int = 60,
    with_text: bool = True,
    force: bool = False,
    restrict_to: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Rank markdown headings within ONE store and return the sections themselves.

    This is the retrieval primitive behind skill-finding and memory-finding. It
    differs from :func:`query` in two ways that matter:

    * **It is scoped to one store.** Searching skills and memory together buries
      the answer: they are different questions ("how do I do this" versus "what
      went wrong last time"), and mixing them means the stronger lexical match
      wins regardless of which question was asked.
    * **It returns the section TEXT, not just a pointer.** A pointer costs a
      second round trip, and in practice an agent handed a ``file:line`` for a
      skill section will often just load the whole skill instead. Returning the
      slice directly is what makes "never load a whole skill" a realistic rule
      rather than an aspiration.
    """
    ensured = ensure("knowledge", force=force)
    if ensured.get("error"):
        return {"status": "error", **ensured}
    graph = ensured["graph"]
    stage_root = _stage_root(graph)

    # Stopwords are dropped, not just short tokens. Agents phrase these queries
    # as questions ("how do I ...", "what happens when ..."), and scoring "how"
    # and "when" against every section swamps the one term that carries the
    # meaning — the retrieval equivalent of matching on punctuation.
    terms = [t for t in re.split(r"\W+", question.lower())
             if len(t) > 2 and t not in _STOPWORDS]
    if not terms:
        return {"status": "error",
                "error": f"no usable terms in {question!r} — it is all stopwords or "
                         "short tokens; name the thing you are looking for"}

    nodes = load_nodes(graph)
    docs = [n for n in nodes
            if n.get("file_type") == "document" and _in_store(n, store)]
    if restrict_to:
        # Phase two of index-first search: the Index has already chosen the
        # subjects, so the graph pass only has to find the right section INSIDE
        # them. Without this the graph would happily re-open the whole library and
        # undo the narrowing the index just did.
        wanted = {name.lower() for name in restrict_to}
        docs = [n for n in docs if _artifact_of(str(n.get("source_file", ""))).lower() in wanted]
    if not docs:
        return {"status": "no_match",
                "error": (f"nothing indexed in the {store!r} store"
                          + (f" for {restrict_to}" if restrict_to else "")),
                "graph": graph}
    docs = _prefer_sections(docs)

    # Score on the section BODY as well as its heading. Heading-only scoring puts
    # a generic `## Lessons` heading above the section that actually answers the
    # question, purely because the word "lesson" appeared in the query — bodies
    # are where the content lives, and a heading is one line of it.
    cache: Dict[str, List[str]] = {}
    scored: List[Tuple[float, Dict[str, Any], Any]] = []
    for node in docs:
        span = _span_cached(stage_root, node, docs, cache)
        body = "\n".join(span[0]) if span else ""
        scored.append((_score_doc(node, terms, body), node, span))

    ranked = sorted(scored, key=lambda t: (-t[0], str(t[1].get("label", ""))))
    hits = [entry for entry in ranked if entry[0] > 0][:limit]
    if not hits:
        return {"status": "no_match",
                "error": f"nothing in {store!r} matches {question!r}",
                "graph": graph}

    results: List[Dict[str, Any]] = []
    for score, node, span in hits:
        entry: Dict[str, Any] = {
            "id": node.get("id"),
            "heading": node.get("label"),
            "source_file": _real_path(stage_root, node["source_file"], "knowledge"),
            "location": node.get("source_location"),
            "score": round(score, 2),
            # The owning artifact: `<layer>-<kind>/<artifact>/SKILL.md` for a
            # skill, `<layer>-<kind>/<name>.md` for a memory.
            "artifact": _artifact_of(node["source_file"]),
        }
        if with_text:
            if span is None:
                entry["error"] = "could not read section"
            else:
                lines, start, stop = span
                entry.update({"text": "\n".join(lines[:max_lines]),
                              "lines": f"L{start}-L{stop}",
                              "truncated": len(lines) > max_lines})
        results.append(entry)

    return {"status": "ok", "store": store, "count": len(results),
            "results": results, "graph": graph,
            "rebuilt": ensured.get("rebuilt", False)}


def _span_cached(stage_root: Path, node: Dict[str, Any], nodes: List[Dict[str, Any]],
                 cache: Dict[str, List[str]]):
    """Read a node's FULL section, caching each file's lines across the ranking pass.

    Returns ``(lines, start, stop)`` untruncated. Scoring must see the whole
    section — truncating first would score a section on however many lines the
    caller happened to ask for, so a small ``max_lines`` would make sections look
    empty and rank them at zero.

    The cache matters: scoring every section means touching each source file once
    per section it contains, so without it this is O(sections) reads of the same
    handful of files.
    """
    source = str(node.get("source_file", ""))
    lines = cache.get(source)
    if lines is None:
        try:
            lines = (stage_root / source).read_text(
                encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []
        cache[source] = lines
    if not lines:
        return None

    start = _node_line(node)
    if start > len(lines):
        return None
    end = -1 if node.get("label") == Path(source).name else _doc_end(nodes, node)
    stop = len(lines) if end < 0 else min(end, len(lines))
    return lines[start - 1:stop], start, stop


def _is_file_node(node: Dict[str, Any]) -> bool:
    """True for the whole-document node graphify emits at L1 of every file."""
    return node.get("label") == Path(str(node.get("source_file", ""))).name


def _prefer_sections(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop whole-file nodes for any file that also has heading nodes.

    A file node spans the entire document, so returning one *is* loading the whole
    skill — precisely what these tools exist to avoid. It also outranks every real
    section for free, because it contains all of their text at once.

    Files with no ``## `` headings keep their file node: for a short memory that
    is genuinely the right unit, and dropping it would make the document
    unreachable rather than merely expensive.
    """
    with_sections = {
        str(node.get("source_file", "")) for node in docs if not _is_file_node(node)
    }
    return [node for node in docs
            if not (_is_file_node(node) and str(node.get("source_file", "")) in with_sections)]


def _section_body(span_text: str) -> str:
    """The section's text with its own heading line removed."""
    lines = span_text.split("\n", 1)
    return lines[1] if len(lines) > 1 and lines[0].lstrip().startswith("#") else span_text


#: Field weights for document ranking. A heading hit is a much stronger signal
#: than a body hit, but a body hit is not zero — which is the whole correction.
_W_HEADING = 6.0
_W_ARTIFACT = 4.0
_W_BODY = 1.0
_BODY_TF_CAP = 4


def _score_doc(node: Dict[str, Any], terms: List[str], body: str) -> float:
    """Weighted heading/artifact/body match, scaled by how much of the query is covered.

    Coverage dominates raw frequency for the same reason it does in memory
    retrieval: a section matching 3 of 3 query terms once each answers the
    question better than one matching a single term twenty times.

    An EMPTY section scores zero regardless of its heading. Every skill ends with
    a bare ``## Lessons`` placeholder waiting for its first entry, and on heading
    weight alone those nine identical placeholders outranked every section with
    actual content for any query containing the word "lesson". Retrieval returns
    content; a heading with nothing under it is not a result.
    """
    if not _section_body(body).strip():
        return 0.0

    heading = str(node.get("label", "")).lower()
    artifact = _artifact_of(str(node.get("source_file", ""))).lower().replace("-", " ")
    lowered = body.lower()

    total = 0.0
    matched = 0
    for term in terms:
        hit = False
        if term in heading:
            total += _W_HEADING
            hit = True
        if term in artifact:
            total += _W_ARTIFACT
            hit = True
        count = lowered.count(term)
        if count:
            total += _W_BODY * (1.0 + min(count, _BODY_TF_CAP) * 0.25)
            hit = True
        if hit:
            matched += 1

    if not matched:
        return 0.0
    return total * (0.5 + 0.5 * (matched / len(terms)))


def _artifact_of(source_file: str) -> str:
    """The skill/memory/agent name a staged document belongs to."""
    parts = Path(source_file).parts
    if len(parts) < 2:
        return ""
    # skills stage as `<layer>-skills/<name>/SKILL.md`; everything else as
    # `<layer>-<kind>/<name>.md`.
    return parts[1] if len(parts) > 2 else Path(parts[1]).stem


def get_node(node: str, scope: str = "knowledge", root: Optional[Path] = None,
             max_lines: int = 200) -> Dict[str, Any]:
    """Return the text a graph node owns — the retriever half of the graph.

    :func:`query` locates; this fetches. A heading node resolves to exactly its
    markdown section and a definition node to its body, so an agent pulls the one
    section it needs rather than a whole skill.
    """
    ensured = ensure(scope, root, force=False)
    if ensured.get("error"):
        return {"status": "error", **ensured}
    graph = ensured["graph"]
    nodes = load_nodes(graph)
    stage_root = _stage_root(graph)

    wanted = node.strip()
    hits = [n for n in nodes if n.get("id") == wanted]
    if not hits:
        hits = [n for n in nodes if str(n.get("label", "")).lower() == wanted.lower()]
    if not hits:
        hits = [n for n in nodes if wanted.lower() in str(n.get("label", "")).lower()]
    if not hits:
        return {"status": "not_found", "error": f"no node {wanted!r}; locate one with graph_query",
                "graph": graph}
    if len(hits) > 1:
        return {
            "status": "ambiguous",
            "error": f"{len(hits)} nodes match {wanted!r} — retry with an exact id",
            "candidates": [{"id": n["id"], "src": n.get("source_file")} for n in hits[:10]],
            "graph": graph,
        }

    hit = hits[0]
    if not hit.get("source_file"):
        return {"status": "error", "error": f"node {wanted!r} has no source file (external symbol)",
                "graph": graph}
    try:
        text, start, stop, truncated = read_span(stage_root, hit, nodes, max_lines)
    except OSError as exc:
        return {"status": "error", "error": f"cannot read {hit['source_file']}: {exc}",
                "graph": graph}

    return {
        "status": "ok",
        "id": hit["id"],
        "label": hit["label"],
        "text": text,
        "source_file": _real_path(stage_root, hit["source_file"], scope),
        "lines": f"L{start}-L{stop}",
        "truncated": truncated,
        "graph": graph,
    }
