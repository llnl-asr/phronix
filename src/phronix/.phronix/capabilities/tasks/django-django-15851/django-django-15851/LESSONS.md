# Lessons — django-django-15851

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — The previous attempt added an extra_files watch for the settings file 

**2026-08-29** — The previous attempt added an extra_files watch for the settings file in django/utils/autoreload.py, but the target test `test_non_template_changed_in_template_directory` still failed because `autoreload.template_changed` incorrectly returned True for non‑template file changes inside a template directory. The watch logic did not handle directory‑level changes correctly.
