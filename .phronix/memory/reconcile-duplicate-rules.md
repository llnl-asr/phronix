---
name: reconcile-duplicate-rules
description: Reconciled duplicate rule blocks across bundled and project skill layers
metadata:
  type: project
---

**Why:** Duplicate rule blocks (e.g., R6) existed in both bundled and project skill copies, risking drift and inconsistent behavior. 
**How to apply:** When `graph_query` finds the same rule in multiple layers, add a reference block in the bundled skill pointing to the project copy, then record the action with `research_observe`. This ensures a single source of truth and maintains consistency across layers.
**What was done:** Added reference X4 in `phronix-skill-authoring` linking to the project copy of R6, verified with `verify_run`, and logged the observation via `research_observe`.
