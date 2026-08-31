---
name: django-django-12497
description: The django-django-12497 subject.
subject: django-django-12497
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix ambiguous relationship hint for ManyToManyField |
| `I2` | Instructions | Diagnosis for django-django-12497 task |

## Instructions

### I1 — Fix ambiguous relationship hint for ManyToManyField

Revert the hint messages in `django/db/models/fields/related.py` for the ambiguous relationship errors back to the original multi‑line string. Replace the single‑line hint:
```python
hint='Use ManyToManyField with symmetrical=False and through="%s".' % relationship_model_name
```
with the original multi‑line hint:
```python
hint=(
    'If you want to create a recursive relationship, '
    'use ForeignKey("%s", symmetrical=False, through="%s").'
) % (
    RECURSIVE_RELATIONSHIP_CONSTANT,
    relationship_model_name,
)
```
This restores the expected hint text so that `test_ambiguous_relationship_model_from` and `test_ambiguous_relationship_model_to` compare the hint correctly and pass.

### I2 — Diagnosis for django-django-12497 task

Task: django-django-12497

This is a Django research task involving investigation of framework behavior and test validation.

Key findings from previous attempts:
- Attempt-1, attempt-2, and attempt-3 have been made on this task
- The last attempt (attempt-3) passed 0 of 1 target test(s)
- Two tests were broken by previous fixes: test_group_by_exists_annotation and test_group_by_subquery_annotation
- Research focused on Django framework investigation with validation of ideas

Research context:
- Research memories exist including research-validate-ideas-pytest-5227 and research-playbook-prevented-retry-waste
- The task involves Django codebase investigation and test fix validation

Diagnosis:
- Previous attempts have explored various approaches to fix the issue
- The fix that was applied broke 2 previously passing tests
- 0 of 1 target tests pass, indicating the core issue remains unfixed
- Need to investigate what specific aspect of the Django framework the task target test is testing
- Previous fixes likely addressed symptoms rather than root cause

Important: The next attempt will look up this skill by exact name "django-django-12497" and by nothing else. A partial diagnosis filed here is valuable for the next attempt to build upon, rather than no diagnosis at all.

## References
