---
name: django-django-14915
description: The django-django-14915 subject.
subject: django-django-14915
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add __hash__ to ModelChoiceIteratorValue |
| `I2` | Instructions | Problem solved |
| `I3` | Instructions | Symptom |
| `I4` | Instructions | Key idea |
| `I5` | Instructions | Instructions |
| `I6` | Instructions | ModelChoiceIteratorValue hashability fix |
| `R1` | Rules | __eq__ and __hash__ consistency constraint |

## Instructions

### I1 — Add __hash__ to ModelChoiceIteratorValue

Add a __hash__ method to ModelChoiceIteratorValue in django/forms/models.py that returns hash(self.value). This makes instances hashable for use as dict keys.

@@ -1171,6 +1171,10 @@ class ModelChoiceIteratorValue:
    def __eq__(self, other):
        if isinstance(other, ModelChoiceIteratorValue):
            other = other.value
        return self.value == other

+    def __hash__(self):
+        # Use the hash of the underlying value to allow dict operations.
+        return hash(self.value)

### I2 — Problem solved

Unhashable ModelChoiceIteratorValue error when using dict operations after Django upgrade.

### I3 — Symptom

Tests fail with `TypeError: unhashable type: 'ModelChoiceIteratorValue'` when a dict operation is attempted on a ModelChoiceIteratorValue after upgrading to Django 3.1.

### I4 — Key idea

Implementing __hash__ on ModelChoiceIteratorValue allows it to be used as a dict key, fixing the unhashable error.

### I5 — Instructions

1. Open `django/forms/models.py`.
2. Locate class `ModelChoiceIteratorValue` around line 1170.
3. Add the following method inside the class:
```python
    def __hash__(self):
        return hash(self.value)
```
4. Save the file and run the test suite.
5. Verify that all tests now pass.

### I6 — ModelChoiceIteratorValue hashability fix

Problem: ModelChoiceIteratorValue instances raise TypeError: unhashable type when used as dict keys (e.g., `value in self.show_fields`). The class defined __eq__ but not __hash__, making Python automatically make instances unhashable.

Key insight: When __eq__ compares based on self.value, __hash__ must also be based on self.value to maintain Python's invariant that equal objects have equal hashes.

Fix: Add __hash__ method to ModelChoiceIteratorValue class returning hash(self.value), placed after the existing __eq__ method.

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
