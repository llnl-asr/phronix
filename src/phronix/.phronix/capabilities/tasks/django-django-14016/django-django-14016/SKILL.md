---
name: django-django-14016
description: Fix TypeError when combining Q objects with dict_keys by normalizing dict_keys to lists in Q._combine.
subject: django-django-14016
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Apply normalization patch |
| `R1` | Rules | Do not modify non-Q objects |
| `R2` | Rules | Preserve existing behavior for non-dict_keys children |

## Instructions

### I1 — Apply normalization patch

Edit `django/db/models/query_utils.py`:
```diff
@@ -41,6 +41,13 @@ class Q(tree.Node):
-    def _combine(self, other, conn):
+    def _combine(self, other, conn):
+        # Convert dict_keys in children to list for pickling safety
+        def normalize(child):
+            if isinstance(child, tuple) and isinstance(child[1], type({}.keys())):
+                return (child[0], list(child[1]))
+            return child
+        self.children = [normalize(c) for c in self.children]
+        other.children = [normalize(c) for c in other.children]
         if not isinstance(other, Q):
             raise TypeError(other)
```

## Rules

### R1 — Do not modify non-Q objects

Ensure the `other` operand is an instance of Q before accessing `other.children` to avoid AttributeError.

### R2 — Preserve existing behavior for non-dict_keys children

The normalization should only affect tuple children where the second element is a dict_keys instance; other children remain unchanged.
