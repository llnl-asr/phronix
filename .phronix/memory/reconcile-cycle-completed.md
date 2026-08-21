---
name: reconcile-cycle-completed
description: Outcome of phronix learning reconcile cycle
metadata:
  type: project
---

---
name: reconcile-cycle-completed
description: Completed a reconcile cycle for phronix learning artifacts, de-duplicated facts, retired falsified lessons, and added learner cleanup steps.
metadata:
  type: project
---

**Why:** The learner had duplicate or contradictory lessons and a persistent graph rebuild failure due to stale cache directories. Reconciling ensures a single source of truth for each fact and improves future learning.

**How to apply:**
- Run `skill_load("phronix-learning-reconcile")` and follow Instructions I1‑I6.
- After merging duplicates, delete any lesson flagged by `research_notice` as falsified.
- Add a cleanup step to the learner's cycle to clear `learner-cache/graph` before rebuilding the knowledge graph.
- Verify no duplicate blocks exist across skills via `graph_query` and `graph_get_node`.

**Related:** [[phronix-learning-reconcile]], [[learner-graph-rebuild-failure]], [[reconciled-phronix-learning]]
