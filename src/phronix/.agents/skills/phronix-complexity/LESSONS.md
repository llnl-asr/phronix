# Lessons — phronix-complexity

Pitfalls and dated lessons for the **measuring task complexity and choosing the model level** subject. Retrieved by *memory*
search (`context_memory`), not by skill search: "how do I do this" and "what went
wrong last time" are different questions, and keeping them in one file makes every
retrieval of either drag in the other.

## Pitfalls

### P1 — Assessing an agent whose difficulty is intrinsic to its function

A planner or synthesiser scores low on scope-derived signals — it loads few skills
and calls well-specified tools — and a purely measured verdict will confidently
demote it. Declare `intrinsic: max` so measurement can only raise it.

### P2 — Raising a level instead of building the capability

A rising score usually means a subject accumulated procedure that should have
become code. Buying a stronger model treats the symptom and leaves the drift
compounding.

### P3 — Never reassessing

The measurement is only worth anything if it is re-run. An agent assessed once at
authoring time and never again is exactly the fixed level the mechanism exists to
replace.

## Lessons
