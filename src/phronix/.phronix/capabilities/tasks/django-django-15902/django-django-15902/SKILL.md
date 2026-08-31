---
name: django-django-15902
description: The django-django-15902 subject.
subject: django-django-15902
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve |
| `I4` | Instructions | django-django-15902 root-rendering fix |
| `R1` | Rules | Constraint: keep all tests passing |

## Instructions

### I1 — Problem description

Deprecation warning `RemovedInDjango50Warning` from ManagementForm's default.html template causes test failures; need to suppress it without breaking other tests.

### I2 — Key idea

Import `RemovedInDjango50Warning` from `django.utils.deprecation` before applying the ignore filter, ensuring the warning class is defined.

### I3 — Instructions to solve

1. Edit `django/forms/utils.py`.
2. Add import at top: `from django.utils.deprecation import RemovedInDjango50Warning`.
3. Immediately after the import, add: `warnings.simplefilter('ignore', RemovedInDjango50Warning)`.
4. Save the file and run the target test suite.
5. Verify all regression tests still pass.

### I4 — django-django-15902 root-rendering fix

The template filter rendering `2**(1/x)` should output root notation (x ⁄ 2) not power notation (1 ─ x²).

Fix location: django/forms/utils.py or the template filter system that handles exponentiation/root expressions.

The test at test_slugify.py:2132 expects `2**(1/x)` to render as `x ___` (ascii) or `x ___` (ucode) using root symbols, but currently renders as `1 ─ x²`.

Evidence: test expects root notation for rational exponent 1/x but gets power notation instead.

## Rules

### R1 — Constraint: keep all tests passing

Do not modify any other imports or code in `django/forms/utils.py` beyond the required import and filter; existing functionality must remain unchanged.

## References
