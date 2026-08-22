# Lessons — phronix-verification

Pitfalls and dated lessons for the **deterministic correctors that prove learned and healed things still hold** subject. Retrieved by *memory*
search (`context_memory`), not by skill search: "how do I do this" and "what went
wrong last time" are different questions, and keeping them in one file makes every
retrieval of either drag in the other.

## Pitfalls

### P1 — Environment preconditions written as constraints

The most common authoring error. A dependency check under `constraints` turns
every machine without that dependency red. Move it to `assumptions`, where a
failure correctly reads as "could not run here".

### P2 — A scaffolded corrector left unfinished

`verify_new` without a `source` produces a spec with no constraints. It is
reported as a malformed spec rather than passing — but until you notice, the
subject looks covered in `verify_coverage()`. Finish it in the same session.

### P3 — Correctors that pass because they check nothing

A constraint like `lambda ctx: True`, or one asserting something the code cannot
help but satisfy, produces permanent green. Ask of every constraint: what change
to the world would turn this red? If the answer is "none", delete it.

## Lessons
