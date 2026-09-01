---
name: django-django-14915
description: The django-django-14915 subject.
subject: django-django-14915
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | ModelChoiceIteratorValue hashability fix |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | __eq__ and __hash__ consistency constraint |
| `X1` | References | ModelChoiceIteratorValue hashable fix pattern |

## Instructions

### I1 — ModelChoiceIteratorValue hashability fix

Problem: ModelChoiceIteratorValue instances raise TypeError: unhashable type when used as dict keys (e.g., `value in self.show_fields`). The class defined __eq__ but not __hash__, making Python automatically make instances unhashable.

Key insight: When __eq__ compares based on self.value, __hash__ must also be based on self.value to maintain Python's invariant that equal objects have equal hashes.

Fix: Add __hash__ method to ModelChoiceIteratorValue class returning hash(self.value), placed after the existing __eq__ method.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/forms/models.py b/django/forms/models.py
index 5dcf923c12..bc7e6959e7 100755
--- a/django/forms/models.py
+++ b/django/forms/models.py
@@ -1171,6 +1171,9 @@ class ModelChoiceIteratorValue:
             other = other.value
         return self.value == other
 
+    def __hash__(self):
+        return hash(self.value)
+
 
 class ModelChoiceIterator:
     def __init__(self, field):
```

## Rules

### R1 — __eq__ and __hash__ consistency constraint

Rule: If __eq__ is defined in a class based on a specific attribute, __hash__ must also be defined based on the same attribute. The ModelChoiceIteratorValue class already defined __eq__ based on self.value; omitting __hash__ caused instances to be automatically unhashable. The fix must add __hash__ returning hash(self.value) — not modifying __eq__ in any way.

Violation consequence: TypeError: unhashable type when using instances as dict keys or in set membership tests.

## References

### X1 — ModelChoiceIteratorValue hashable fix pattern

Reference pattern: When a class defines __eq__ based on attribute X, always add __hash__ based on the same attribute X. Example from this fix:

```python
def __eq__(self, other):
    return isinstance(other, ModelChoiceIteratorValue) and self.value == other.value

def __hash__(self):
    return hash(self.value)
```

The __hash__ method was added after the __eq__ method, ensuring Python's invariant is preserved: if a == b, then hash(a) == hash(b). The auto-generated __hash__ = None that results from defining __eq__ without explicit __hash__ would make the TypeError inevitable.
