---
name: sphinx-doc-issue-10451
description: The sphinx-doc-issue-10451 subject.
subject: sphinx-doc-issue-10451
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I1 — Problem |
| `I2` | Instructions | I2 — Key idea |
| `I3` | Instructions | I3 — Instructions to solve it |
| `R1` | Rules | R1 — Constraints |





## Instructions

### I1 — I1 — Problem

The email is stored in the user hash but a custom user model lacks an `email` attribute, causing a TypeError during token generation.

### I2 — I2 — Key idea

Add an explicit `email` field to the custom user model so that token generation can access it without error.

### I3 — I3 — Instructions to solve it

1. Open the custom user model file (e.g., `models.py`).
2. Add `email = models.EmailField(null=True, blank=True)` to the class.
3. Run migrations: `python manage.py makemigrations` and `python manage.py migrate`.
4. Ensure any code accessing `user.email` now works; remove fallback attribute code if present.
5. Re‑run the failing tests; `test_user_email` should now pass.
6. Verify that template rendering no longer raises `UndefinedError` for missing email.

## Rules

### R1 — R1 — Constraints

Do not remove existing fallback attribute code until all code paths that rely on it are updated, otherwise unrelated features may break.

## References

- `skill_load(name="sphinx-doc-issue-10451", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

