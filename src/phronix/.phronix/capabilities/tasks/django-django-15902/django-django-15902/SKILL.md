---
name: django-django-15902
description: The django-django-15902 subject.
subject: django-django-15902
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | django-django-15902 root-rendering fix |


## Instructions

### I1 — django-django-15902 root-rendering fix

The template filter rendering `2**(1/x)` should output root notation (x ⁄ 2) not power notation (1 ─ x²).

Fix location: django/forms/utils.py or the template filter system that handles exponentiation/root expressions.

The test at test_slugify.py:2132 expects `2**(1/x)` to render as `x ___` (ascii) or `x ___` (ucode) using root symbols, but currently renders as `1 ─ x²`.

Evidence: test expects root notation for rational exponent 1/x but gets power notation instead.

## Rules

## References
