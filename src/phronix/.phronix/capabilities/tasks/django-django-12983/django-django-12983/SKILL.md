---
name: django-django-12983
description: The django-django-12983 subject.
subject: django-django-12983
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix slugify to strip leading/trailing dashes and underscores |
| `I2` | Instructions | Problem description |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Naming convention for skills |
| `I5` | Instructions | Django Issue 12983 Diagnosis |
| `R1` | Rules | Do not alter other behavior of slugify |

## Instructions

### I1 — Fix slugify to strip leading/trailing dashes and underscores

In `django/utils/text.py`, modify `slugify` to return `re.sub(r'[-\s]+', '-', value).strip('-_')` instead of just `re.sub(r'[-\s]+', '-', value)`. This removes leading and trailing dashes and underscores from the slug.

**Why**: The original implementation left leading/trailing dashes and underscores (e.g., `___this-is-a-test-`). Stripping them produces a clean slug (`this-is-a-test`). This change fixes the failing test expecting the cleaned output.

**Tests**: The `test_slugify` test now expects the output without leading/trailing characters.

### I2 — Problem description

The slugify function returns strings with trailing hyphens or underscores, causing failing tests that expect clean slugs without trailing punctuation.

### I3 — Key idea

Strip trailing hyphens and underscores after slug generation by chaining `.strip('-_')` to the existing regex replacement.

### I4 — Naming convention for skills

Skill names should be the task identifier followed by the task ID, e.g., `django-django-12983`, to ensure later runs can load the skill directly via `skill_load("django-django-12983")`.

### I5 — Django Issue 12983 Diagnosis

Django issue #12983 (task 272, django__django-12983) research context.

User instructions: "If the diagnosis is incomplete, write what you have. A partial fix the next attempt can build on is worth more than a complete one it never sees." User also: "Do not diagnose again, do not read the source again, do not attempt the task: take what is there and file it." User emphasized exact-name lookup: "the next attempt looks it up by that name and by nothing else"

Available context from exploration:
- Django forms, views, utils structure examined
- research.py infrastructure: assess(), define_fom(), add_approach(), choose(), write_plan()
- research-2.md does not exist at expected path (main blocker)
- Memory files in cache paths but not as task-level research documents
- Django code patterns: forms widgets, _make_hash_value, view decorators, URL patterns
- Research methodology: approach evaluation with train/validate/test, FOM, operation kinds

This skill captures the available diagnosis context from the exploration of Django issue #12983 in task 272, structured for exact-name lookup by the next attempt.

## Rules

### R1 — Do not alter other behavior of slugify

Ensure the change only strips trailing hyphens/underscores; other slugify functionality must remain unchanged, and all existing tests must continue to pass.

## References
