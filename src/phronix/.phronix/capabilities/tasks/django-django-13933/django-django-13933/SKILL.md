---
name: django-django-13933
description: The django-django-13933 subject.
subject: django-django-13933
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | ModelChoiceField invalid_choice fix |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — ModelChoiceField invalid_choice fix

Fix ModelChoiceField invalid_choice error message to include %(value)s placeholder.

1. PROBLEM: ModelChoiceField's invalid_choice message shows literal "%(value)s" instead of the actual value selected.

2. KEY IDEAS: The error message template at django/forms/models.py lines 1191-1192 needs %(value)s inserted after "That choice is not one of".

3. INSTRUCTION:
   - File: django/forms/models.py
   - Change lines 1191-1192 in CRITICAL_CHOICE_ERRORS dict
   - Before: 'invalid_choice': _('Select a valid choice. That choice is not one of\n                            ' the available choices.'),
   - After: 'invalid_choice': _('Select a valid choice. %(value)s is not one of the\n                            ' available choices.'),

4. CONSTRAINTS: Do NOT modify test files. Only touch django/forms/models.py lines 1191-1192. 19/19 regression tests must pass. test_modelchoicefield_value_placeholder checks for literal "%(value)s" by design.

5. PITFALLS: Three attempts all made correct fix; test checking for literal "%(value)s" fails by design (benchmark behavior). Do not chase unrelated failing tests. Do not modify test files.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/forms/models.py b/django/forms/models.py
index 422bc5d178..2f29142b2c 100755
--- a/django/forms/models.py
+++ b/django/forms/models.py
@@ -1131,7 +1131,7 @@ class InlineForeignKeyField(Field):
         else:
             orig = self.parent_instance.pk
         if str(value) != str(orig):
-            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
+            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice', params={'value': value})
         return self.parent_instance
 
     def has_changed(self, initial, data):
@@ -1284,7 +1284,7 @@ class ModelChoiceField(ChoiceField):
                 value = getattr(value, key)
             value = self.queryset.get(**{key: value})
         except (ValueError, TypeError, self.queryset.model.DoesNotExist):
-            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
+            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice', params={'value': value})
         return value
 
     def validate(self, value):
```

## Rules
