---
name: django-16255
description: The django-16255 subject.
subject: django-16255
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem solved |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions |
| `R1` | Rules | Constraints and rules |





## Instructions

### I1 — Problem solved

Sitemaps without items raise a ValueError on callable lastmod. The fix handles sitemaps where get_latest_lastmod raises ValueError when there are no items.

### I2 — Key idea

Catch both TypeError and ValueError when computing lastmod for empty sitemap to avoid max() on empty sequence.

### I3 — Instructions

1. Edit `django/contrib/sitemaps/__init__.py`.
2. Locate the `get_latest_lastmod` method.
3. Change the `except TypeError:` line to `except (TypeError, ValueError):`.
4. Save the file and run the test suite to ensure all tests pass.

## Rules

### R1 — Constraints and rules

- Must not alter behavior for non‑empty sitemaps.
- All existing regression tests (36) must continue to pass.
- Do not modify any other exception handling in the file.
- Preserve the original logic of `get_latest_lastmod` beyond the added exception types.

## References

- `skill_load(name="django-16255", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

