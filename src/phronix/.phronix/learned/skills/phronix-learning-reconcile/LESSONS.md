# Lessons — phronix-learning-reconcile

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — skill_write_lesson does not update an existing lesson in place

Calling `skill_write_lesson` again against the same skill with an unchanged title does NOT update the existing lesson (e.g. L1) in place — it appends a new lesson (e.g. L2) with the identical title, producing an immediate duplicate that then has to be re-merged next cycle. The "label stable if title unchanged" guarantee (I2/R1 in this skill) applies to `skill_define` (which takes the full `lessons` array and an explicit label), not to `skill_write_lesson`, which is append-only. To widen or correct an existing lesson found during reconcile, read the current LESSONS.md, then use `skill_define` with the full lessons array and the same explicit label to update it in place. Reserve `skill_write_lesson` for genuinely new lessons/pitfalls (as done here) or when the skill/LESSONS.md doesn't exist yet.

### P2 — graph_query/Read surface every layer; skill_write_lesson and memory_write only write the project layer

A reconcile cycle that finds a fact via `graph_query`/`graph_get_node` may be looking at a block whose `source_file` sits outside this project's `store/.phronix/skills/` tree (e.g. a shared `/usr/.../phronix/.phronix/learned/skills/` copy). Writing tools used from this project resolve to the project layer by default, so a rule believed to be "already captured" from a graph hit can still be invisible to `skill_load` on later cycles — this is what stranded R4/R5 in `phronix-learning-reconcile`'s own SKILL.md for many cycles until this cycle re-wrote them into the project layer (see R6 there). Check `source_file` on any block a cycle is about to trust as reachable; if it points outside the project layer, re-write it into the project layer.

## Lessons
