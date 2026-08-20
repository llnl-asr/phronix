"""The memory write path — one implementation shared by the CLI and the MCP tools.

:mod:`phronix.memory_graph` is the read side (ranking, link-walking). This is the
write side: creating a memory, keeping each layer's ``MEMORY.md`` index current,
and refusing to persist anything that identifies a person.

Three invariants are enforced here rather than left to prompt discipline, because
"the agent was told not to" is not a privacy control:

1. **Everything written is redacted first.** :func:`phronix.privacy.anonymize`
   runs on the full document, and what it changed is reported back so the caller
   can see what was stripped instead of discovering it in a diff later.
2. **``type: user`` is rejected outright.** A profile of a person is precisely
   the thing this store must never contain, and no amount of redaction makes one
   safe — the whole document *is* the identity.
3. **The index is rewritten, never appended blindly.** A memory updated twice
   would otherwise get two index lines, and the index is what every session reads
   first.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

#: The frontmatter types a memory may carry.
#:
#: ``project``   ongoing work, goals, constraints not derivable from the code.
#: ``feedback``  guidance on how to work, with the reason it was given.
#: ``reference`` pointers to external resources.
#: ``lesson``    symptom -> root cause -> exact fix, captured from a real failure.
MEMORY_TYPES = ("project", "feedback", "reference", "lesson")

_INDEX_HEADER = "# Memory Index\n"


def slugify(name: str) -> str:
    """Normalize a memory name to the kebab-case slug used as its filename."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def read(name: str) -> Optional[Dict[str, Any]]:
    """Return one memory by name or filename stem, searching all layers."""
    from phronix.layers import memory_files

    wanted = name.strip().lower()
    for path in memory_files().values():
        text = path.read_text(encoding="utf-8", errors="replace")
        stem = path.stem.lower()
        declared = re.search(r"(?m)^name:\s*(.+)$", text[:500])
        declared_name = declared.group(1).strip().lower() if declared else ""
        if wanted in (stem, declared_name):
            from phronix.layers import which_layer

            return {
                "name": declared_name or stem,
                "file": path.name,
                "path": str(path),
                "layer": which_layer(path),
                "content": text,
            }
    return None


def listing() -> List[Dict[str, Any]]:
    """Every visible memory's name, description, type and owning layer."""
    from phronix.layers import memory_files, which_layer

    out: List[Dict[str, Any]] = []
    for filename, path in sorted(memory_files().items()):
        entry: Dict[str, Any] = {"file": filename, "layer": which_layer(path)}
        head = path.read_text(encoding="utf-8", errors="replace")[:1000]
        match = re.match(r"^---\n(.*?)\n---\n", head, re.DOTALL)
        if match:
            block = match.group(1)
            for key in ("name", "description"):
                hit = re.search(rf"(?m)^{key}:\s*(.+)$", block)
                if hit:
                    entry[key] = hit.group(1).strip()
            type_hit = re.search(r"(?m)^\s*type:\s*(.+)$", block)
            if type_hit:
                entry["type"] = type_hit.group(1).strip()
        entry.setdefault("name", path.stem)
        out.append(entry)
    return out


def write(
    name: str,
    description: str,
    body: str,
    type: str = "project",
    layer: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or update a memory, redacting it and refreshing the layer index.

    Args:
        name: kebab-case slug, e.g. ``project-harness-agent-templates``.
        description: one-line summary; this is what the index and the injected
            digest show, so it carries most of the retrieval signal.
        body: the fact. For ``feedback``/``project``, include ``**Why:**`` and
            ``**How to apply:**`` lines. Link related memories with ``[[name]]``.
        type: one of :data:`MEMORY_TYPES`.
        layer: force a target layer; defaults to
            :func:`phronix.layers.resolve_write_layer`.

    Returns a dict with ``status``, ``file``, ``layer``, ``action``
    (created/updated) and ``redacted`` (what the anonymizer stripped).
    """
    from phronix.layers import resolve_write_layer
    from phronix.privacy import anonymize, current_users, find_identifiers

    if type == "user":
        return {
            "status": "error",
            "error": "type='user' is never allowed: memory is shared and version-controlled, "
                     "and a profile of a person cannot be made safe by redaction. "
                     f"Use one of {'|'.join(MEMORY_TYPES)}.",
        }
    if type not in MEMORY_TYPES:
        return {"status": "error", "error": f"type={type!r} must be one of {'|'.join(MEMORY_TYPES)}"}

    slug = slugify(name)
    if not slug:
        return {"status": "error", "error": "name must contain letters or digits"}

    target = resolve_write_layer(layer)
    mem_dir = target.dir("memory")
    mem_dir.mkdir(parents=True, exist_ok=True)

    text = (
        f"---\nname: {slug}\ndescription: {description}\n"
        f"metadata:\n  type: {type}\n---\n\n{body.rstrip()}\n"
    )
    # Bare usernames outside a path are only caught when passed explicitly.
    extra_users = current_users()
    redacted = find_identifiers(text, extra_users=extra_users)
    text = anonymize(text, extra_users=extra_users)

    dest = mem_dir / f"{slug}.md"
    existed = dest.exists()
    dest.write_text(text)
    reindex(target.root / "memory")

    # The knowledge graph rebuilds on a content hash, so a memory written
    # mid-session stays invisible to graph_query(mode="docs") until the next
    # sweep. Marking dirty here is what makes a just-recorded lesson retrievable
    # in the SAME session. memory_recall reads the store directly and is
    # unaffected, but the graph path must not go stale behind it.
    try:
        from phronix.knowledge_graph import mark_dirty

        mark_dirty(f"memory_write:{slug}")
    except Exception:
        pass  # retrieval degrades to the next hash sweep; never fail a write

    return {
        "status": "ok",
        "file": str(dest),
        "layer": target.name,
        "action": "updated" if existed else "created",
        "redacted": redacted,
    }


def reindex(mem_dir: Path) -> Path:
    """Rewrite ``MEMORY.md`` for one layer's memory directory.

    Rebuilt from the files on disk rather than edited in place, so a deleted
    memory disappears from the index and a renamed one does not leave a ghost
    line pointing at nothing.
    """
    from phronix.privacy import anonymize

    mem_dir = Path(mem_dir)
    mem_dir.mkdir(parents=True, exist_ok=True)
    lines = [_INDEX_HEADER, "", "One line per memory. Bodies live in the linked files.", ""]
    for path in sorted(mem_dir.glob("*.md")):
        if path.name == "MEMORY.md":
            continue
        head = path.read_text(encoding="utf-8", errors="replace")[:1000]
        desc_hit = re.search(r"(?m)^description:\s*(.+)$", head)
        desc = anonymize(desc_hit.group(1).strip()) if desc_hit else ""
        lines.append(f"- [{path.stem}]({path.name}) — {desc}" if desc else f"- [{path.stem}]({path.name})")
    index = mem_dir / "MEMORY.md"
    index.write_text("\n".join(lines) + "\n")
    return index


def reindex_all() -> List[str]:
    """Refresh every writable layer's index. Used by the startup self-heal."""
    from phronix.layers import layers

    touched: List[str] = []
    for layer in layers():
        if layer.writable and layer.dir("memory").is_dir():
            touched.append(str(reindex(layer.dir("memory"))))
    return touched
