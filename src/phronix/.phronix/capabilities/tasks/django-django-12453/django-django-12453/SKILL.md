---
name: django-django-12453
description: The sympy-issue-atoms subject.
subject: django-django-12453
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Constraints |

## Instructions

### I1 — Problem description

Fix TransactionTestCase.serialized_rollback ordering issue where deserialization saves models without a transaction, causing integrity errors for foreign‑key ordered data.

### I2 — Key idea

Wrap the entire deserialization loop in a single atomic transaction to ensure all objects are saved together, avoiding intermediate integrity errors caused by foreign‑key ordering.

### I3 — Instructions to solve it

1. Edit `django/db/backends/base/creation.py`.
2. Add `transaction` to the imports: `from django.db import router, transaction`.
3. Locate the deserialization loop in `deserialize_db_from_string` (lines ~128‑140).
4. Wrap the loop with `with transaction.atomic(using=self.connection.alias):` and indent the `for obj in serializers.deserialize(...): obj.save()` inside the block.
5. Save the file and run the target test `test_circular_reference`.
6. Ensure the full regression suite still passes.

### I4 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/backends/base/creation.py b/django/db/backends/base/creation.py
index c50fc90171..5cf1f5b3c2 100755
--- a/django/db/backends/base/creation.py
+++ b/django/db/backends/base/creation.py
@@ -5,7 +5,7 @@ from io import StringIO
 from django.apps import apps
 from django.conf import settings
 from django.core import serializers
-from django.db import router
+from django.db import router, transaction
 
 # The prefix to put on the default database name when creating
 # the test database.
@@ -126,8 +126,9 @@ class BaseDatabaseCreation:
         the serialize_db_to_string() method.
         """
         data = StringIO(data)
-        for obj in serializers.deserialize("json", data, using=self.connection.alias):
-            obj.save()
+        with transaction.atomic(using=self.connection.alias):
+            for obj in serializers.deserialize("json", data, using=self.connection.alias):
+                obj.save()
 
     def _get_database_display_str(self, verbosity, database_name):
         """
```

## Rules

### R1 — Constraints

* The regression suite must remain green.
* Do not alter any import statements other than adding `transaction`.
* Do not change the order of deserialized objects beyond wrapping them in a transaction.
* The fix must be compatible with Django's existing `loaddata` transaction handling.
