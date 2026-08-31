---
name: django-django-15400
description: The django-django-15400 subject.
subject: django-django-15400
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix __radd__ implementation in SimpleLazyObject |
| `I2` | Instructions | Problem Description |
| `I3` | Instructions | Key Idea |
| `I4` | Instructions | Apply Fix |
| `R1` | Rules | Constraints |






## Instructions

### I1 — Fix __radd__ implementation in SimpleLazyObject

Update `django/utils/functional.py`:
```diff
@@
-    def __radd__(self, other):
-        return other + self.__cast()
+    def __radd__(self, other):
+        # Ensure the lazy object is evaluated before performing reverse addition.
+        # ``self.__cast()`` expects the wrapped object to have ``__cast`` which an
+        # ``int`` does not. Mirror the logic of ``__add__``: evaluate the lazy
+        # object and then delegate the operation to the underlying value.
+        self._setup()
+        return other + self._wrapped
```

### I2 — Problem Description

SimpleLazyObject lacks a working `__radd__` method, causing failures in `test_add` and `test_radd` where addition with an int raises `TypeError` or `AttributeError`.

### I3 — Key Idea

Implement `__radd__` by delegating to the underlying wrapped value after ensuring it is evaluated, mirroring the existing `__add__` logic.

### I4 — Apply Fix

In `django/utils/functional.py` replace the provisional `__radd__` implementation with:
```python
def __radd__(self, other):
    # Ensure the underlying object is evaluated like __add__ does.
    if self._wrapped is empty:
        self._setup()
    return other + self._wrapped
```
This mirrors the logic of `__add__` and delegates the addition to the evaluated wrapped value.

## Rules

### R1 — Constraints

- Existing regression tests (62) must continue to pass.
- The lazy‑evaluation behavior of `SimpleLazyObject` must remain unchanged for all other operations.
- Do not modify other magic methods; only add `__radd__`.
- Ensure `_setup()` is called when the wrapped value is not yet evaluated.

## References
