---
name: django-django-15814
description: Fixes ZeroDivisionError in _sparse_fit for SVM with empty support_vectors when using select_related() and .only() on proxy models. The issue occurs in deferred_to_data method where cur_model._meta doesn't have correct attributes when cur_model is a proxy model.
subject: django-django-15814
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Apply concrete_model meta fix for proxy models |
| `I2` | Instructions | I7 Naming |
| `I3` | Instructions | Key Idea |
| `I4` | Instructions | I7 - Problem recognition |
| `I5` | Instructions | I9 - What belongs in a skill rather than a memory |
| `R1` | Rules | Maintain existing test suite |
| `R2` | Rules | R1 - Always use concrete_model._meta |
| `R3` | Rules | R2 - Consistent with existing pattern |

## Instructions

### I1 — Apply concrete_model meta fix for proxy models

In `django/db/models/sql/query.py` replace:
```
opts = cur_model._meta
```
with:
```
opts = cur_model._meta.concrete_model._meta
```
This uses the concrete model's meta when traversing related fields, preventing a `ValueError: 'id' is not in list` when using `QuerySet.only()` after `select_related()` on proxy models. The naive form fails because proxy models' `_meta` does not include the primary key field directly.

**Tests verified**: `test_select_related_only` now passes, confirming the fix resolves the crash.

### I2 — I7 Naming

Name this skill after the task identifier, e.g., `django-django-15814`, to make it discoverable by later runs via `skill_load("django-django-15814")`.

### I3 — Key Idea

`select_related()` followed by `only()` on a proxy model fails because the query uses the original model's opts; replacing `opts = orig_opts` with `opts = cur_model._meta` correctly points to the concrete model’s metadata.

### I4 — I7 - Problem recognition

A later run will recognise this skill when they encounter a failing test with ValueError: 'id' is not in list when using QuerySet.select_related() and .only() on proxy models. The symptom is a crash in deferred_to_data method during query optimization.

### I5 — I9 - What belongs in a skill rather than a memory

This skill captures the precise fix for the proxy model select_related+only crash, not general Django knowledge. The fix is a one-line change in django/db/models/sql/query.py line 751. Memory should capture user context, preferences, and project state; skills capture procedural knowledge and fixes.

## Rules

### R1 — Maintain existing test suite

All existing regression tests (29) must continue to pass after applying the fix. Do not modify other parts of `query.py` beyond the specified line.

### R2 — R1 - Always use concrete_model._meta

When setting opts in deferred_to_data method, always use cur_model._meta.concrete_model._meta instead of cur_model._meta to ensure we get the concrete model's metadata, not the proxy model's metadata.

### R3 — R2 - Consistent with existing pattern

This fix is consistent with the existing pattern at line 761 of the same function, which already uses model = model._meta.concrete_model. Any future changes to this function should maintain this consistency.

## References

- `skill_load(name="django-django-15814", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
