---
name: django-django-14608
description: The django-django-14608 subject.
subject: django-django-14608
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Implement change |
| `I4` | Instructions | Add nonform CSS class for non-form errors in FormSets |
| `R1` | Rules | Maintain existing test suite |
| `R2` | Rules | Do not break non‑field error handling |

## Instructions

### I1 — Problem description

FormSets should include a `nonform` CSS class for non‑form errors, enabling custom styling distinct from form and non‑field errors.

### I2 — Key idea

Set the error list for non‑form errors with `error_class='nonform'` and ensure validation bounds propagate correctly.

### I3 — Implement change

1. In `django/forms/formsets.py` modify `BaseFormSet.__init__` to create `self._non_form_errors = self.error_class(error_class='nonform')`.
2. Extend validation logic in `BaseFormSet` to handle `validate_max`/`validate_min` when `max_num`/`min_num` conflict with `TOTAL_FORMS`, ensuring non‑form errors are added appropriately.

### I4 — Add nonform CSS class for non-form errors in FormSets

## Rules

### R1 — Maintain existing test suite

All existing regression tests (394) must continue to pass after changes.

### R2 — Do not break non‑field error handling

The existing `nonfield` CSS class behavior for forms must remain unchanged.

## References
