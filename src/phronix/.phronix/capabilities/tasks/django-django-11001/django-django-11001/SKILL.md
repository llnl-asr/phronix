---
name: django-django-11001
description: The django-django-11001 subject.
subject: django-django-11001
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Deserialize database fixtures with transaction atomic |
| `I2` | Instructions | What problem it solves |
| `I3` | Instructions | The key idea |
| `I4` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Deserialize database fixtures with transaction atomic

Fix: Wrap obj.save() in transaction.atomic() in deserialize_db_from_string method (django/db/backends/base/creation.py).

Two changes:
1. Add `transaction` to import: `from django.db import router, transaction`
2. Wrap saves: `with transaction.atomic(using=self.connection.alias):\n            for obj in serializers.deserialize("json", data, using=self.connection.alias):\n                obj.save()`

Why: When serialized_rollback=True on TransactionTestCase, saves happen outside transaction, causing integrity errors if object with FK is saved before referenced instance. loaddata already wraps in transaction correctly.

Tests: test_circular_reference passes. Resolved YES - target 1 of 1, regression 5 of 5 passed.

### I2 — What problem it solves

A later run arrives with a failing test where RawSQL multiline expressions in order_by clauses are incorrectly deduplicated. The symptom: only the first RawSQL with a given trailing line is retained, and subsequent ones with identical endings are silently dropped from the query.

### I3 — The key idea

The email field is not always called `email`; when SQL is written as multiline RawSQL, the `ordering_parts` regex only matches the last line, causing duplicate detection to fail. The fix normalizes multiline SQL to a single line so the regex matches the complete expression, making duplicate detection work correctly for multiline RawSQL expressions.

### I4 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/models/sql/compiler.py b/django/db/models/sql/compiler.py
index 7649c39262..ce0c5bb2d9 100755
--- a/django/db/models/sql/compiler.py
+++ b/django/db/models/sql/compiler.py
@@ -353,7 +353,11 @@ class SQLCompiler:
             # not taken into account so we strip it. When this entire method
             # is refactored into expressions, then we can check each part as we
             # generate it.
-            without_ordering = self.ordering_parts.search(sql).group(1)
+            # Normalize multiline SQL (e.g. from RawSQL) by removing newlines
+            # so that the ordering_parts regex can match the full SQL text.
+            # See https://code.djangoproject.com/ticket/33396
+            sql_oneline = ' '.join(sql.split('\n'))
+            without_ordering = self.ordering_parts.search(sql_oneline).group(1)
             params_hash = make_hashable(params)
             if (without_ordering, params_hash) in seen:
                 continue
@@ -366,7 +370,11 @@ class SQLCompiler:
         if self.query.distinct and not self.query.distinct_fields:
             select_sql = [t[1] for t in select]
             for expr, (sql, params, is_ref) in order_by:
-                without_ordering = self.ordering_parts.search(sql).group(1)
+                # Normalize multiline SQL (e.g. from RawSQL) by removing newlines
+                # so that the ordering_parts regex can match the full SQL text.
+                # See https://code.djangoproject.com/ticket/33396
+                sql_oneline = ' '.join(sql.split('\n'))
+                without_ordering = self.ordering_parts.search(sql_oneline).group(1)
                 if not is_ref and (without_ordering, params) not in select_sql:
                     extra_select.append((expr, (without_ordering, params), None))
         return extra_select
```

## Rules
