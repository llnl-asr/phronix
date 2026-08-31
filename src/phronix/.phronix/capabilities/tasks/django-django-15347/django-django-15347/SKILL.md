---
name: django-django-15347
description: The django-django-15347 subject.
subject: django-django-15347
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix extra_tags serialization in MessageEncoder |
| `I2` | Instructions | Symptom: extra_tags becomes None on empty string |
| `I3` | Instructions | Fix extra_tags handling in MessageEncoder |
| `R1` | Rules | Preserve empty string extra_tags |





## Instructions

### I1 — Fix extra_tags serialization in MessageEncoder

Update django/contrib/messages/storage/cookie.py: in MessageEncoder.default, replace the truthy check `if obj.extra_tags:` with `if obj.extra_tags is not None:` to ensure empty strings are preserved during JSON serialization. This prevents loss of empty extra_tags values, fixing the bug where messages lost their tags when serialized.

Tests check that the extra_tags attribute is correctly preserved (test_extra_tags) and all target tests (1 of 1) now pass.

### I2 — Symptom: extra_tags becomes None on empty string

When a Django message with `extra_tags=""` is serialized and then deserialized, `extra_tags` is converted to `None`, causing template checks like `{% if x not in message.extra_tags %}` to error.

### I3 — Fix extra_tags handling in MessageEncoder

Edit `django/contrib/messages/storage/cookie.py`:
```diff
@@
-            if obj.extra_tags:
+            if obj.extra_tags is not None:
```

## Rules

### R1 — Preserve empty string extra_tags

`extra_tags` may be an empty string; code must treat it distinct from `None` to avoid false negatives in template logic.

## References
