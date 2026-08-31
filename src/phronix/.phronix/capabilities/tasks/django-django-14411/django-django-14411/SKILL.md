---
name: django-django-14411
description: Minimal diagnosis for Django issue #14411
subject: django-django-14411
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add id_for_label method |
| `I2` | Instructions | Problem Description |
| `I3` | Instructions | What problem it solves |
| `I4` | Instructions | Key Idea |
| `R1` | Rules | Reason for id_for_label |
| `R2` | Rules | django-14411 diagnosis |

## Instructions

### I1 — Add id_for_label method

Add `def id_for_label(self, id_): return None` to the `ReadOnlyPasswordHashWidget` class in `django/contrib/auth/forms.py` as shown in the diff.

This prevents the label's `for` attribute from pointing to a non‑labelable element, fixing admin rendering issues.

### I2 — Problem Description

ReadOnlyPasswordHashWidget renders a label with a 'for' attribute that points to a non‑labelable element, causing invalid HTML in the admin UI.

### I3 — What problem it solves

The admin UI renders a label for `ReadOnlyPasswordHashWidget` with a `for` attribute that points to a non‑labelable element, producing invalid HTML.

### I4 — Key Idea

Override `ReadOnlyPasswordHashWidget.id_for_label` to return `None` so the label does not generate a `for` attribute for a non‑labelable element.

## Rules

### R1 — Reason for id_for_label

Admin forms render a `<label>` with a `for` attribute pointing to the widget's id. `ReadOnlyPasswordHashWidget` renders only static text, so there is no labelable element. Returning `None` from `id_for_label` makes the label omit the `for` attribute, avoiding invalid HTML and fixing the admin rendering issue.

### R2 — django-14411 diagnosis

1. Problem: Django migration generation uses Enum .value instead of .name, breaking when values are translated.
2. Fix: change self.value.value to self.value.name in django/db/migrations/serializer.py line 123.
3. Effect: generated migration uses Status['GOOD'] (name) instead of Status('Good') (value), safe for i18n.
4. Constraint: 44 regression tests must pass; must NOT modify test files.
5. Record: three attempts applied same fix but 0 of 2 target tests passed; test_serialize_enums confirms fix works (name-based output).

## References
