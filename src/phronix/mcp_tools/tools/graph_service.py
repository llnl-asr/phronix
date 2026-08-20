"""Graph tools: locate code and knowledge instead of reading it.

Three thin wrappers rather than graphify's own MCP server. That server exposes
around twenty-five schemas, and every tool schema sits in the model's context on
every turn for the whole session. Three wrappers buy the two things that
actually matter — guaranteed freshness and node retrieval — at a fraction of the
standing cost.
"""
from __future__ import annotations

import json
from typing import Any, List, Optional


def register(mcp: Any) -> None:
    @mcp.tool()
    def graph_ensure(scope: str = "knowledge", root: str = "", force: bool = False) -> str:
        """Ensure a knowledge graph is fresh, rebuilding only if its inputs changed.

        You rarely need to call this directly — ``graph_query`` freshens the graph
        itself. Call it explicitly to warm the graph before a burst of queries, or
        with ``force=True`` when a query returns a line number that no longer
        matches the file.

        Args:
            scope: ``knowledge`` — phronix's own source plus every skill, agent
                template and memory it can see. ``project`` — the tree you are
                working in.
            root: an explicit path for ``scope="project"``.
            force: rebuild even when the content hash is unchanged.

        Returns JSON: {rebuilt, reason, graph, nodes}.
        """
        from phronix.knowledge_graph import ensure

        return json.dumps(ensure(scope, root or None, force), indent=2)

    @mcp.tool()
    def graph_query(
        question: str = "",
        mode: str = "query",
        symbol: str = "",
        budget: int = 1200,
        depth: int = 2,
        scope: str = "knowledge",
        root: str = "",
        context: Optional[List[str]] = None,
        limit: int = 12,
    ) -> str:
        """Locate code and documents without reading them. Freshens the graph first.

        **Use this before Read or grep on any tree, and before loading a whole
        skill.** Locating through the graph costs a few hundred tokens where
        reading the relevant files costs tens of thousands — and the answer is a
        precise ``file:line`` rather than a file you still have to scan.

        Modes:

        ``query``
            Breadth-first search for *question*; returns ``NODE <symbol>
            [src=file loc=Lnn]``. Open only what it names.
        ``docs``
            Search markdown only — skills, agent templates, memory. This is the
            cheap way into a large skill: it returns the exact heading and
            ``file:line``, which you then pass to ``graph_get_node`` or use as
            the ``section`` argument to ``skill_load``. A plain ``query`` BFS
            leaks into the code subgraph and buries headings under generic
            helpers, which is why documents get their own ranked path.
        ``explain``
            Definition, callers and callees of *symbol*.
        ``affected``
            Reverse traversal — everything impacted by changing *symbol*.
            **Run this before editing any shared function and state the blast
            radius.** A "local" fix that silently breaks a caller is the failure
            this exists to prevent.

        Args:
            question: what you are looking for (``query`` / ``docs``).
            mode: query | docs | explain | affected.
            symbol: function or class name (``explain`` / ``affected``).
            budget: token cap on ``query`` output; raise only if truncated.
            depth: reverse-traversal depth for ``affected``.
            scope: ``knowledge`` (skills, agents, memory, phronix source) or
                ``project`` (the tree you are working in).
            root: explicit path for ``scope="project"``.
            context: edge-context filters narrowing a ``query`` BFS, e.g. ["call"].
            limit: maximum rows for ``mode="docs"``.

        Returns JSON: {status, output, graph}. BFS pulls in generic nodes — ignore
        them rather than widening the query.
        """
        from phronix.knowledge_graph import query

        return json.dumps(
            query(question=question, mode=mode, symbol=symbol, budget=budget,
                  depth=depth, scope=scope, root=root or None, context=context,
                  limit=limit),
            indent=2,
        )

    @mcp.tool()
    def graph_get_node(node: str, scope: str = "knowledge", root: str = "",
                       max_lines: int = 200) -> str:
        """Return the text a graph node owns — the retriever half of the graph.

        ``graph_query`` locates; this fetches. A heading node resolves to exactly
        its markdown section and a definition node to its body, so you can pull the
        one section you need instead of a whole file or a whole skill.

        Args:
            node: a node ``id`` (exact, and preferred — take it from
                ``graph_query``) or a label. An ambiguous label returns the
                candidate ids rather than picking one.
            scope: knowledge | project.
            root: explicit path for ``scope="project"``.
            max_lines: truncate bodies longer than this.

        Returns JSON: {status, text, source_file, lines, truncated}.
        """
        from phronix.knowledge_graph import get_node

        return json.dumps(get_node(node, scope=scope, root=root or None,
                                   max_lines=max_lines), indent=2)
