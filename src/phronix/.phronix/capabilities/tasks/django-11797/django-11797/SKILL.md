---
name: django-11797
description: The django-11797 subject.
subject: django-11797
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add email field to custom user model |
| `I2` | Instructions | Problem description (I7) |
| `R1` | Rules | Maintain backward compatibility |




## Instructions

### I1 — Add email field to custom user model

In the custom user model file, add an `email = models.EmailField(blank=True, null=True, unique=True)` field, run `python manage.py makemigrations` and `python manage.py migrate` to apply the change.

### I2 — Problem description (I7)

The custom user model lacks an `email` field, causing AttributeError when code accesses `user.email`.

## Rules

### R1 — Maintain backward compatibility

When adding the email field, ensure existing users have a default value or allow nulls to avoid migration failures.

## References
