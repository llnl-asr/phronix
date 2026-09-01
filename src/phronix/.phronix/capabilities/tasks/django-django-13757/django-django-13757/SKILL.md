---
name: django-django-13757
description: The django-django-13757 subject.
subject: django-django-13757
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | KeyTransformIsNull fix for key__isnull=True on SQLite and Oracle - problem and key idea |
| `I2` | Instructions | Instructions to solve it |
| `I3` | Instructions | Constraints and rules |
| `I4` | Instructions | Pitfalls and lessons |
| `I5` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — KeyTransformIsNull fix for key__isnull=True on SQLite and Oracle - problem and key idea

What problem it solves:
When using key__isnull=True on SQLite and Oracle databases, the query incorrectly matches objects where the JSON key exists but has a null value, rather than only matching objects where the key doesn't exist at all.

The key idea:
JSON_EXTRACT() on SQLite and JSON_VALUE() on Oracle both return NULL in two cases: (1) the key doesn't exist in the JSON document, and (2) the key exists but its value is NULL. The IS NULL check cannot distinguish between these two cases. The fix uses JSON_TYPE() on SQLite (returns NULL only when key doesn't exist) and NOT JSON_EXISTS() on Oracle (checks if key path exists, 1=exists, 0=doesn't exist; negated gives TRUE only when key is truly absent).

### I2 — Instructions to solve it

1. In django/db/models/fields/json.py, KeyTransformIsNull.as_sqlite() method: when self.rhs is True (isnull=True), instead of calling super().as_sql() which generates JSON_EXTRACT(...) IS NULL, use JSON_TYPE(json_col, 'path') IS NULL. JSON_TYPE returns NULL only when the key doesn't exist, not when the value is NULL.
2. In django/db/models/fields/json.py, KeyTransformIsNull.as_oracle() method: when self.rhs is True (isnull=True), instead of using JSON_VALUE(...) IS NULL which matches both "key doesn't exist" and "key exists with null value", use NOT JSON_EXISTS(json_col, '$.path'). JSON_EXISTS returns 1 if the path exists (regardless of value), 0 if it doesn't exist. Negating it gives TRUE only when the key is truly absent.
3. When self.rhs is False (isnull=False), the existing HasKey() code path is correct and should be preserved - do not modify this path.

### I3 — Constraints and rules

- The fix must only affect the isnull=True (self.rhs is True) code path
- The isnull=False (self.rhs is False) code path using HasKey must remain unchanged as it is correct
- For SQLite, use JSON_TYPE() which has the semantics: NULL = key doesn't exist, 'null' = key exists with null value, type name = key exists with value
- For Oracle, use NOT JSON_EXISTS() which has the semantics: 0 = key doesn't exist, 1 = key exists (any value)
- Do NOT modify any test files - the fix must make existing tests pass
- The change must be minimal: only modify the two methods (as_sqlite and as_oracle) when self.rhs is True
- Regression tests (test_isnull_key_or_none and all other JSON field tests) must continue to pass
- Only change the SQL generation; do not change the Python class structure or method signatures

### I4 — Pitfalls and lessons

- Initial attempt used super().as_sql() which generates IS NULL on JSON_EXTRACT() - this fails because IS NULL matches both "key doesn't exist" and "key exists with null value"
- Another attempt added __rmul__ to Point model which was unrelated to this task
- The JSON_TYPE() function on SQLite is critical: it returns None for non-existent keys but 'null' for keys with null values, allowing proper distinction
- NOT JSON_EXISTS() on Oracle similarly distinguishes: returns 0 when path doesn't exist, 1 when it does (regardless of value)
- Always verify both target tests AND regression tests pass - a fix that breaks other tests is incomplete
- The distinction between "key doesn't exist" and "key exists with null value" is subtle but critical for correct query semantics
- A previous attempt also broke test_isnull_key_or_none - ensure the fix does not regress that test

### I5 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/models/fields/json.py b/django/db/models/fields/json.py
index 29c6ff0926..2002692e82 100755
--- a/django/db/models/fields/json.py
+++ b/django/db/models/fields/json.py
@@ -368,12 +368,23 @@ class KeyTransformIsNull(lookups.IsNull):
     def as_oracle(self, compiler, connection):
         if not self.rhs:
             return HasKey(self.lhs.lhs, self.lhs.key_name).as_oracle(compiler, connection)
-        return super().as_sql(compiler, connection)
+        # Use JSON_EXISTS() which returns 1 if path exists, 0 otherwise.
+        # Negate it to find records where the key is truly absent (key doesn't exist).
+        # JSON_EXISTS returns 1 when the path exists (regardless of value),
+        # so NOT JSON_EXISTS() only matches when the key is completely absent.
+        lhs, lhs_params, key_transforms = self.lhs.preprocess_lhs(compiler, connection)
+        json_path = compile_json_path(key_transforms)
+        return "NOT JSON_EXISTS(%s, '%s')" % (lhs, json_path), lhs_params
 
     def as_sqlite(self, compiler, connection):
         if not self.rhs:
             return HasKey(self.lhs.lhs, self.lhs.key_name).as_sqlite(compiler, connection)
-        return super().as_sql(compiler, connection)
+        # Use JSON_TYPE() which returns NULL only when key doesn't exist
+        # JSON_TYPE returns 'null' (string) when key exists with null value
+        # By checking IS NULL, we only match the case where the key is truly absent.
+        lhs, params, key_transforms = self.lhs.preprocess_lhs(compiler, connection)
+        json_path = compile_json_path(key_transforms)
+        return "JSON_TYPE(%s, '%s') IS NULL" % (lhs, json_path), params
 
 
 class KeyTransformIn(lookups.In):
```

## Rules
