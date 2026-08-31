---
name: django-django-14238
description: The django-django-14238 subject.
subject: django-django-14238
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Section 1: Problem |
| `I5` | Instructions | Section 4: Constraints and validation |
| `I6` | Instructions | Section 5: Pitfalls and lessons |
| `R1` | Rules | Do not modify other logic in AutoFieldMeta |
| `R2` | Rules | Section 2: Fix |

## Instructions

### I1 — Problem description

Fails when DEFAULT_AUTO_FIELD is set to a subclass of BigAutoField or SmallAutoField because AutoFieldMeta.__subclasscheck__ does not recognize indirect subclasses.

### I2 — Key idea

Modify AutoFieldMeta.__subclasscheck__ to accept indirect subclasses of BigAutoField and SmallAutoField via an any() check over _subclasses.

### I3 — Instructions to solve it

Apply the following diff to `django/db/models/fields/__init__.py`:

```diff
@@
-        return subclass in self._subclasses or super().__subclasscheck__(subclass)
+        # Accept indirect subclasses of BigAutoField or SmallAutoField
+        return any(issubclass(subclass, s) for s in self._subclasses) or super().__subclasscheck__(subclass)
```

### I4 — Section 1: Problem

When a user sets DEFAULT_AUTO_FIELD = "example.core.models.MyBigAutoField" where MyBigAutoField extends BigAutoField, Django crashes with ValueError: Primary key '...' must subclass AutoField. The root cause is AutoFieldMeta.__subclasscheck__ only checking for exact class matches in _subclasses (which returns (BigAutoField, SmallAutoField)), not indirect subclasses.

### I5 — Section 4: Constraints and validation

Constraints: (1) Never revert the fix — the __subclasscheck__ method must always include the any(issubclass(...) for sub in self._subclasses) clause. (2) Do not remove this line even if code is later refactored. (3) The fix was validated across 2 target tests and 39 regression tests — all passing. (4) Any future refactoring must preserve this any(...) clause or the subclass regression will return.

### I6 — Section 5: Pitfalls and lessons

Pitfall: If __subclasscheck__ only checks subclass in self._subclasses, indirect BigAutoField subclasses like MyBigAutoField will fail the DEFAULT_AUTO_FIELD validation with ValueError: Primary key '...' must subclass AutoField.

Lesson: Always check issubclass relationships, not just exact class membership, when _subclasses contains base classes like BigAutoField/SmallAutoField.

Validation: The fix was validated across 2 target tests and 39 regression tests — all passing.

Future-proofing: Any future refactoring must preserve this any(...) clause or the subclass regression will return.

## Rules

### R1 — Do not modify other logic in AutoFieldMeta

Only change the subclasscheck implementation; other behavior of AutoFieldMeta must remain unchanged to avoid regressions.

### R2 — Section 2: Fix

The fix: Modify AutoFieldMeta.__subclasscheck__ in django/db/models/fields/__init__.py from `return subclass in self._subclasses or super().__subclasscheck__(subclass)` to a 3-line return: `return (subclass in self._subclasses or any(issubclass(subclass, sub) for sub in self._subclasses) or super().__subclasscheck__(subclass))`. This ensures: (1) BigAutoField and SmallAutoField themselves pass via subclass in self._subclasses; (2) MyBigAutoField and MySmallAutoField pass via any(issubclass(subclass, sub) for sub in self._subclasses); (3) All other AutoField subclasses still work via super().__subclasscheck__(subclass).

## References

### X1 — Section 3: Code locations

Code change location: django/db/models/fields/__init__.py, lines 2526-2529. Original: `return subclass in self._subclasses or super().__subclasscheck__(subclass)`. Fixed: Three-line return with `any(issubclass(subclass, sub) for sub in self._subclasses)` added to also check for indirect subclasses.
