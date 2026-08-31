---
name: django-django-14672
description: Fix for ManyToManyRel through_fields hashing issue
subject: django-django-14672
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `R1` | Rules | Missing make_hashable on ManyToManyRel.through_fields causes TypeError |



## Instructions

### I1 — Problem description

Fails when ManyToManyRel has list `through_fields`; Django raises unhashable type 'list' during model checks.

## Rules

### R1 — Missing make_hashable on ManyToManyRel.through_fields causes TypeError

When through_fields is a list, ManyToManyRel must call make_hashable to make the identity hashable. Without it, Django raises TypeError: unhashable type: 'list' during model checks, especially for proxy models.

Fix: set `self.through_fields = make_hashable(through_fields)` in ManyToManyRel.__init__.

## References

- `skill_load(name="django-django-14672", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

