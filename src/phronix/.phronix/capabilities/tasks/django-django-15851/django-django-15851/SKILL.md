---
name: django-django-15851
description: The django-django-15851 subject.
subject: django-django-15851
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix PostgreSQL dbshell parameter ordering |
| `I2` | Instructions | Why parameter order matters for psql |
| `I3` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Fix PostgreSQL dbshell parameter ordering

In django/db/backends/postgresql/client.py, the settings_to_cmd_args_env classmethod constructs command-line arguments for the psql client. The bug was that the database name (dbname) was added before the user-supplied parameters/options via `args.extend(parameters)`, but psql requires all options to precede the database name.

### I2 — Why parameter order matters for psql

psql expects the command format `psql [options] [dbname]` — all options/flags must come before the database name. When Django's dbshell passes user parameters (like `-- -c "select * from some_table;"`) after the database name, psql warns that extra command-line arguments are ignored. The fix reorders so parameters come before dbname in the generated args list.

### I3 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/backends/postgresql/client.py b/django/db/backends/postgresql/client.py
index 4c9bd63546..3b5ddafaca 100755
--- a/django/db/backends/postgresql/client.py
+++ b/django/db/backends/postgresql/client.py
@@ -32,9 +32,9 @@ class DatabaseClient(BaseDatabaseClient):
             args += ["-h", host]
         if port:
             args += ["-p", str(port)]
+        args.extend(parameters)
         if dbname:
             args += [dbname]
-        args.extend(parameters)
 
         env = {}
         if passwd:
```

## Rules
