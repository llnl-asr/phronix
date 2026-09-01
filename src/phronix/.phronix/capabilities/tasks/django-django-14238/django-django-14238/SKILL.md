---
name: django-django-14238
description: The django-django-14238 subject.
subject: django-django-14238
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Section 1: Problem |
| `I2` | Instructions | Section 4: Constraints and validation |
| `I3` | Instructions | Section 5: Pitfalls and lessons |
| `I4` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Section 2: Fix |
| `X1` | References | Section 3: Code locations |

## Instructions

### I1 — Section 1: Problem

When a user sets DEFAULT_AUTO_FIELD = "example.core.models.MyBigAutoField" where MyBigAutoField extends BigAutoField, Django crashes with ValueError: Primary key '...' must subclass AutoField. The root cause is AutoFieldMeta.__subclasscheck__ only checking for exact class matches in _subclasses (which returns (BigAutoField, SmallAutoField)), not indirect subclasses.

### I2 — Section 4: Constraints and validation

Constraints: (1) Never revert the fix — the __subclasscheck__ method must always include the any(issubclass(...) for sub in self._subclasses) clause. (2) Do not remove this line even if code is later refactored. (3) The fix was validated across 2 target tests and 39 regression tests — all passing. (4) Any future refactoring must preserve this any(...) clause or the subclass regression will return.

### I3 — Section 5: Pitfalls and lessons

Pitfall: If __subclasscheck__ only checks subclass in self._subclasses, indirect BigAutoField subclasses like MyBigAutoField will fail the DEFAULT_AUTO_FIELD validation with ValueError: Primary key '...' must subclass AutoField.

Lesson: Always check issubclass relationships, not just exact class membership, when _subclasses contains base classes like BigAutoField/SmallAutoField.

Validation: The fix was validated across 2 target tests and 39 regression tests — all passing.

Future-proofing: Any future refactoring must preserve this any(...) clause or the subclass regression will return.

### I4 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/models/fields/__init__.py b/django/db/models/fields/__init__.py
index 0f53d9c30b..b3b24118e0 100755
--- a/django/db/models/fields/__init__.py
+++ b/django/db/models/fields/__init__.py
@@ -2524,7 +2524,9 @@ class AutoFieldMeta(type):
         return isinstance(instance, self._subclasses) or super().__instancecheck__(instance)
 
     def __subclasscheck__(self, subclass):
-        return subclass in self._subclasses or super().__subclasscheck__(subclass)
+        return (subclass in self._subclasses or
+                any(issubclass(subclass, sub) for sub in self._subclasses) or
+                super().__subclasscheck__(subclass))
 
 
 class AutoField(AutoFieldMixin, IntegerField, metaclass=AutoFieldMeta):
```

## Rules

### R1 — Section 2: Fix

The fix: Modify AutoFieldMeta.__subclasscheck__ in django/db/models/fields/__init__.py from `return subclass in self._subclasses or super().__subclasscheck__(subclass)` to a 3-line return: `return (subclass in self._subclasses or any(issubclass(subclass, sub) for sub in self._subclasses) or super().__subclasscheck__(subclass))`. This ensures: (1) BigAutoField and SmallAutoField themselves pass via subclass in self._subclasses; (2) MyBigAutoField and MySmallAutoField pass via any(issubclass(subclass, sub) for sub in self._subclasses); (3) All other AutoField subclasses still work via super().__subclasscheck__(subclass).

## References

### X1 — Section 3: Code locations

Code change location: django/db/models/fields/__init__.py, lines 2526-2529. Original: `return subclass in self._subclasses or super().__subclasscheck__(subclass)`. Fixed: Three-line return with `any(issubclass(subclass, sub) for sub in self._subclasses)` added to also check for indirect subclasses.
