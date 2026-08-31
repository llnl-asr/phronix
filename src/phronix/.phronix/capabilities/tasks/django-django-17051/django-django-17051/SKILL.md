---
name: django-django-17051
description: Skill for handling bulk_create returning IDs with update_conflicts in Django
subject: django-django-17051
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem solved |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Change to apply |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |
| `I6` | Instructions | Task overview |
| `I7` | Instructions | Approach investigation |
| `R1` | Rules | Do not modify test files |
| `R2` | Rules | Make minimal changes |

## Instructions

### I1 — Problem solved

Bulk create with update_conflicts should return primary key IDs, but currently asserts length mismatch causing test failures.

### I2 — Key idea

The returned_columns list is only populated when the connection supports returning rows and on_conflict is None; we need to allow it when on_conflict is set for update_conflicts.

### I3 — Change to apply

In django/db/models/query.py, modify the condition at line 812 to remove the `and on_conflict is None` check, ensuring the assertion only runs when returned_columns are provided.

### I4 — Constraints and rules

Do not disturb the behavior for ignore_conflicts; the test `test_ignore_conflicts_ignore` must continue to pass. Preserve existing bulk insert behavior for databases without RETURNING support.

### I5 — Pitfalls and lessons

Removing the check caused regression in ignore_conflicts test. Future changes must verify both update_conflicts and ignore_conflicts scenarios.

### I6 — Task overview

This skill covers the Django bulk_create returning IDs issue when update_conflicts is used. The problem is that primary keys are not returned in the queryset when update_conflicts=True is set. Investigate the bulk_create code path, particularly how returning_fields is handled in conflict resolution, and find where to add RETURNING my_model.id clause.

### I7 — Approach investigation

Start by examining django/db/models/query.py for the bulk_create method and _batched_insert. Look at how returning_fields is constructed and where it gets removed during conflict handling. The key is to discriminate cases so that returning_fields are kept in the case of update_conflicts, unlike ignore_conflicts where PostgreSQL may not return IDs.

## Rules

### R1 — Do not modify test files

Only edit source code, not tests.

### R2 — Make minimal changes

The smallest change that genuinely fixes the described problem.
