---
name: learner-graph-rebuild-failure
description: Repeated failures rebuilding the knowledge graph in the learner
metadata:
  type: feedback
---

The learner has repeatedly failed to rebuild the knowledge graph, causing errors such as `Directory not empty` when attempting `graph_query`. This prevents graph-based queries needed for reconciliation.

**Why:** The learner's cache directory contains leftover files from previous runs, leading to a non-empty directory error.

**How to apply:** Ensure the learner clears its cache before rebuilding the graph. Implement a cleanup step in the learner's cycle to remove stale graph files or initialize a fresh graph directory.

**Related:** [[phronix-learning-reconcile]]
