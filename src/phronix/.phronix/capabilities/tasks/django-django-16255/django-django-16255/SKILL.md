---
name: django-django-16255
description: Adds ValueError handling to get_latest_lastmod for empty items with callable lastmod
subject: django-django-16255
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | The patch that made the tests pass |
| `R1` | Rules | ValueError handling in get_latest_lastmod |

## Instructions

### I1 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/contrib/sitemaps/__init__.py b/django/contrib/sitemaps/__init__.py
index 27756d9d96..b40ad806ed 100755
--- a/django/contrib/sitemaps/__init__.py
+++ b/django/contrib/sitemaps/__init__.py
@@ -168,7 +168,7 @@ class Sitemap:
         if callable(self.lastmod):
             try:
                 return max([self.lastmod(item) for item in self.items()])
-            except TypeError:
+            except (TypeError, ValueError):
                 return None
         else:
             return self.lastmod
```

## Rules

### R1 — ValueError handling in get_latest_lastmod

In Django's sitemap framework, the get_latest_lastmod() method in django/contrib/sitemaps/__init__.py needs to catch ValueError in addition to TypeError. When self.items() returns an empty list and self.lastmod is callable, max([self.lastmod(item) for item in self.items()]) raises ValueError: max() arg is an empty sequence. The fix is to change except TypeError to except (TypeError, ValueError) so the method gracefully returns None instead of crashing.
