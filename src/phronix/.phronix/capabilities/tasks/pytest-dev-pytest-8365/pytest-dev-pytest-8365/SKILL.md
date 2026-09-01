---
name: pytest-dev-pytest-8365
description: Guidance for handling email attribute issues in custom user models during pytest failures.
subject: pytest-dev-pytest-8365
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem it solves |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Never delete a failure entry that remains true |

## Instructions

### I1 — Problem it solves

Failing tests due to a missing `email` attribute on a custom user model when the email is stored in the hash.

### I2 — Key idea

Provide a flexible way to retrieve the email field name, handling custom models that may use a different attribute.

### I3 — Instructions to solve it

1. In the email retrieval code (e.g., `tokens.py`), replace direct `user.email` access with a helper `get_email_field_name(user)` that returns the correct attribute name.
2. Implement `get_email_field_name` to check for known alternatives like `email` and `email_address` using `hasattr` or a mapping.
3. Use `getattr(user, field_name, "")` to obtain the email value safely.
4. Update any model definitions to include the appropriate email attribute if missing, or ensure the helper covers all cases.

### I4 — Constraints and rules

- Do not remove existing email handling logic that other components rely on.
- Ensure that after changes, all target tests that previously passed still pass.
- Maintain backward compatibility: the helper must return a valid email string or empty string without raising errors.
- Preserve the semantics of token generation that expects a non‑empty email where applicable.

### I5 — Pitfalls and lessons

- Simply falling back to an empty string (`getattr(user, "email", "")`) may hide deeper mismatches and cause other failures.
- Renaming the model field to `email_address` without updating all code paths leads to new attribute errors.
- Adding a helper without handling all call sites can leave some modules still using the old direct attribute access.
- Ensure the helper is used consistently; partial adoption can result in inconsistent behavior.

## Rules

### R1 — Never delete a failure entry that remains true

If an attempt fails, keep the record until a later fact proves it resolved.
