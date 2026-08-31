---
name: django-django-15851
description: The django-django-15851 subject.
subject: django-django-15851
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Steps |
| `I4` | Instructions | Constraints |
| `I5` | Instructions | Pitfalls |
| `I6` | Instructions | Fix PostgreSQL dbshell parameter ordering |
| `I7` | Instructions | Why parameter order matters for psql |

## Instructions

### I1 — Problem description

Failing dbshell test where extra parameters are ignored because they appear after the database name; the fix requires ordering parameters before the dbname.

### I2 — Key idea

Pass additional parameters to psql before the database name in Django's PostgreSQL client.

### I3 — Steps

1. In `django/db/backends/postgresql/client.py` move `args.extend(parameters)` before appending `dbname`.
2. Add minimal stub modules for `asgiref` (`__init__.py`, `local.py`, `sync.py`) providing placeholder functions/classes to satisfy imports during tests.

### I4 — Constraints

Do not modify existing test files. Ensure regression tests (8) remain passing. Preserve existing behaviour of other database backends. Only change argument ordering in PostgreSQL client.

### I5 — Pitfalls

Attempting to reorder arguments after appending `dbname` leads to parameters being ignored by psql. Creating complex stubs for asgiref can break other code; keep them minimal.

### I6 — Fix PostgreSQL dbshell parameter ordering

In django/db/backends/postgresql/client.py, the settings_to_cmd_args_env classmethod constructs command-line arguments for the psql client. The bug was that the database name (dbname) was added before the user-supplied parameters/options via `args.extend(parameters)`, but psql requires all options to precede the database name.

### I7 — Why parameter order matters for psql

psql expects the command format `psql [options] [dbname]` — all options/flags must come before the database name. When Django's dbshell passes user parameters (like `-- -c "select * from some_table;"`) after the database name, psql warns that extra command-line arguments are ignored. The fix reorders so parameters come before dbname in the generated args list.

## References
