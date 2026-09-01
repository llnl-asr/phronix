---
name: django-django-12125
description: The django-django-12125 subject.
subject: django-django-12125
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis for Django issue #12125 |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Diagnosis for Django issue #12125

Diagnosis for django-django-12125: Based on conversation analysis, this diagnosis is filed under the exact name "django-django-12125" as instructed. The next attempt will look up this diagnosis by that name and by nothing else.

Key constraints from user:
- Diagnosis filed under exact name "django-django-12125" only
- Do not diagnose again, do not read the source again, do not attempt the task
- If incomplete, partial diagnosis is worth more than none

This diagnosis captures the established context from the conversation without re-reading source files. The exact name ensures proper lookup by the next attempt.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/migrations/serializer.py b/django/db/migrations/serializer.py
index 7d226955d5..00e7bea1b7 100755
--- a/django/db/migrations/serializer.py
+++ b/django/db/migrations/serializer.py
@@ -267,9 +267,9 @@ class TypeSerializer(BaseSerializer):
         if hasattr(self.value, "__module__"):
             module = self.value.__module__
             if module == builtins.__name__:
-                return self.value.__name__, set()
+                return self.value.__qualname__, set()
             else:
-                return "%s.%s" % (module, self.value.__name__), {"import %s" % module}
+                return "%s.%s" % (module, self.value.__qualname__), {"import %s" % module}
 
 
 class UUIDSerializer(BaseSerializer):
```

## Rules
