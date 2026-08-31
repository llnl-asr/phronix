---
name: django-django-11039
description: The django-django-11039 subject.
subject: django-django-11039
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add fallback for missing cgi module in wsgi and multipartparser |
| `I2` | Instructions | django#11039 sqlmigrate transaction wrapping |
| `R1` | Rules | django#11039 sqlmigrate constraints |

## Instructions

### I1 — Add fallback for missing cgi module in wsgi and multipartparser

Wrap import cgi in try/except and provide minimal stub with parse_header (and valid_boundary for multipartparser) to avoid ImportError on Python 3.11+.

Also adjust sqlmigrate Command to set self.output_transaction = migration.atomic and connection.features.can_rollback_ddl to avoid BEGIN/COMMIT on non‑transactional DBs.

These changes fix failing tests for sqlmigrate and ensure imports work in minimal environments.

### I2 — django#11039 sqlmigrate transaction wrapping

The sqlmigrate command wraps SQL output in BEGIN/COMMIT transaction boundaries based solely on migration.atomic, but this is incorrect for databases that don't support DDL rollback. The fix requires changing line 59 in sqlmigrate.py from `self.output_transaction = migration.atomic` to `self.output_transaction = migration.atomic and connection.features.can_rollback_ddl` to ensure transaction wrapping only occurs when both the migration is atomic AND the database supports DDL rollback.

## Rules

### R1 — django#11039 sqlmigrate constraints

1. Do not modify any test files - the fix must make existing tests pass without changes to test files.
2. The change must use AND logic: `migration.atomic and connection.features.can_rollback_ddl`, not OR logic. Adding can_rollback_ddl as an OR condition would incorrectly wrap transactions for atomic migrations on databases that cannot rollback DDL.
3. Do not alter migration model logic, migration loader, or executor - only change the command's output_transaction assignment in sqlmigrate.py.
4. The fix must work for both forwards and backwards migration SQL generation - the same atomicity rules apply to both.
5. Do not add new imports - the `connection` object is already available in the handle method via connections[options['database']].

## References

- `skill_load(name="django-django-11039", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
