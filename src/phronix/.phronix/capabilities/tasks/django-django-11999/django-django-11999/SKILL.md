---
name: django-django-11999
description: Fix for Django issue where users cannot override get_FOO_display() methods on model fields with choices. The problem: Django's contribute_to_class method unconditionally adds get_%s_display to model classes when fields have choices, overwriting any user-defined get_FOO_display method. The fix adds a check to preserve user-defined overrides.
subject: django-django-11999
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Constraints and rules — part 1 |
| `R2` | Rules | Constraints and rules — part 2 |
| `R3` | Rules | Constraints and rules — part 3 |

## Instructions

### I1 — What problem it solves

The symptom: A user defines a custom `get_FOO_display()` method on a Django model with a choices field, expecting it to be called when `obj.get_FOO_display()` is invoked. However, in Django 2.2+, Django's `contribute_to_class` method unconditionally adds a `get_%s_display` method to the model class whenever a field has choices. This overwrites the user's custom method, so the custom display always returns the default Django lookup value instead of the user's override.

Later runs: Someone arrives with a failing test where `get_FOO_display()` returns the wrong value. They check if they defined a custom `get_FOO_display()` — if yes, the skill IS their problem. The key claim: "the email field is not always called `email`" — meaning the method name is derived from the field name, and the fix must check for the correctly-named method, not hardcode `email`.

### I2 — The key idea

The one insight: When a model field has choices, Django's `contribute_to_class` method adds a `get_%s_display` (where %s is the field's `name` attribute) to the model class using `partialmethod(cls._get_FIELD_display, field=self)`. This happens unconditionally — if the model class already defines a method with that exact name, Django's method overwrites it. The fix must check at class-creation time whether `get_%s_display` already exists on the class before adding Django's version. The check follows the exact same pattern Django already uses for the field attribute name at line 763: `if not getattr(cls, self.attname, None)`.

### I3 — Instructions to solve it

1. Locate `django/db/models/fields/__init__.py` and find the `contribute_to_class` method (around line 749-767).

2. In the section where `self.choices is not None` (around line 760-767), add a check before adding the `get_%s_display` method.

3. Change the unconditional `setattr(cls, 'get_%s_display' % self.name, partialmethod(cls._get_FIELD_display, field=self))` to first check if the method already exists on the class:
   ```python
   if not getattr(cls, 'get_%s_display' % self.name, None):
       setattr(cls, 'get_%s_display' % self.name,
               partialmethod(cls._get_FIELD_display, field=self))
   ```

4. The check `if not getattr(cls, 'get_%s_display' % self.name, None)` follows the same pattern Django already uses at line 763 for checking the field attribute name — it uses `getattr` with a default of `None` to test existence without raising AttributeError.

5. After applying the fix, verify that:
   - Models with user-defined `get_FOO_display()` methods PRESERVE their custom implementation
   - Models without such methods still get Django's default `get_FOO_display()` method added

### I4 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/models/fields/__init__.py b/django/db/models/fields/__init__.py
index ee45bb941e..411a7c4e40 100755
--- a/django/db/models/fields/__init__.py
+++ b/django/db/models/fields/__init__.py
@@ -763,8 +763,9 @@ class Field(RegisterLookupMixin):
             if not getattr(cls, self.attname, None):
                 setattr(cls, self.attname, self.descriptor_class(self))
         if self.choices is not None:
-            setattr(cls, 'get_%s_display' % self.name,
-                    partialmethod(cls._get_FIELD_display, field=self))
+            if not getattr(cls, 'get_%s_display' % self.name, None):
+                setattr(cls, 'get_%s_display' % self.name,
+                        partialmethod(cls._get_FIELD_display, field=self))
 
     def get_filter_kwargs_for_object(self, obj):
         """
```

## Rules

### R1 — Constraints and rules — part 1

1. The fix must not break existing tests: all 30 regression tests must keep passing, and the 1 target test must pass.

2. The check `if not getattr(cls, 'get_%s_display' % self.name, None)` must use the field's `name` attribute dynamically — not a hardcoded name like `email` or `status`.

### R2 — Constraints and rules — part 2

3. The pattern must follow Django's existing convention at line 763: use `getattr` with a default of `None` to test method existence without raising AttributeError.

4. Only the `contribute_to_class` method in `django/db/models/fields/__init__.py` should be modified. Do not change any other files, including test files.

### R3 — Constraints and rules — part 3

5. The fix must be minimal — only add the `if not getattr(...)` check, do not refactor surrounding code or change the `partialmethod` call structure.

6. The `get_%s_display` method name must use `self.name` (the field's attribute name), derived from the field definition dynamically.
