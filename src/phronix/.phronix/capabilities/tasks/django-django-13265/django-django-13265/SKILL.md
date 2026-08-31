---
name: django-django-13265
description: The django-django-13265 subject.
subject: django-django-13265
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Reorder migrations |
| `I2` | Instructions | Update Index definition |
| `I3` | Instructions | AlterOrderWithRespectTo migration ordering with _order in Index |
| `I4` | Instructions | What problem it solves |
| `I5` | Instructions | The key idea |
| `I6` | Instructions | Instructions to solve it |
| `I7` | Instructions | Constraints and rules |
| `R1` | Rules | Do not reference `_order` before it exists |

## Instructions

### I1 — Reorder migrations

Place the `AlterOrderWithRespectTo` operation before any `AddIndex` that references the `_order` field in the migration file.

### I2 — Update Index definition

Ensure the index on `_order` combines with another field only after the order is defined, or remove the `_order` index if not needed.

### I3 — AlterOrderWithRespectTo migration ordering with _order in Index

test

### I4 — What problem it solves

A Django migration crashes when `AlterOrderWithRespectTo()` appears after `AddIndex` of the `_order` field in the migration operations list. The crash occurs because `AlterOrderWithRespectTo.database_forwards()` calls `to_model._meta.get_field("_order")` but the `_order` database column hasn't been created yet since `AddIndex` was listed before it. Anyone arriving with a model that has `order_with_respect_to = 'look'` and `models.Index(fields=['look', '_order'])` in their Meta class will see this error if migration order isn't corrected.

### I5 — The key idea

The `_order` field used by `order_with_respect_to` is an auto-created column that must exist before `AlterOrderWithRespectTo` can reference it. The migration optimizer/autodetector must reorder operations so that `AlterOrderWithRespectTo` runs before any `AddIndex` that includes `_order` in its fields — not after, as the default ordering produces.

### I6 — Instructions to solve it

- File: `django/db/migrations/operations/models.py` (the `AlterOrderWithRespectTo` class)
- Identify all `AddIndex` operations in the migration that include `_order` in their fields list (e.g., `models.Index(fields=['look', '_order'])`)
- Reorder the migration operations list so that `AlterOrderWithRespectTo` appears before any `AddIndex` that references `_order`
- The specific change: move `migrations.AlterOrderWithRespectTo(name='lookimage', order_with_respect_to='look')` to a position before `migrations.AddIndex(..., index=models.Index(fields=['look', '_order'], ...))` in the operations list
- After reordering, verify that `AlterOrderWithRespectTo.database_forwards()` will find `_order` already present in the model state when it executes

### I7 — Constraints and rules

- Do NOT modify the `AlterOrderWithRespectTo` class code itself — the operation is correct; the issue is purely ordering
- Do NOT modify any test files
- Do NOT remove or alter the `_order` field definition or `order_with_respect_to` meta option
- The `AddIndex` operations for other fields (`created_at`, `updated_at`) must remain in their relative positions
- Only reorder `AlterOrderWithRespectTo` relative to `AddIndex` operations that include `_order`; do not change other operation orderings
- The fix must be minimal — only swap the position of `AlterOrderWithRespectTo` past the relevant `AddIndex` entries

## Rules

### R1 — Do not reference `_order` before it exists

Any migration that adds an index on `_order` must occur after the `AlterOrderWithRespectTo` that creates the `_order` field.

## References

- `skill_load(name="django-django-13265", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
