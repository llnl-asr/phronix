# Lessons — sympy-sympy-19487

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Assuming fixed field name

Assuming the field is always named email — this is the core issue; the field name may vary across different sympy contexts

### P2 — Performance regression

Overusing symbols() or assumption calls which can introduce performance regressions or break other parts of the codebase

### P3 — Introducing regressions

Making changes that fix one test but break other previously passing tests (as noted in the task history)

## Lessons

### L1 — Run full test suite

Always run the full relevant test suite, not just the failing test, to ensure no regressions

### L2 — Consult documentation

When in doubt about field naming, consult sympy's assumption system documentation and existing patterns in the codebase before hardcoding names

### L3 — Fix is half the work

The fix alone is half of it — ensure all integration points are handled, not just the immediate code change
