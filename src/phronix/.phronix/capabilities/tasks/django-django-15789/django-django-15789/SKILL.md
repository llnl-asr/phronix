---
name: django-django-15789
description: Support custom JSON encoder in json_script
subject: django-django-15789
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |
| `I6` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — What problem it solves

Allow callers of django.utils.html.json_script to provide a custom JSON encoder, enabling serialization of custom data types.

### I2 — Key idea

Add optional encoder argument defaulting to DjangoJSONEncoder and use it in json.dumps.

### I3 — Instructions to solve it

1. Edit django/utils/html.py.
2. Change function signature to `def json_script(value, element_id=None, encoder=None):`.
3. Inside, set `encoder_cls = encoder if encoder is not None else DjangoJSONEncoder`.
4. Replace json.dumps call with `json.dumps(value, cls=encoder_cls)`.
5. Preserve existing behavior by default.

### I4 — Constraints and rules

- Do not alter other parts of json_script.
- Ensure all existing tests continue to pass.
- Default encoder must be DjangoJSONEncoder when encoder is None.

### I5 — Pitfalls and lessons

- Adding a parameter without default breaks callers; provide default None.
- Ensure the import of DjangoJSONEncoder remains.
- Verify that custom encoder class is compatible with json.dumps cls parameter.

### I6 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/utils/html.py b/django/utils/html.py
index d0bc97be80..422a9b66db 100755
--- a/django/utils/html.py
+++ b/django/utils/html.py
@@ -59,15 +59,25 @@ _json_script_escapes = {
 }
 
 
-def json_script(value, element_id=None):
+def json_script(value, element_id=None, encoder=None):
     """
     Escape all the HTML/XML special characters with their unicode escapes, so
     value is safe to be output anywhere except for inside a tag attribute. Wrap
     the escaped JSON in a script tag.
+
+    Args:
+        value: A Python object to be serialized to JSON.
+        element_id: If provided, the JSON will be placed in a script tag with this
+            id attribute.
+        encoder: A JSON encoder class to use for serializing the value. If not
+            provided, DjangoJSONEncoder is used.
     """
-    from django.core.serializers.json import DjangoJSONEncoder
+    if encoder is None:
+        from django.core.serializers.json import DjangoJSONEncoder
+
+        encoder = DjangoJSONEncoder
 
-    json_str = json.dumps(value, cls=DjangoJSONEncoder).translate(_json_script_escapes)
+    json_str = json.dumps(value, cls=encoder).translate(_json_script_escapes)
     if element_id:
         template = '<script id="{}" type="application/json">{}</script>'
         args = (element_id, mark_safe(json_str))
```

## Rules
