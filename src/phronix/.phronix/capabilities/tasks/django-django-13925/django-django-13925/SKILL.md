---
name: django-django-13925
description: The django-django-13925 subject.
subject: django-django-13925
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Placeholder |
| `I2` | Instructions | Problem Symptom |
| `I3` | Instructions | Key Idea |
| `I4` | Instructions | Instructions |
| `R1` | Rules | Constraints |






## Instructions

### I1 — Placeholder

Placeholder for skill content

### I2 — Problem Symptom

Tests `test_auto_created_inherited_pk` and `test_explicit_inherited_pk` fail with warning `models.W042` about auto‑created primary key on inherited models, even when a primary key is defined in the base model.

### I3 — Key Idea

The global `DEFAULT_AUTO_FIELD` only applies to models **without** an explicit primary key; inherited models retain their own primary key definition, so the warning persists.

### I4 — Instructions

1. Edit `django/conf/global_settings.py` and change:
   ```diff
   -DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
   +DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
   ```
2. Run the test suite.
3. Observe that the two target tests still fail with `models.W042` warnings.
4. No further changes were made in this attempt.

## Rules

### R1 — Constraints

* All existing regression tests (24) must continue to pass.
* Do not modify files other than `django/conf/global_settings.py` in this step.
* The fix must eliminate `models.W042` warnings for inherited models without introducing new warnings.

## References
