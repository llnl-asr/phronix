---
name: django-django-14752
description: The django-django-14752 subject.
subject: django-django-14752
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | serialize_result method for AutocompleteJsonView |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — serialize_result method for AutocompleteJsonView

Add a `serialize_result(self, obj, to_field_name)` method to `AutocompleteJsonView` that returns `{'id': str(getattr(obj, to_field_name)), 'text': str(obj)}`, and modify `get()` to call `self.serialize_result(obj, to_field_name)` instead of constructing the dict inline.

This enables users to customize autocomplete response fields by overriding `serialize_result()` in a subclass, without needing to fully override `get()`.

Example:
```python
class CustomAutocompleteJsonView(AutocompleteJsonView):
    def serialize_result(self, obj, to_field_name):
        return {'id': str(getattr(obj, to_field_name)), 'text': str(obj), 'notes': obj.notes}
```

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/contrib/admin/views/autocomplete.py b/django/contrib/admin/views/autocomplete.py
index 3903e4c98c..593bb371dd 100755
--- a/django/contrib/admin/views/autocomplete.py
+++ b/django/contrib/admin/views/autocomplete.py
@@ -26,12 +26,14 @@ class AutocompleteJsonView(BaseListView):
         context = self.get_context_data()
         return JsonResponse({
             'results': [
-                {'id': str(getattr(obj, to_field_name)), 'text': str(obj)}
-                for obj in context['object_list']
+                self.serialize_result(obj, to_field_name) for obj in context['object_list']
             ],
             'pagination': {'more': context['page_obj'].has_next()},
         })
 
+    def serialize_result(self, obj, to_field_name):
+        return {'id': str(getattr(obj, to_field_name)), 'text': str(obj)}
+
     def get_paginator(self, *args, **kwargs):
         """Use the ModelAdmin's paginator."""
         return self.model_admin.get_paginator(self.request, *args, **kwargs)
```

## Rules
