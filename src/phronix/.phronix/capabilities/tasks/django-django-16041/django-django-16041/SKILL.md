---
name: django-django-16041
description: The django-django-16041 subject.
subject: django-django-16041
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Filter out empty_permitted from form kwargs |
| `I2` | Instructions | Diagnosis of empty_permitted KeyError in Django formsets |
| `R1` | Rules | Preserve existing functionality |
| `R2` | Rules | Maintain test coverage |

## Instructions

### I1 — Filter out empty_permitted from form kwargs

In `django/forms/formsets.py`, locate the line constructing the form:
```python
**self.get_form_kwargs(None),
```
Replace it with:
```python
**{k: v for k, v in self.get_form_kwargs(None).items() if k != 'empty_permitted'},
```
This prevents the `empty_permitted` argument from being passed to `empty_form`.

### I2 — Diagnosis of empty_permitted KeyError in Django formsets

## Rules

### R1 — Preserve existing functionality

Do not modify any other arguments or logic in the form construction. All other kwargs must be passed unchanged.

### R2 — Maintain test coverage

After applying the change, ensure all target tests (2) and regression tests (113) pass.

## References

- `skill_load(name="django-django-16041", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
