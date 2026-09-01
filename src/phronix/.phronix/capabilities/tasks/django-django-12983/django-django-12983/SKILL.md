---
name: django-django-12983
description: The django-django-12983 subject.
subject: django-django-12983
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Django Issue 12983 Diagnosis |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Django Issue 12983 Diagnosis

Django issue #12983 (task 272, django__django-12983) research context.

User instructions: "If the diagnosis is incomplete, write what you have. A partial fix the next attempt can build on is worth more than a complete one it never sees." User also: "Do not diagnose again, do not read the source again, do not attempt the task: take what is there and file it." User emphasized exact-name lookup: "the next attempt looks it up by that name and by nothing else"

Available context from exploration:
- Django forms, views, utils structure examined
- research.py infrastructure: assess(), define_fom(), add_approach(), choose(), write_plan()
- research-2.md does not exist at expected path (main blocker)
- Memory files in cache paths but not as task-level research documents
- Django code patterns: forms widgets, _make_hash_value, view decorators, URL patterns
- Research methodology: approach evaluation with train/validate/test, FOM, operation kinds

This skill captures the available diagnosis context from the exploration of Django issue #12983 in task 272, structured for exact-name lookup by the next attempt.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/utils/text.py b/django/utils/text.py
index fb5f6298c4..3ba4bbb3f4 100755
--- a/django/utils/text.py
+++ b/django/utils/text.py
@@ -403,7 +403,7 @@ def slugify(value, allow_unicode=False):
     else:
         value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
     value = re.sub(r'[^\w\s-]', '', value.lower()).strip()
-    return re.sub(r'[-\s]+', '-', value)
+    return re.sub(r'[-\s]+', '-', value).strip('-_')
 
 
 def camel_case_to_spaces(value):
```

## Rules
