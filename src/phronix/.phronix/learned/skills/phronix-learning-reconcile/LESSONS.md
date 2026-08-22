# Lessons — phronix-learning-reconcile

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Stale learning persistence

Repeated learning attempts fail to capture new observations, leading to stale or incorrect knowledge. When `research_observe` reports repeated failures, the learner does not adjust its capture rules, causing the same mistaken lesson to persist across cycles.

## Lessons

### L1 — L2 – Update capture rules on repeated failures

**2026-08-21** — When `research_observe(topic="learning", worked=false)` reports repeated failures, the learner must adjust its capture rules in `phronix-learning-capture` to record new observations. Without this, stale knowledge persists and leads to repeated false lessons. Add or modify capture rules accordingly.


### L3 — Handle stale knowledge graph rebuild failures

**2026-08-21** — The knowledge graph sometimes fails to rebuild, causing FileNotFoundError errors across multiple tasks (e.g., Flask related). When this occurs, run `graph_ensure(force=True)` to force a rebuild before relying on graph queries. Ensure the graph files exist and paths are correct.
