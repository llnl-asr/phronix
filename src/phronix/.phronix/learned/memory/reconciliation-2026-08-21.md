---
name: reconciliation-2026-08-21
description: Executed a reconcile cycle for learned skills on 2026-08-21
metadata:
  type: project
---

**Why:** Ensure the knowledge base has a single authoritative copy of each fact, remove duplicated or falsified lessons, and improve the learner's processes.

**How to apply:** Run the `phronix-learning-reconcile` skill which:
- Finds the neighbourhood of each subject.
- Merges duplicate blocks by label, keeping sharper wording.
- Adds references instead of restating.
- Retires lessons that have been falsified according to `research_notice`.
- Updates the learner's own skill definitions based on observed patterns.
- Records the last run timestamp.

All duplicate facts were merged, no falsified lessons were found, and the learner's own skill set was reviewed for improvements.
