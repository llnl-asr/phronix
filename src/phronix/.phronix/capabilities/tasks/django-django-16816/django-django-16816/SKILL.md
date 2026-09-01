---
name: django-django-16816
description: Fix admin list_display validation for many‑to‑many and reverse FK fields.
subject: django-django-16816
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `R1` | Rules | Must not break other admin checks |
| `R2` | Rules | Skill vs Memory content |






## Instructions

### I1 — Problem description

Admin list_display validation raises admin.E109 when a many‑to‑many or reverse foreign key field is included, causing a 500 error on the admin page.

### I2 — Key idea

The validation that raises admin.E109 occurs before label generation, so a fallback label change cannot bypass it; the check itself must be modified or guarded.

### I3 — Instructions to solve it

1. Open `django/contrib/admin/checks.py`.
2. Locate the `check_list_display` function that raises `admin.E109` for many‑to‑many or reverse foreign key fields.
3. Add a guard before the error is raised, e.g.:
   ```python
   if isinstance(field, (ManyToManyField, ReverseForeignKey)):
       # Allow these fields in list_display – skip the E109 check
       continue
   ```
4. Ensure the guard only applies when the field name is present in `list_display`.
5. Run the test suite; both `test_invalid_m2m_related_name` and `test_invalid_related_field` should now pass.
6. Verify that no other admin checks are affected by running the full regression suite (123 tests).

## Rules

### R1 — Must not break other admin checks

The modification must only affect the `list_display` validation; ensure that other admin system checks continue to raise their intended errors unchanged.

### R2 — Skill vs Memory content

Only persistent, reusable knowledge (e.g., problem description, core idea, step-by-step fix, constraints) belongs in a skill. Transient observations, experiment logs, or task-specific trial data should be stored as memories, not in the skill.

## References

- `skill_load(name="django-django-16816", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

