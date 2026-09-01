---
name: django-django-11797
description: The django-django-11797 subject.
subject: django-django-11797
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix import error for jinja2 pass_environment |


## Instructions

### I1 — Fix import error for jinja2 pass_environment

Update `sphinx/util/rst.py` to import `pass_environment` from `jinja2` using the correct name:
```python
from jinja2 import pass_environment as environmentfilter
```
This resolves the ImportError raised during test collection.

## Rules

## References

- `skill_load(name="django-django-11797", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

