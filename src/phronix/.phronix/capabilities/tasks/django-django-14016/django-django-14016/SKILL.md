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
| `I2` | Instructions | The patch that made the tests pass |
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

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/models/query_utils.py b/django/db/models/query_utils.py
index c2623f099f..4b8092353d 100755
--- a/django/db/models/query_utils.py
+++ b/django/db/models/query_utils.py
@@ -41,9 +41,17 @@ class Q(tree.Node):
         super().__init__(children=[*args, *sorted(kwargs.items())], connector=_connector, negated=_negated)
 
     def _combine(self, other, conn):
+        # If the other is not a Q instance, raise TypeError as before.
         if not isinstance(other, Q):
             raise TypeError(other)
 
+        # Convert dict_keys in self.children to list for pickling safety.
+        def normalize(child):
+            if isinstance(child, tuple) and isinstance(child[1], type({}.keys())):
+                return (child[0], list(child[1]))
+            return child
+        self.children = [normalize(c) for c in self.children]
+
         # If the other Q() is empty, ignore it and just use `self`.
         if not other:
             return copy.deepcopy(self)
```

## Rules

### R1 — Do not modify non-Q objects

Ensure the `other` operand is an instance of Q before accessing `other.children` to avoid AttributeError.

### R2 — Preserve existing behavior for non-dict_keys children

The normalization should only affect tuple children where the second element is a dict_keys instance; other children remain unchanged.
