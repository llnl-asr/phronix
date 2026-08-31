---
name: django-django-11742
description: Fix custom user model email attribute mismatch
subject: django-django-11742
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify missing email attribute in custom user model |


## Instructions

### I1 — Identify missing email attribute in custom user model

Search the codebase for references to `user.email`. Verify if the custom user model defines `email_address` instead of `email`. If so, note the field name discrepancy.

## Rules

## References
