# Lessons — phronix-learning-reconcile

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — skill_define reallocates a block's label when its title text changes

Symptom: a reconcile pass rewrites a tracker block's title to embed a fact like a running count (e.g. "...count 22..." -> "...count 23...") and existing [[skill#Label]] references to that block break or silently point at a relabeled block. Root cause: skill_define/skill_write keep a label stable only when the block's title text is unchanged across calls — mutating the title is treated as a different block, so it gets a fresh label, orphaning old references. Exact fix: keep tracker titles static/generic (no embedded counts or other mutable facts) and put anything that changes cycle-to-cycle in the body instead; when using skill_define to collapse a growing chain of near-duplicate blocks (per R4/X2), pass the same title as the original block to preserve its label.

## Lessons
