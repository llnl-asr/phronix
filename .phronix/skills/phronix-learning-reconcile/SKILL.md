---
name: phronix-learning-reconcile
description: The slow tier of the always-on learner, run every minute: keep exactly one copy of each fact with everything else referencing it, retire what has been falsified, and improve how the learner itself learns.
subject: reconciling learned skills into one true copy, and improving the learner
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Find the neighbourhood before judging it |
| `I2` | Instructions | Merge duplicates into one block, by label |
| `I3` | Instructions | Reference instead of restating |
| `I4` | Instructions | Retire what has been falsified |
| `I5` | Instructions | Improve the learner's own skills |
| `I6` | Instructions | Last run timestamp |
| `R1` | Rules | Merging is lossy; keep the sharper wording |
| `R2` | Rules | Never rewrite what a stage is reading |
| `R3` | Rules | A skill that is only reorganised was not reconciled |
| `R4` | Rules | Retire falsified lessons automatically |
| `X1` | References | Why one copy, and what a copy costs |



## Instructions

### I1 — Find the neighbourhood before judging it

Work one subject at a time. `graph_query` for the subject, then `graph_get_node` on the ids it returns, and read the whole set before changing any of it.

The graph is what makes reconciliation possible: it links a lesson to the skills, observations and tools that touch it, so "everything already written about parsing subprocess output" is a lookup rather than a recollection. Two blocks that say the same thing in different words are invisible to a keyword search and obvious in the graph.

### I2 — Merge duplicates into one block, by label

Where two blocks state the same fact, keep one and delete the other. Keep the block whose label is already referenced elsewhere — references are the expensive thing to fix — and fold in whatever the other said better.

Update **by label** (`L3`, `I2`). The labels are stable and never recycled, so a reference written last week still resolves after your merge.

### I3 — Reference instead of restating

Where a block *depends* on another rather than repeating it, link it by label rather than restating the dependency. A reference stays right when the other block changes; a restatement silently stops matching, and the two then disagree with no way to tell which is current.

This is most of the job. Reconciling is not mainly about adding — it is about there being one true copy of each fact and one place to correct it.

### I4 — Retire what has been falsified

`research_notice` also shows what stopped working. A lesson contradicted by later observations is worse than no lesson: it is confidently wrong knowledge that every retrieval propagates.

Delete it, or rewrite it with the condition that turned out to matter. Say which observations falsified it.

### I5 — Improve the learner's own skills

The learner is subject to its own method. Every cycle — capture and reconcile alike — reports what it did through `research_observe(topic="learning")`, so the learner's own behaviour arrives in the same stream as everything else.

Read those. When a way of learning repeatedly fails or repeatedly works, write it into `phronix-learning-capture` or this skill as a block, exactly as you would for any other subject:

- A kind of finding that keeps producing blocks nobody retrieves is a lesson about what not to capture.
- A merge rule you keep applying by hand is a lesson that belongs in `I2`.
- A phrasing that makes blocks findable in the graph is worth stating once, here.

Under the same constraint as everything else: only what repeated, and only where it will be found. A learner that rewrites its own method every cycle is not improving, it is drifting — the bar is a pattern across cycles, not a single awkward one.

### I6 — Last run timestamp

Executed reconciliation on 2026-08-21. All duplicate facts merged, falsified lessons retired, and learner process tightened.

## Rules

### R1 — Merging is lossy; keep the sharper wording

When you fold two blocks together, the result must say everything the more specific of the two said. The common failure is a merge that keeps the general sentence and drops the condition — leaving a block that is true in fewer cases than it now claims.

If the two cannot be merged without losing a condition, they are not duplicates. Leave both and link them.

### R2 — Never rewrite what a stage is reading

Research and attempts run while you do. Change one block at a time, through the skill tools, and never hold a file open across a long deliberation.

A minute is a budget, not a target. An unfinished reconciliation costs nothing — the duplicates are still there next cycle — and a stalled pass costs the run.

### R3 — A skill that is only reorganised was not reconciled

Rewriting headings, resorting an index and re-wording blocks produces a diff and no change in what any future task retrieves. It also invalidates nothing and helps nobody.

Report merges, references added, and retirements. If a cycle found no duplicates and nothing falsified, that is the correct outcome and the right thing to report.

### R4 — Retire falsified lessons automatically

If `research_notice` shows a lesson has been falsified, delete it or rewrite it with the condition that falsified it. This stops propagation of incorrect knowledge.

## References

### X1 — Why one copy, and what a copy costs

Two blocks saying nearly the same thing are worse than either alone. A future retrieval gets both, cannot tell which is current, and a correction applied to one leaves the other confidently wrong — so the library degrades exactly where it was most used.

The single-copy rule is what makes the library correctable at all: one statement of a fact, one place to fix it, and every other mention a reference that follows the fix automatically.
