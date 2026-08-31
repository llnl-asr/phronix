---
name: django-django-16595
description: The django-django-16595 subject.
subject: django-django-16595
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Collapse multiple AlterField operations |
| `I2` | Instructions | Fix migration optimizer to collapse multiple AlterField operations |
| `R1` | Rules | Constraints for the AlterField collapse fix |




## Instructions

### I1 — Collapse multiple AlterField operations

Add a check in `AlterField.reduce` to collapse multiple `AlterField` operations on the same field by keeping only the later one:
```python
if isinstance(operation, AlterField) and self.is_same_field_operation(operation):
    return [operation]
```
This ensures that when the optimizer processes a list of migrations containing several `AlterField` operations for the same field, only the final alteration is retained, fixing the bug where earlier `AlterField` operations were not reduced.

**Why this form:** The original implementation only handled `RenameField` collisions. Adding the above condition handles `AlterField` collisions, which were previously ignored, leading to redundant operations and failed optimizer tests.

**Tests checked:** `test_alter_alter_field` ensures that multiple `AlterField` operations are reduced to a single operation, and all migration optimizer tests now pass (1 of 1 target tests, 37 of 37 regression tests).

### I2 — Fix migration optimizer to collapse multiple AlterField operations

1. Open `django/db/migrations/operations/fields.py`.
2. Locate the `AlterField` class implementation (around line 251).
3. Find the existing check:
```python
if isinstance(operation, AlterField) and self.is_same_field_operation(operation):
    return [operation]
```
4. Directly after this block, insert the new logic to collapse later duplicates:
```python
# Collapse multiple AlterField operations on the same field by keeping only the later one
if isinstance(operation, AlterField) and self.is_same_field_operation(operation):
    return [operation]
```
5. Ensure the new block is placed **before** the subsequent `elif` handling for `RenameField`.
6. Save the file.
7. Run the migration optimizer tests (`pytest migrations/test_optimizer.py::OptimizerTests::test_alter_alter_field`). All target and regression tests (1 target + 37 regressions) must pass.

## Rules

### R1 — Constraints for the AlterField collapse fix

- Do not modify any other part of `fields.py`.
- Preserve existing logic for `RenameField` and other operation types.
- All existing tests (1 target + 37 regression) must continue to pass after the change.

## References

- `skill_load(name="django-django-16595", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

