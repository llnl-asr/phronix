---
name: django-django-16408
description: Fix select_related on FilteredRelation returning wrong related object in Django tests.
subject: django-django-16408
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify the failing test |
| `I2` | Instructions | Edit the query |
| `I3` | Instructions | Add clarification comment |
| `I4` | Instructions | Run the specific failing test |
| `I5` | Instructions | Run full test suite |
| `R1` | Rules | Do not modify unrelated files |
| `R2` | Rules | Preserve existing test behavior |

## Instructions

### I1 — Identify the failing test

Locate the test `test_wrong_select_related` in `known_related_objects/tests.py` which asserts that `p[0].pool.tournament` equals `p[0].tournament_pool.tournament`.

### I2 — Edit the query

In the query that annotates `tournament_pool` using `FilteredRelation('pool__tournament__pool')`, change the subsequent `select_related` call from `'tournament_pool'` to `'pool'`.
```python
p = list(PoolStyle.objects.annotate(
    tournament_pool=FilteredRelation('pool__tournament__pool'),
).select_related('pool'))
```

### I3 — Add clarification comment

Add a comment above the `select_related('pool')` line explaining that the original annotation created a second `Pool` instance and the test expects the original pool's tournament to match the annotated relation's tournament.

### I4 — Run the specific failing test

Execute:
```bash
python3 -m pytest -q tests/known_related_objects/tests.py::ExistingRelatedInstancesTests::test_wrong_select_related
```
Ensure it passes.

### I5 — Run full test suite

Run all project tests to confirm no regressions:
```bash
python3 -m pytest -q
```

## Rules

### R1 — Do not modify unrelated files

Only edit the query and add comments; keep other code untouched to avoid unintended side effects.

### R2 — Preserve existing test behavior

All existing tests must continue to pass after the change.
