---
name: django-django-17051
description: Skill for handling bulk_create returning IDs with update_conflicts in Django
subject: django-django-17051
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Task overview |
| `I2` | Instructions | Approach investigation |
| `R1` | Rules | Do not modify test files |
| `R2` | Rules | Make minimal changes |

## Instructions

### I1 — Task overview

This skill covers the Django bulk_create returning IDs issue when update_conflicts is used. The problem is that primary keys are not returned in the queryset when update_conflicts=True is set. Investigate the bulk_create code path, particularly how returning_fields is handled in conflict resolution, and find where to add RETURNING my_model.id clause.

### I2 — Approach investigation

Start by examining django/db/models/query.py for the bulk_create method and _batched_insert. Look at how returning_fields is constructed and where it gets removed during conflict handling. The key is to discriminate cases so that returning_fields are kept in the case of update_conflicts, unlike ignore_conflicts where PostgreSQL may not return IDs.

## Rules

### R1 — Do not modify test files

Only edit source code, not tests.

### R2 — Make minimal changes

The smallest change that genuinely fixes the described problem.
