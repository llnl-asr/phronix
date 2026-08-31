---
name: django-django-16820
description: The django-django-16820 subject.
subject: django-django-16820
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints |





## Instructions

### I1 — Problem description

Deprecation warnings appear when squashing migrations that use `Meta.index_together`. The task is to transition these to `Meta.indexes` to eliminate the warnings.

### I2 — Key idea

Deprecation warnings stem from Django's migration handling of `Meta.index_together` vs `Meta.indexes`; the fix requires updating migration generation logic to correctly translate `index_together` into `Index` objects and handle circular foreign‑key dependencies.

### I3 — Instructions to solve it

1. Open `django/db/migrations/optimizer.py` (or the relevant file handling migration optimization).
2. Locate the logic that processes `Meta.index_together` in the `AutoModel` migration generation.
3. Replace the code that creates `AddIndex` operations for `index_together` with a call that creates proper `Index` objects using `Meta.indexes` when present.
4. Ensure that when both `index_together` and `indexes` are defined, the generated migration does not create duplicate indexes.
5. Update the circular foreign‑key handling in `AutoModel` to correctly order operations so that `AddIndex` is applied after the related model is created.
6. Run the target test suite; the deprecation warnings should disappear and the tests `test_add_model_order_with_respect_to_index`, `test_create_model_with_indexes`, `test_create_model_index_together_rename_index`, `test_create_model_remove_index`, `test_create_model_remove_index_together_rename_index`, `test_same_app_circular_fk_dependency_with_unique_together_and_indexes` should now pass.
7. Commit the changes and re‑run the full regression suite to confirm no new failures.

## Rules

### R1 — Constraints

- Existing regression tests (203) must continue to pass.
- No duplicate indexes should be created when both `Meta.index_together` and `Meta.indexes` are present.
- Migration generation must preserve the order of operations for circular foreign‑key dependencies.
- The solution must not rely on external stubs (e.g., the earlier `asgiref` stub approach).

## References
