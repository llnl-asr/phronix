---
name: django-django-16041
description: The django-django-16041 subject.
subject: django-django-16041
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis of empty_permitted KeyError in Django formsets |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Diagnosis of empty_permitted KeyError in Django formsets



### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/forms/formsets.py b/django/forms/formsets.py
index 57676428ff..2dd91e5fd4 100755
--- a/django/forms/formsets.py
+++ b/django/forms/formsets.py
@@ -262,7 +262,7 @@ class BaseFormSet(RenderableFormMixin):
             prefix=self.add_prefix("__prefix__"),
             empty_permitted=True,
             use_required_attribute=False,
-            **self.get_form_kwargs(None),
+            **{k: v for k, v in self.get_form_kwargs(None).items() if k != 'empty_permitted'},
             renderer=self.renderer,
         )
         self.add_fields(form, None)
```

## Rules
