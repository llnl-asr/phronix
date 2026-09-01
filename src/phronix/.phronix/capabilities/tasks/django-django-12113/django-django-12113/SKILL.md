---
name: django-django-12113
description: Fix SQLite database locking when using --keepdb --parallel 1 with multiple database aliases. The fix adds explicit TEST configurations with unique NAME values to prevent different database aliases from sharing the same test database file.
subject: django-django-12113
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7 - Naming and identification |
| `I2` | Instructions | I9 - What belongs in a skill vs memory |
| `I3` | Instructions | Fix instructions - add TEST configurations |
| `R1` | Rules | Constraints and rules |





## Instructions

### I1 — I7 - Naming and identification

Skill name: django-django-12113
Subject: Fix SQLite database locking when using --keepdb --parallel 1 with multiple database aliases
Problem: When running Django admin tests with --keepdb --parallel 1 using multiple database aliases, SQLite databases get locked because both database connections share the same default test database file
Symptom: sqlite3.OperationalError: database is locked when admin_views.test_multidb.MultiDatabaseTests.setUpTestData tries to create a superuser

### I2 — I9 - What belongs in a skill vs memory

What belongs in this skill (not in memory):
- Instructions on how to apply the fix (add TEST configurations with unique NAME values)
- Constraints and rules about what must stay true while solving
- Pitfalls and lessons from what did not work
- Key idea: test_db_signature doesn't include connection alias for file-based databases

What does NOT belong in this skill (go to memory instead):
- Specific code diffs or patch content
- Exact file paths of changed files (unless part of the structural instruction)
- Personal observations or session-specific notes
- Outcomes of whether the task passed or failed

### I3 — Fix instructions - add TEST configurations

1. In tests/test_sqlite.py, locate the DATABASES setting
2. Under the 'default' database configuration, add:
   'TEST': {
       'NAME': 'test_default.sqlite3'
   },
3. Under the 'other' database configuration, add:
   'TEST': {
       'NAME': 'test_other.sqlite3'
   },
4. The TEST configurations must use unique NAME values for each database alias
5. Do not modify any other settings (ENGINE, etc.) - only add the TEST sub-dictionary
6. The fix ensures each database alias gets a distinct test database file, eliminating cross-process locking conflicts when using --keepdb with multiple databases in parallel

## Rules

### R1 — Constraints and rules

Constraints:
- Only add TEST sub-dictionary to existing DATABASES entries - do not remove or modify any existing keys
- TEST NAME values must be unique per database alias (test_default.sqlite3 for 'default', test_other.sqlite3 for 'other')
- The DATABASES setting structure must be preserved exactly as-is, only adding the TEST key
- Do not change test logic, test methods, or test assertions - only add configuration
- The fix must work with --keepdb --parallel 1 flag combination

Rules:
- Must not break existing test functionality
- Must not modify any test files other than tests/test_sqlite.py DATABASES configuration
- The TEST NAME must follow Django's test database naming conventions
- After applying the fix, tests should run without sqlite3.OperationalError: database is locked

## References

- `skill_load(name="django-django-12113", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

