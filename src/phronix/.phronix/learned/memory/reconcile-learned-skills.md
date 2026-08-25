---
name: reconcile-learned-skills
description: Performed reconciliation of learned skills per phronix-learning-reconcile instructions
metadata:
  type: project
---

Implemented steps I1‑I5: examined graph neighbourhoods, merged sibling subjects, shaped topic skills with answer and cases, merged duplicate blocks by label, added references, retired falsified lessons, and improved learner's own skills. Updated skills accordingly and recorded actions.

**Why:** To ensure a single true copy of each fact, remove redundancies, and enhance learner reliability.

**How to apply:** Run the reconciliation cycle regularly; use `graph_query` and `graph_get_node` to identify duplicates, merge using `skill_write` and `skill_write_lesson`, retire falsified entries, and document learner improvements.
