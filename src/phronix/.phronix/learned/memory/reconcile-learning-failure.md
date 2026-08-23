---
name: reconcile-learning-failure
description: Failed to rebuild knowledge graph for reconciliation
metadata:
  type: project
---

---
name: reconcile-learning-failure
description: Failed to rebuild knowledge graph for reconciliation
metadata:
  type: feedback
---
The attempt to rebuild the knowledge graph for the "phronix-learning-reconcile" skill failed due to a non-empty directory error. This prevents automated graph queries needed for subject reconciliation.

**Why:** The graph cache directory contains leftover files that block a clean rebuild.

**How to apply:** Manually clear the directory `$SCRATCH_ROOT/phronix-bench/runs/claude-0822-224248/claude-phronix/learner-cache/graph/knowledge/stage` or resolve the lock. Then re-run `graph_ensure` with `force:true`.
