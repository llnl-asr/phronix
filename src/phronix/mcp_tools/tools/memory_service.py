"""Memory tools: durable facts, portable across every harness.

Some harnesses have a native memory feature; they do not agree on where it
lives, and none of them put it anywhere version control can see. These tools are
the portable write path — memory recorded through them is committed alongside the
project and reaches whoever clones it next.
"""
from __future__ import annotations

import json
from typing import Any


def register(mcp: Any) -> None:
    @mcp.tool()
    def memory_list() -> str:
        """List every memory: name, one-line description, type, and layer.

        Memory is one markdown file per durable fact. Call this at session start
        for a map of what past sessions established, then ``memory_read`` the ones
        that matter. Prefer ``memory_recall`` once you know what you are after —
        this returns everything.

        Returns JSON: {status, count, memories: [{name, description, type, layer, file}]}.
        """
        from phronix.memory import listing

        memories = listing()
        return json.dumps({
            "status": "ok",
            "count": len(memories),
            "memories": memories,
            "usage": "memory_read(name=...) for full text; memory_recall(query=...) to search.",
        }, indent=2)

    @mcp.tool()
    def memory_recall(query: str, k: int = 5, types: str = "", expand_links: bool = True) -> str:
        """Search memory by relevance instead of listing all of it.

        Ranks every memory against *query* by matching its name, description AND
        body, then walks one hop of the ``[[wikilink]]`` graph — so a memory that
        names the right neighbour pulls that neighbour in too, even when the
        neighbour's own text does not match your query.

        Use this whenever you are about to do something the project may already
        have a view on: a build, a deployment, a design decision, an approach the
        user has corrected before.

        Args:
            query: free text; a task description or an error message both work.
            k: how many directly-matched memories to keep before link expansion.
            types: comma-separated filter — project | feedback | reference | lesson.
            expand_links: include 1-hop [[wikilink]] neighbours of the hits.

        Returns JSON: {status, count, results: [{name, description, type, score,
        via}], digest}. ``via`` is "match" for a direct hit, or the name of the
        memory that linked to it. Bodies are not included — ``memory_read`` those
        that matter.
        """
        from phronix.memory_graph import recall, render_digest

        wanted = [t.strip() for t in types.split(",") if t.strip()] or None
        try:
            results = recall(query, k=k, types=wanted, expand_links=expand_links)
        except Exception as exc:
            return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
        return json.dumps({
            "status": "ok" if results else "no_match",
            "count": len(results),
            "results": results,
            "digest": render_digest(results, budget_chars=2000),
            "usage": "memory_read(name=...) for the full text of any of these.",
        }, indent=2)

    @mcp.tool()
    def memory_read(name: str) -> str:
        """Return the full text of one or more memories (comma-separated names).

        ``name`` matches the frontmatter ``name`` or the filename stem.

        Returns JSON: {status, loaded: [{name, layer, content}], missing: [...]}.
        """
        from phronix.memory import read

        loaded, missing = [], []
        for requested in [n.strip() for n in name.split(",") if n.strip()]:
            hit = read(requested)
            (loaded if hit else missing).append(hit or requested)
        result = {"status": "ok" if loaded else "not_found", "loaded": loaded}
        if missing:
            from phronix.memory import listing

            result["missing"] = missing
            result["available"] = sorted(m["name"] for m in listing())
        return json.dumps(result, indent=2)

    @mcp.tool()
    def memory_write(
        name: str,
        description: str,
        body: str,
        type: str = "project",
        layer: str = "",
    ) -> str:
        """Create or update a durable memory, and refresh the index.

        **Use this whenever the session produces a fact that should outlive it** —
        not only at the end. A decision the user made, a constraint they stated, a
        piece of standing guidance, the state of ongoing work.

        Choose the type by what the fact IS:

        - ``project`` — ongoing work, goals, constraints not derivable from the code.
        - ``feedback`` — guidance on how to work. Always include **Why:** — a rule
          without its reason gets misapplied the first time the situation differs.
        - ``reference`` — pointers to external resources (URLs, dashboards, tickets).
        - ``lesson`` — symptom → root cause → exact fix from a real failure.

        Link related memories with ``[[name]]``. Link liberally: a link to a memory
        that does not exist yet is not an error, it marks something worth writing.
        The links are what let ``memory_recall`` surface a relevant neighbour whose
        own text does not match the query.

        Everything is redacted before it is written, and ``type=user`` is rejected
        outright — a profile of a person cannot be made safe by redaction, and this
        store is committed and shared.

        Args:
            name: kebab-case slug, e.g. "project-auth-migration".
            description: one line; this is what the index and the injected digest
                show, so it carries most of the retrieval signal. Make it specific.
            body: the fact. For feedback/project, include **Why:** and
                **How to apply:** lines.
            type: project | feedback | reference | lesson.
            layer: force a target layer ("project", "user", "bundled").

        Returns JSON: {status, file, layer, action, redacted}.
        """
        from phronix.memory import write

        return json.dumps(
            write(name, description, body, type=type, layer=layer or None), indent=2)
