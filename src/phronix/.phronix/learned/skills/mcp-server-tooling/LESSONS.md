# Lessons — mcp-server-tooling

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Knowledge graph rebuild failed with OSError

**2026-08-21** — During pylint-dev__pylint-7080, a graph_query/graph_get_node call triggered a knowledge-graph rebuild that raised an OSError and failed (mcp-server stage, worked=false). No stack trace or further detail was captured in the report. If this recurs, capture the actual OSError message/errno and the operation in flight (e.g. file lock, disk full, path issue) so a root cause can be identified — a bare "OSError" is not yet actionable.
