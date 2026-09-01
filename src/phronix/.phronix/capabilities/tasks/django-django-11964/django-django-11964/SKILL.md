---
name: django-django-11964
description: When accessing a TextChoices field, __str__ returns the enum member rather than its value, causing type mismatch in tests.
subject: django-django-11964
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7: Problem description |
| `I2` | Instructions | I9: Skill vs Memory |



## Instructions

### I1 — I7: Problem description

When a model field uses a Django TextChoices enum, the stored value is the enum member (e.g., `MyChoice.FIRST_CHOICE`) instead of the raw underlying string (`"first"`). This causes tests that expect a plain string to fail.

### I2 — I9: Skill vs Memory

Store the problem description, key idea, step‑by‑step fix, constraints and pitfalls in this skill. Use memories only for non‑code facts such as project decisions, dates, or user preferences. The fix itself belongs in a skill so later runs can load it directly.

## Rules

## References

- `skill_load(name="django-11964", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

