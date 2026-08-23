# Lessons — mcp-server-tooling

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

## Lessons

### L1 — Knowledge graph rebuild failed with OSError

2026-08-22, root cause found: reproduced live as `OSError: [Errno 39] Directory not empty: '<workdir>/learner-cache/graph/knowledge/stage/graphify-out/cache/ast'` from graph_query(mode="docs"). The rebuild step removes/replaces that cache/ast directory and fails with ENOTEMPTY, consistent with a concurrent or previously-interrupted rebuild leaving files behind when the next rebuild tries to clear it. Recurred 3x, all on pallets__flask-4045, mcp-server stage, all worked=false; earlier reports (this task, and pylint-dev__pylint-7080 before it) only had a bare "OSError" with no stack trace — this is the first occurrence with errno/path captured, so the failure is now root-caused rather than just repeated.

Handling: see R1 (retry once, then avoid graph tools for the rest of the stage — the cache dir does not self-heal within a single rebuild attempt).

Still open: whether this is triggered by concurrent mcp-server processes racing on the same cache dir, or a leftover from an earlier crashed rebuild. Next occurrence: check whether another process/task shares this learner-cache path concurrently.

### L2 — Knowledge graph rebuild failed with OSError

**2026-08-22** — graph_query/graph_get_node from the mcp-server stage has repeatedly triggered a knowledge-graph rebuild that fails with OSError/FileNotFoundError (worked=false every time). This is the same fact tracked in full — occurrence count, topics, and the "stop retrying and fall back" guidance — at [[phronix-context-economy#X3]] and [[phronix-context-economy#R6]]. Do not log new occurrences here; widen the count on X3 instead so there is one tracker, not two.

### L3 — L2's pointer to phronix-context-economy is broken; L1 is the canonical tracker

**2026-08-22** — 2026-08-22 — Reconcile pass checked the references in L2 ([[phronix-context-economy#X3]], [[phronix-context-economy#R6]]): neither label exists in phronix-context-economy (its blocks are I1-I5, R1-R5, X1-X2, P1-P3). L2's instruction to "log occurrences there, not here" cannot be followed — that tracker does not exist. Treat **L1** as the canonical, only tracker for this OSError until/unless a real cross-referenced skill is created and confirmed to exist. This cycle's report ("repeated — the knowledge graph failed to rebuild: OSError, mcp-server") is another occurrence of the same L1 fact; widening the count there rather than adding a new dated block. No skill_write tool supports deleting/rewriting L2 in place (see R4) — this entry supersedes it; a future editor with file access should delete L2 and merge its content into L1.

### L4 — L1 occurrence count is stale — now 5, not 3

**2026-08-22** — 2026-08-22 reconcile: this is the same OSError fact tracked in full at L1 (root cause: ENOTEMPTY on learner-cache/graph/knowledge/stage/graphify-out/cache/ast during rebuild; handling: R1 retry-once-then-fallback). research_notice now shows 5 occurrences (all mcp-server stage, pallets__flask-4045, worked=false), not the "3x" L1 states — widening the count here since skill_write_lesson cannot edit L1 in place (see R4/X2). No new root cause or handling info in this occurrence; do not append another duplicate block for future recurrences of the same bare report — check research_notice's count against L1's stated count instead, and only write if genuinely new detail (stack trace, trigger condition) appears.
