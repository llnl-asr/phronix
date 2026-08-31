---
name: django-django-12286
description: The django-django-12286 subject.
subject: django-django-12286
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Allow base language fallback for LANGUAGE_CODE |
| `R1` | Rules | Base language must be present when using sub‑language codes |



## Instructions

### I1 — Allow base language fallback for LANGUAGE_CODE

In `django/core/checks/translation.py` extend the language‑code check to consider the base language when the full sub‑language tag is not present. Build the set of available language tags including the default `'en-us'`. If `settings.LANGUAGE_CODE` is not in this set, split on `'-'` and check the base language. Only return the `E004` error if neither the full code nor the base language is available.

## Rules

### R1 — Base language must be present when using sub‑language codes

If `settings.LANGUAGE_CODE` uses a sub‑language tag (e.g., `de-at`) and the full tag is not listed in `settings.LANGUAGES`, Django should accept the code only when the base language (e.g., `de`) is available. Otherwise, raise `translation.E004`.

## References
