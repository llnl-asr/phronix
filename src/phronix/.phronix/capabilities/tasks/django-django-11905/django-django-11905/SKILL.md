---
name: django-django-11905
description: Attempt to raise error for non-boolean __isnull lookup produced no changes; need different approach
subject: django-django-11905
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Instructions |
| `R1` | Rules | Constraints |





## Instructions

### I1 — Problem

Prevent using ``__isnull`` lookup with non‑boolean values; such usage currently raises a ``TypeError`` only for booleans, causing test failures.

### I2 — Key Idea

Guard ``IsNull`` by ensuring the RHS is a boolean; raise ``TypeError`` otherwise, preventing misuse of ``__isnull`` with non‑boolean values.

### I3 — Instructions

1. Edit ``django/db/models/lookups.py``.
2. Locate the ``IsNull`` class.
3. In ``as_sql`` add a boolean‑type guard before compiling the LHS:
   ```python
   if not isinstance(self.rhs, bool):
       raise TypeError("__isnull lookup requires a boolean value, got %r" % (self.rhs,))
   ```
4. Keep the existing logic unchanged after the guard.
5. Run the test suite; ensure the 38 regression tests still pass.
6. Verify that ``test_isnull_non_boolean_value`` now fails with the intended ``TypeError`` and that other lookup tests (e.g., ``test_iterator``) no longer error due to the guard.

## Rules

### R1 — Constraints

- The guard must only affect ``IsNull`` lookups; other lookups must remain unchanged.
- The change must not interfere with query iteration or teardown processes.
- Regression tests (38) must continue to pass.
- The raised TypeError should be specific to non‑boolean RHS values.

## References

- `skill_load(name="django-django-11905", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

