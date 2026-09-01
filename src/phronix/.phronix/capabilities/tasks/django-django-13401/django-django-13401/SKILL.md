---
name: django-django-13401
description: Fix abstract model field equality, ordering, and hashing.
subject: django-django-13401
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Adjust Field equality, ordering, and hashing for abstract models |
| `I2` | Instructions | Problem description |
| `I3` | Instructions | What problem it solves |
| `I4` | Instructions | The key idea |
| `I5` | Instructions | Instructions to solve it |
| `I6` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Constraints and rules |

## Instructions

### I1 — Adjust Field equality, ordering, and hashing for abstract models

In `django/db/models/fields/__init__.py`, update the `Field` class methods:

* `__eq__`: Compare both `creation_counter` and the owning model. If both fields have a `model` attribute, return true only when `self.creation_counter == other.creation_counter` **and** `self.model is other.model`. This prevents fields from different abstract models being considered equal.

* `__lt__`: Compare model identity first, then `creation_counter`. If both fields have a `model`, order by model ID (`id(self.model)`) when models differ; if models are the same, fall back to `creation_counter` for stable ordering.

* `__hash__`: Include the model in the hash. When a `model` attribute exists, return `hash((self.creation_counter, id(self.model)))`; otherwise, hash only `creation_counter`.

These changes ensure that abstract model fields are distinct across different models, fixing equality collisions that caused set deduplication and ordering issues. The tests verify that abstract model field instances are not equal and that ordering remains stable.

### I2 — Problem description

Abstract model fields from different models compare equal, causing deduplication when collecting fields into a set.

Symptoms: `len({B._meta.get_field('myfield'), C._meta.get_field('myfield')}) == 1` and `B._meta.get_field('myfield') == C._meta.get_field('myfield')`.

A later run with failing tests will see this equality collision.

### I3 — What problem it solves

Abstract model fields compare equal across different models, causing deduplication when collecting fields and leading to failing tests that expect distinct field instances per model.

### I4 — The key idea

Include the field's model identity in __eq__, __hash__, and ordering to differentiate fields from different models.

### I5 — Instructions to solve it

1. Open `django/db/models/fields/__init__.py`.
2. In `Field.__eq__`, add a check: if both `self` and `other` have a `model` attribute, return `self.creation_counter == other.creation_counter and self.model is other.model`; otherwise fall back to comparing `creation_counter` only.
3. In `Field.__lt__`, add a check: if both have a `model` attribute, compare `id(self.model)` with `id(other.model)`. If the models are the same, compare `creation_counter`; otherwise order by model id.
4. In `Field.__hash__`, add a check: if the field has a `model` attribute, return `hash((self.creation_counter, id(self.model)))`; otherwise return `hash(self.creation_counter)`.
5. Run the full test suite to ensure the target test passes and the 32 regression tests still pass.
6. Commit the changes.

### I6 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/models/fields/__init__.py b/django/db/models/fields/__init__.py
index 28374272f4..29cef7629e 100755
--- a/django/db/models/fields/__init__.py
+++ b/django/db/models/fields/__init__.py
@@ -514,18 +514,29 @@ class Field(RegisterLookupMixin):
         return self.__class__(*args, **kwargs)
 
     def __eq__(self, other):
-        # Needed for @total_ordering
+        # Compare both creation_counter and model to avoid equality across different models
         if isinstance(other, Field):
+            # Some fields may not have a model attribute; fallback to creation_counter only
+            if hasattr(self, 'model') and hasattr(other, 'model'):
+                return (self.creation_counter == other.creation_counter) and (self.model is other.model)
             return self.creation_counter == other.creation_counter
         return NotImplemented
 
     def __lt__(self, other):
-        # This is needed because bisect does not take a comparison function.
+        # Compare both creation_counter and model for ordering
         if isinstance(other, Field):
+            if hasattr(self, 'model') and hasattr(other, 'model'):
+                # First compare model identity, then creation_counter to keep stable order
+                if self.model is other.model:
+                    return self.creation_counter < other.creation_counter
+                return id(self.model) < id(other.model)
             return self.creation_counter < other.creation_counter
         return NotImplemented
 
     def __hash__(self):
+        # Include model in hash to differentiate fields from different models
+        if hasattr(self, 'model'):
+            return hash((self.creation_counter, id(self.model)))
         return hash(self.creation_counter)
 
     def __deepcopy__(self, memodict):
```

## Rules

### R1 — Constraints and rules

R1: All existing regression tests (32) must continue to pass after the changes.
R2: Field ordering within the same model must remain based on `creation_counter` to preserve original behavior.
R3: The added `model` checks must be guarded with `hasattr` to avoid attribute errors on fields without a model.
R4: The `__hash__` implementation must remain deterministic across runs for the same field.
R5: Do not modify any other parts of `django/db/models/fields/__init__.py` beyond the three methods.
