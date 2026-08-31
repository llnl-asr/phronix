---
name: django-django-13220
description: Fix ValidationError equality and hashability in Django core exceptions.
subject: django-django-13220
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add __eq__ method to ValidationError |
| `I2` | Instructions | Add __hash__ method to ValidationError |
| `R1` | Rules | Preserve existing message handling |
| `R2` | Rules | Maintain compatibility with field errors |

## Instructions

### I1 — Add __eq__ method to ValidationError

In django/core/exceptions.py, inside class ValidationError, define __eq__(self, other) that returns True when other is ValidationError and set(self.messages) == set(other.messages).

### I2 — Add __hash__ method to ValidationError

Define __hash__(self) returning hash of tuple(sorted(self.messages)). This makes ValidationError hashable based on its messages.

## Rules

### R1 — Preserve existing message handling

Do not alter the existing __init__ signature or message storage; ensure self.messages remains a list of messages as before.

### R2 — Maintain compatibility with field errors

Equality should compare flattened message sets regardless of whether messages come from field errors or non_field_errors.
