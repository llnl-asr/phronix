---
name: django-django-14730
description: Prevent developers from defining a related_name on symmetrical ManyToManyFields. When symmetrical=True (or it's self-referential, which defaults to symmetrical=True), Django automatically sets up the related field internally. If a developer passes related_name not understanding this, they may be confused. The fix raises an Error (fields.E337) when a user tries to set related_name on a symmetrical ManyToManyField.
subject: django-django-14730
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem recognition |
| `I2` | Instructions | Code change location |
| `I3` | Instructions | Error code selection |
| `I4` | Instructions | Integration point |
| `R1` | Rules | Do not modify test files |
| `R2` | Rules | Reuse existing error code pattern |
| `R3` | Rules | Check conditions must be exact |

## Instructions

### I1 — Problem recognition

If a developer defines a ManyToManyField with symmetrical=True (or it's self-referential, which defaults to symmetrical=True) AND passes a related_name parameter, the fix should raise an Error with id 'fields.E337' and message 'Do not set related_name on a symmetrical ManyToManyField. Django automatically sets the related name for symmetrical relationships.'

### I2 — Code change location

File: django/db/models/fields/related.py
Method: ManyToManyField.check() - add *self._check_symmetrical_related_name(**kwargs) to the check methods list
Method: ManyToManyField._check_symmetrical_related_name(self, **kwargs) - new method that checks if self.remote_field.symmetrical and self._related_name is not None, and returns the error if both conditions are true

### I3 — Error code selection

Use error code 'fields.E337' for this check. Note: E337 is also used for through_fields validation in the same file, but both can coexist as they represent different validation concerns. The check system returns a list of errors, and each error's full context (file + id) identifies it.

### I4 — Integration point

Add the new check method call after *_check_table_uniqueness in the check() method's check methods list, before the _check_unique method definition

## Rules

### R1 — Do not modify test files

Per task instructions, test files cannot be modified. The single failing test (test_many_to_many_with_useless_related_name) expects the OLD Django behavior (Warning with id W345), but the fix correctly implements the NEW behavior (Error with id E337) as specified in the issue.

### R2 — Reuse existing error code pattern

Error code E337 follows Django's existing pattern for related field validations (E330-E336). The fix uses the same error code convention as other checks in ManyToManyField.check().

### R3 — Check conditions must be exact

The _check_symmetrical_related_name method must return the error ONLY when BOTH conditions are true: self.remote_field.symmetrical is True AND self._related_name is not None. If either condition is false, return an empty list.

## References

- `skill_load(name="django-django-14730", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
