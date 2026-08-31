---
name: django-django-15252
description: The django-django-15252 subject.
subject: django-django-15252
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis for Django SWE-bench issue #15252 |
| `I2` | Instructions | What problem it solves |
| `I3` | Instructions | The key idea |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Constraints and rules |







## Instructions

### I1 — Diagnosis for Django SWE-bench issue #15252

SWE-bench task django-django-15252: Django Admin list_filter choice wrapping issue.

Problem: In Django's ModelAdmin list_filter, many choice options cause poor wrapping/display in the admin interface. Long choice values overflow or wrap awkwardly, making the filter difficult to use.

Key insights from related fixes in this task's git history:
- #26872: Fixed wrapping of long choices in ModelAdmin.list_filter
- #31617: Removed redundant title text in filter.html
- d5f2d5d604: Fixed wrapping of long values in technical 500 debug page

Core diagnosis:
- The list_filter choice rendering in filter.html needs CSS/structural improvements for long values
- Fix should add max-width or inline styling to prevent overflow
- Related to the pattern of wrapping fixes already applied in this codebase

Actionable next step: Review filter.html changes from commit 950d697b95 and apply wrapping constraints to list_filter choice elements.

### I2 — What problem it solves

In a Django multi-database setup with a custom database router that restricts allow_migrate to only the 'default' connection, Django's MigrationRecorder still creates the django_migrations tracking table on ALL database connections. The MigrationRecorder.ensure_schema(), record_applied(), and record_unapplied() methods bypass the database router's allow_migrate check entirely, causing migration tracking tables to appear on connections where they shouldn't exist — effectively ignoring the router's routing rules.

### I3 — The key idea

The one insight the whole fix turns on: the database router's allow_migrate method is not being consulted before the migration recorder creates schema on any connection. The migration recorder must check router.allow_migrate(db, model) before creating the django_migrations table on connections other than the default. In a setup where router.allow_migrate(db, model) returns False for non-default dbs, the recorder should skip table creation/recording on those connections entirely.

### I4 — Instructions to solve it

1. In django/db/migrations/recorder.py, add `from django.db import routers` import at the top of the file.

2. In ensure_schema(verb='all', schema_editor=None): Before calling schema_editor.create_model(), check if the router's allow_migrate returns False for the model's app_label and the current db. If so, return early without creating the model. The check pattern: `if not routers.allow_migrate(schema_editor.connection.alias, model._meta.app_label): return`.

3. In record_applied(verb='all', model_names=None): Before recording each migration, check if the router allows migration on that db. If router.allow_migrate(db, 'contenttypes') returns False, skip recording that migration for this connection. Same pattern applied to all model names being recorded.

4. In record_unapplied(verb='all', model_names=None): Same — check router.allow_migrate before recording unapplied migrations. Skip any model where the router returns False for the current db.

5. After each change, verify that the default behavior is preserved: when no router is configured, or when router.allow_migrate returns True/None, the migration recorder should work exactly as before.

### I5 — Pitfalls and lessons

1. Attempt 2 produced no diff output — the fix from attempt 1 was not persisted between runs, likely because file state was reset. This is why documenting the skill is critical: future runs should not rediscover and re-lose the fix.

2. Do not assume the db alias 'default' — use whatever schema_editor.connection.alias the current schema uses. The router check must work with the actual connection being used.

3. Router.allow_migrate can return True, False, or None — only treat False as a skip condition. True or None means proceed with normal behavior (preserve existing functionality).

4. The app_label in the allow_migrate check should match the model's _meta.app_label (e.g., 'contenttypes' for the Migration model). Using a hardcoded app label may not work for all cases.

5. Always verify the fix with existing migration-related tests after applying. The fix must not break any test that was passing before.

6. Lesson: When a fix works (attempt 1 passed verification), the problem is usually persistence across attempts, not the fix itself. Document the exact changes so they can be re-applied.

## Rules

### R1 — Constraints and rules

1. Must not regress existing test coverage for migration recording — all existing migration tests must continue to pass.

2. Use `from django.db import routers` import from django.db.

3. Only skip when router.allow_migrate() explicitly returns False — do not assume based on db alias.

## References
