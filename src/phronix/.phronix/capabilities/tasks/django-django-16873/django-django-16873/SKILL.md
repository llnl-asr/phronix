---
name: django-django-16873
description: Fix join filter escaping behavior when autoescape is off
subject: django-django-16873
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update join filter to respect autoescape flag for separator |
| `R1` | Rules | Preserve existing escaping for values |
| `R2` | Rules | Do not alter other defaultfilter behavior |

## Instructions

### I1 — Update join filter to respect autoescape flag for separator

In `django/template/defaultfilters.py`, modify the `join` function: replace the line `data = conditional_escape(arg).join(value)` with `data = (conditional_escape(arg) if autoescape else arg).join(value)`.

## Rules

### R1 — Preserve existing escaping for values

When `autoescape` is True, each element in `value` must still be escaped via `conditional_escape` before joining.

### R2 — Do not alter other defaultfilter behavior

Only the handling of the separator `arg` should be conditional; the rest of the function remains unchanged.
