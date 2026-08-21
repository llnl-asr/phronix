---
name: phronix-learning-reconcile-established
description: Stage has executed phronix-learning-reconcile skill, producing consolidated facts
metadata:
  type: project
---

---
name: phronix-learning-reconcile-established
description: The phronix learning reconcile stage has been run, consolidating duplicate facts and improving learner behavior.
metadata:
  type: project
---
The `phronix-learning-reconcile` skill was executed, resulting in:
- Merged duplicate fact blocks per instructions I2.
- Added reference links to original sources (X1).
- Retired falsified entries as identified by `research_notice`.
- Updated learner's own capture rules (I5).

**Why:** Ensures the knowledge base remains a single source of truth, preventing divergent facts and making future corrections propagate automatically.
**How to apply:** When adding new facts, check the index for existing labels before creating new blocks. Use `skill_write` with reference links rather than duplicating content.

[[learner-graph-rebuild-failure]]
[[phronix-learning-reconcile]]
