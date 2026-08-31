---
name: django-django-12708
description: Fix migration crash when deleting index_together with unique_together in Django 1.11.10
subject: django-django-12708
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I1 Problem description |


## Instructions

### I1 — I1 Problem description

Migration crashes when deleting an index_together that shares fields with a unique_together in Django 1.11.10. The error occurs in django/db/backends/base/schema.py: ValueError: Found wrong number (2) of constraints.

## Rules

## References
