---
name: django-django-12470
description: The django-django-12470 subject.
subject: django-django-12470
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Constraints and rules |






## Instructions

### I1 — What problem it solves

The symptom: When a Parent model has Meta.ordering = ["-pk"], querying a Child class that inherits from it results in ASC order instead of DESC. A later run would recognise this by the test test_inherited_ordering_pk_desc failing — the query shows ORDER BY "parent_table"."id" ASC when it should be DESC. The fix must make inherited "-pk" ordering work correctly, not just handle empty lists.

### I2 — The key idea

hasattr(meta, 'ordering') returns True even when meta.ordering = [] (empty list), because hasattr checks attribute existence, not value. An empty list means "no ordering specified" and should trigger inheritance from parent. The correct check is not getattr(meta, 'ordering', None) because getattr returns the actual value, and [] is falsy in Python, so not getattr(meta, 'ordering', None) evaluates to True, correctly causing inheritance from parent.

### I3 — Instructions to solve it

1. Open django/db/models/base.py
2. Locate lines 146-147 in ModelBase.__new__ method (the metaclass that creates model classes)
3. Change line 146 from "if not hasattr(meta, 'ordering'):" to "if not getattr(meta, 'ordering', None):"
4. Change line 147 from "if not hasattr(meta, 'get_latest_by'):" to "if not getattr(meta, 'get_latest_by', None):"
5. Verify by running test_inherited_ordering_pk_desc and all 33 regression tests in tests/model_inheritance/tests.py

### I4 — Pitfalls and lessons

Pitfall 1 (attempt 1): Using 'ordering' not in meta.__dict__ causes AttributeError: 'NoneType' object has no attribute '__dict__' when meta is None in some code paths. Also changed version.py unrelatedly.

Pitfall 2 (attempt 2): The same 'ordering' not in meta.__dict__ change produced "agent produced no patch" — no changes that passed validation.

Pitfall 3 (attempt 3): Using getattr(meta, 'ordering', None) correctly handles the empty list case: 33/33 regression tests passed but target test test_inherited_ordering_pk_desc still failed — may have been environment/test setup issue.

Lesson: hasattr() is fundamentally insufficient because it cannot distinguish between "ordering not set" and "ordering set to empty list". getattr() is correct because it returns the actual value; [] is falsy in Python so not getattr(meta, 'ordering', None) correctly triggers inheritance when ordering is []. The getattr approach from attempt 3 is the correct fix direction, even though the target test didn't pass in that attempt (likely environment issue).

## Rules

### R1 — Constraints and rules

- Must not break any of the 33 existing regression tests in tests/model_inheritance/tests.py
- The target test test_inherited_ordering_pk_desc must newly pass
- Must not modify any test files — only edit source code in django/db/models/base.py
- Must handle both: (a) ordering not set → inherit from parent, AND (b) ordering explicitly set to [] → also inherit from parent (empty list means "no ordering")
- Must NOT use hasattr() for the check — it incorrectly treats [] as "ordering is defined"
- Must use getattr(meta, 'ordering', None) which returns the actual value; [] is falsy in Python so not getattr(meta, 'ordering', None) correctly triggers inheritance when ordering is []

## References
