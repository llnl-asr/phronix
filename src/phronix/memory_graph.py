"""Relevance retrieval over the layered markdown memory store.

Memory is a *linked* corpus: one file per fact, carrying ``[[wikilink]]``
references to sibling memories. Without something that reads those links, the
only retrieval available is "list every memory's name and description and let
the agent eyeball-pick" — which costs more context every session than it saves
and degrades as the corpus grows.

Retrieval here is a direct read of the store rather than a knowledge-graph
query, for three reasons:

* **Size.** A memory corpus is tens of files and a few hundred KB. Reading it
  costs a few milliseconds, so there is no index to amortise.
* **Body text.** The graph's ``docs`` mode scores headings and file paths; a
  memory whose *content* is relevant but whose title is not would score zero.
  Bodies are where the lessons actually live.
* **Staleness.** The graph rebuilds on a content hash, so a memory written
  mid-session is invisible until the next sweep. Reading the directory is
  always current — which matters most for exactly the memory just written.

Scoring is lexical (weighted field match + saturating body frequency, scaled by
query coverage), then the wikilink graph is walked one hop so a memory that
names the right neighbour pulls it in. Everything is pure and side-effect free
so it is unit-testable without a server; :func:`recall` is the entry point.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

# Field weights. Name and description are curated one-liners, so a hit there is
# a far stronger signal than a hit somewhere in a 3 KB body.
_W_NAME = 4.0
_W_DESC = 3.0
_W_BODY = 1.0

# Body term-frequency saturation: repeating one term 50 times must not outrank a
# memory that matches more of the query. Caps the per-term body bonus at +2.0.
_BODY_TF_CAP = 5

# A 1-hop neighbour inherits this fraction of the score that pulled it in.
_LINK_DECAY = 0.35

_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)

_STOPWORDS = frozenset("""
and are but for from has have how not the that this was were what when
with you your can will its about into than then they there their
""".split())


def parse_links(text: str) -> List[str]:
    """Return the ``[[wikilink]]`` targets in *text*, lowercased and de-duped.

    Targets are memory ``name`` slugs. A link may point at a memory that does not
    exist yet — the conventions explicitly allow that as a "worth writing later"
    marker — so callers must tolerate dangling targets.
    """
    seen, out = set(), []
    for raw in _LINK_RE.findall(text):
        # "[[name|alias]]" and "[[name#section]]" both resolve to the name.
        target = re.split(r"[|#]", raw, maxsplit=1)[0].strip().lower()
        if target and target not in seen:
            seen.add(target)
            out.append(target)
    return out


def _parse_frontmatter(text: str) -> Dict[str, str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    block = match.group(1)
    fields: Dict[str, str] = {}
    for key in ("name", "description"):
        hit = re.search(rf"(?m)^{key}:\s*(.+)$", block)
        if hit:
            fields[key] = hit.group(1).strip().strip('"').strip("'")
    type_hit = re.search(r"(?m)^\s*type:\s*(.+)$", block)
    if type_hit:
        fields["type"] = type_hit.group(1).strip()
    return fields


def _body_of(text: str) -> str:
    match = _FRONTMATTER_RE.match(text)
    return text[match.end():] if match else text


def load_memories(mem_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Parse every visible memory into a dict, merged across layers.

    Pass *mem_dir* to read one directory instead (tests, or inspecting a single
    layer). Falls back to the filename stem when frontmatter omits ``name``, so
    a hand-written memory is still addressable.
    """
    if mem_dir is not None:
        base = Path(mem_dir)
        paths = sorted(p for p in base.glob("*.md") if p.name != "MEMORY.md") if base.is_dir() else []
    else:
        from phronix.layers import memory_files

        paths = sorted(memory_files().values())

    out: List[Dict[str, Any]] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fields = _parse_frontmatter(text)
        body = _body_of(text)
        out.append({
            "name": (fields.get("name") or path.stem).strip(),
            "description": fields.get("description", ""),
            "type": fields.get("type", ""),
            "body": body,
            "links": parse_links(body),
            "file": path.name,
            "path": str(path),
            "chars": len(text),
        })
    return out


def tokenize(query: str) -> List[str]:
    """Query terms: longer than 2 chars, de-duped, stopwords dropped.

    Hyphenated slugs are split as well, so a query of ``always-function-mode``
    also matches prose that says "function mode".
    """
    raw = re.split(r"[^\w.]+", query.lower())
    terms: List[str] = []
    seen = set()
    for token in raw:
        parts = ({token} | set(token.split("-"))) if "-" in token else {token}
        for part in parts:
            part = part.strip(".")
            if len(part) > 2 and part not in _STOPWORDS and part not in seen:
                seen.add(part)
                terms.append(part)
    return terms


def score_memory(mem: Dict[str, Any], terms: Sequence[str]) -> float:
    """Weighted field match, saturating body frequency, scaled by query coverage.

    Coverage matters more than raw frequency: a memory matching 3 of 3 query
    terms once each is a better answer than one matching a single term 40 times.
    """
    if not terms:
        return 0.0
    name = mem["name"].lower().replace("-", " ")
    desc = mem["description"].lower()
    body = mem["body"].lower()

    total = 0.0
    matched = 0
    for term in terms:
        hit = False
        if term in name:
            total += _W_NAME
            hit = True
        if term in desc:
            total += _W_DESC
            hit = True
        count = body.count(term)
        if count:
            total += _W_BODY * (1.0 + min(count, _BODY_TF_CAP) * 0.2)
            hit = True
        if hit:
            matched += 1

    if not matched:
        return 0.0
    coverage = matched / len(terms)
    return total * (0.5 + 0.5 * coverage)


def recall(
    query: str,
    k: int = 5,
    types: Optional[Iterable[str]] = None,
    expand_links: bool = True,
    mem_dir: Optional[Path] = None,
    memories: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Rank memories against *query*, then walk one hop of the wikilink graph.

    Args:
        query: free text — a user prompt, a tool name plus args, an error message.
        k: how many *directly scored* hits to keep before link expansion.
        types: restrict to these frontmatter types (project/feedback/reference).
        expand_links: pull in 1-hop ``[[wikilink]]`` neighbours of the hits.
        mem_dir / memories: injection points for tests and single-layer views.

    Returns a ranked list of ``{name, description, type, score, via, file}``,
    where ``via`` is ``"match"`` for a direct hit or the linking memory's name
    for one pulled in by expansion. Bodies are NOT included — the caller decides
    how much text to spend (see :func:`render_digest`).
    """
    pool = memories if memories is not None else load_memories(mem_dir)
    if types:
        wanted = {t.strip().lower() for t in types if t and t.strip()}
        if wanted:
            pool = [m for m in pool if m.get("type", "").lower() in wanted]
    terms = tokenize(query)
    if not terms or not pool:
        return []

    scored = [(score_memory(m, terms), m) for m in pool]
    hits = sorted(((s, m) for s, m in scored if s > 0), key=lambda p: (-p[0], p[1]["name"]))[:k]
    if not hits:
        return []

    by_name = {m["name"].lower(): m for m in pool}
    results: List[Dict[str, Any]] = []
    seen = set()
    for score, mem in hits:
        seen.add(mem["name"].lower())
        results.append({**_summary(mem), "score": round(score, 2), "via": "match"})

    if expand_links:
        for score, mem in hits:
            for target in mem["links"]:
                if target in seen:
                    continue
                neighbour = by_name.get(target)
                if neighbour is None:
                    continue  # dangling link — allowed by the memory conventions
                seen.add(target)
                results.append({
                    **_summary(neighbour),
                    "score": round(score * _LINK_DECAY, 2),
                    "via": mem["name"],
                })

    results.sort(key=lambda r: (-r["score"], r["name"]))
    return results


def _summary(mem: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": mem["name"],
        "description": mem["description"],
        "type": mem.get("type", ""),
        "file": mem.get("file", ""),
        "chars": mem.get("chars", 0),
    }


def render_digest(results: Sequence[Dict[str, Any]], budget_chars: int = 1200) -> str:
    """One line per memory, truncated to *budget_chars*.

    Intentionally descriptions-only. This is the shape injected automatically on
    every prompt, and injecting bodies would cost more context than the memories
    save. Each line names the memory so the agent can ``memory_read`` the ones
    that actually matter.
    """
    lines: List[str] = []
    used = 0
    for result in results:
        via = "" if result["via"] == "match" else f" (via {result['via']})"
        line = f"- {result['name']}: {result['description']}{via}"
        if used + len(line) + 1 > budget_chars:
            lines.append(f"- ... {len(results) - len(lines)} more (memory_recall for the rest)")
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)
