---
name: django-django-12286
description: The django-django-12286 subject.
subject: django-django-12286
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/core/checks/translation.py b/django/core/checks/translation.py
index 138ed07ff8..0e2c1f462c 100755
--- a/django/core/checks/translation.py
+++ b/django/core/checks/translation.py
@@ -57,5 +57,10 @@ def check_language_settings_consistent(app_configs, **kwargs):
     """Error if language settings are not consistent with each other."""
     available_tags = {i for i, _ in settings.LANGUAGES} | {'en-us'}
     if settings.LANGUAGE_CODE not in available_tags:
-        return [E004]
+        # If the exact language code is not available, check if the base language
+        # (e.g., "de" from "de-at") is available, per Django's language fallback
+        # behavior described in the documentation.
+        base_language = settings.LANGUAGE_CODE.split('-')[0]
+        if base_language not in available_tags:
+            return [E004]
     return []
```

## Rules
