---
name: django-django-13315
description: Fix for duplicate options in limit_choices_to with Q objects involving joins
subject: django-django-13315
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7 Identify the symptom |
| `I2` | Instructions | I9 Skill vs Memory guidance |
| `I3` | Instructions | limit_choices_to with Q objects and joins |
| `R1` | Rules | R1 Invariant: existing tests must continue to pass |

## Instructions

### I1 — I7 Identify the symptom

When a test fails due to duplicate choices in a Django admin ForeignKey formfield, recognize it as the `limit_choices_to` Q‑object join issue.

### I2 — I9 Skill vs Memory guidance

Store factual, repeatable knowledge (the duplicate‑option cause and the distinct() fix) as a skill. Record session‑specific observations (e.g., environment setup steps, failed attempts) in memories, not in this skill.

### I3 — limit_choices_to with Q objects and joins

When limit_choices_to contains a Q object involving a join, applying it via complex_filter can produce duplicate options in form fields. After calling complex_filter(limit_choices_to), always call .distinct() on the queryset to deduplicate results. This ensures unique options in admin form fields, especially when the Q object involves joins across related models.

## Rules

### R1 — R1 Invariant: existing tests must continue to pass

Do not change behavior of unrelated fields; ensure only the queryset for the affected ForeignKey is made distinct.

## References
