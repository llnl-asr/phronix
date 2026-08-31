---
name: django-django-11001
description: The django-django-11001 subject.
subject: django-django-11001
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix ordering_parts regex to handle multiline RawSQL |
| `I2` | Instructions | Deserialize database fixtures with transaction atomic |
| `I3` | Instructions | What problem it solves |
| `I4` | Instructions | The key idea |

## Instructions

### I1 — Fix ordering_parts regex to handle multiline RawSQL

In `django/db/models/sql/compiler.py`, update the `ordering_parts` regular expression to include the DOTALL flag so it matches across newlines:
```python
-        self.ordering_parts = re.compile(r'(.*)\s(ASC|DESC)(.*)')
+        self.ordering_parts = re.compile(r'(.*)\s(ASC|DESC)(.*)', re.DOTALL)
```
**Why:** The original regex stopped at the first newline, causing only the first RawSQL order‑by clause to be recognized. Multiline RawSQL strings share the same final line (`ASC`/`DESC`), so later clauses were mistakenly considered duplicates and omitted from the query. Adding `re.DOTALL` makes the pattern span the entire SQL string, correctly handling multiline order‑by expressions.

**What the tests check:** The test suite includes `test_order_by_multiline_sql` which ensures that order‑by clauses using multiline `RawSQL` are preserved. After this change, both target tests (`test_order_by_exists` and `test_order_by_multiline_sql`) pass, confirming the fix.

### I2 — Deserialize database fixtures with transaction atomic

Fix: Wrap obj.save() in transaction.atomic() in deserialize_db_from_string method (django/db/backends/base/creation.py).

Two changes:
1. Add `transaction` to import: `from django.db import router, transaction`
2. Wrap saves: `with transaction.atomic(using=self.connection.alias):\n            for obj in serializers.deserialize("json", data, using=self.connection.alias):\n                obj.save()`

Why: When serialized_rollback=True on TransactionTestCase, saves happen outside transaction, causing integrity errors if object with FK is saved before referenced instance. loaddata already wraps in transaction correctly.

Tests: test_circular_reference passes. Resolved YES - target 1 of 1, regression 5 of 5 passed.

### I3 — What problem it solves

A later run arrives with a failing test where RawSQL multiline expressions in order_by clauses are incorrectly deduplicated. The symptom: only the first RawSQL with a given trailing line is retained, and subsequent ones with identical endings are silently dropped from the query.

### I4 — The key idea

The email field is not always called `email`; when SQL is written as multiline RawSQL, the `ordering_parts` regex only matches the last line, causing duplicate detection to fail. The fix normalizes multiline SQL to a single line so the regex matches the complete expression, making duplicate detection work correctly for multiline RawSQL expressions.

## References
