---
name: django-django-13033
description: Fix ordering of queryset involving self‑referencing foreign key.
subject: django-django-13033
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem it solves |
| `I2` | Instructions | Key idea |



## Instructions

### I1 — Problem it solves

Self‑referencing foreign‑key ordering produces incorrect SQL ordering (unexpected DESC) when using `order_by('record__root_id')` on a queryset, causing tests to fail.

### I2 — Key idea

The default ordering defined on the self‑referencing model (`ordering = ('-id',)`) propagates through joins, overriding an explicit `order_by` on a related field.

## Rules

## References
